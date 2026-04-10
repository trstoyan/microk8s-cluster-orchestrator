"""Plugin management and secure action execution for MKO."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer

from ..models.database import db
from ..models.flask_models import PluginActionAudit, PluginInstallation
from ..services.playbook_service import PlaybookService
from ..utils.config import config

logger = logging.getLogger(__name__)


class PluginManagerError(RuntimeError):
    """Raised when plugin operations fail."""


@dataclass
class LoadedPluginRuntime:
    """In-memory runtime bundle for one plugin revision."""

    module: Any
    actions: Dict[str, Dict[str, Any]]
    health_collector: Optional[Any]


class PluginManager:
    """Install, validate, and execute approved plugin actions."""

    MANIFEST_PATH = Path(".mko-plugin/plugin.json")

    def __init__(self) -> None:
        self.plugins_root = Path(config.get("plugins.storage_dir", "data/plugins"))
        self.plan_ttl_seconds = int(config.get("plugins.plan_ttl_seconds", 900) or 900)
        self.auto_apply_configmap = bool(config.get("plugins.auto_apply_configmap", False))
        self._runtime_cache: Dict[str, LoadedPluginRuntime] = {}
        self._serializer: Optional[URLSafeTimedSerializer] = None

    def init_app(self, app: Flask) -> None:
        """Attach manager to app and preload enabled plugins."""
        self.plugins_root.mkdir(parents=True, exist_ok=True)
        self._serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mko-plugin-actions")
        app.extensions["plugin_manager"] = self
        with app.app_context():
            self._load_enabled_plugins()

    def _require_serializer(self) -> URLSafeTimedSerializer:
        if self._serializer is None:
            raise PluginManagerError("Plugin manager is not initialized")
        return self._serializer

    def _assert_repo_commit_allowed(self, repo_url: str, commit: str) -> None:
        allowed_repositories = set(config.get("plugins.allowed_repositories", []))
        if repo_url not in allowed_repositories:
            raise PluginManagerError(f"Repository is not in allowlist: {repo_url}")

        allowed_commits = config.get("plugins.allowed_commits", {}) or {}
        allowed_for_repo = set(allowed_commits.get(repo_url, []))
        if not allowed_for_repo or commit not in allowed_for_repo:
            raise PluginManagerError("Commit is not in pinned allowlist")

    def _read_manifest(self, source_dir: Path) -> Dict[str, Any]:
        manifest_path = source_dir / self.MANIFEST_PATH
        if not manifest_path.exists():
            raise PluginManagerError("Missing plugin manifest: .mko-plugin/plugin.json")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PluginManagerError(f"Invalid plugin manifest JSON: {exc}") from exc

        required = {"id", "name", "version", "mko_plugin_api", "entrypoints"}
        missing = sorted(required - set(manifest.keys()))
        if missing:
            raise PluginManagerError(f"Manifest missing required fields: {', '.join(missing)}")

        if manifest["mko_plugin_api"] != "v1":
            raise PluginManagerError("Unsupported plugin API version")

        entrypoints = manifest.get("entrypoints") or {}
        if not isinstance(entrypoints, dict):
            raise PluginManagerError("Manifest entrypoints must be an object")

        module_rel = entrypoints.get("module")
        if not module_rel:
            raise PluginManagerError("Manifest entrypoints.module is required")

        module_path = source_dir / module_rel
        if not module_path.exists():
            raise PluginManagerError(f"Plugin module not found: {module_rel}")

        return manifest

    def _checkout_plugin(self, repo_url: str, commit: str) -> Path:
        tmp_dir = Path(tempfile.mkdtemp(prefix="mko-plugin-src-"))
        try:
            subprocess.run(["git", "clone", repo_url, str(tmp_dir)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(tmp_dir), "checkout", commit], check=True, capture_output=True, text=True)
            resolved = subprocess.run(
                ["git", "-C", str(tmp_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if resolved != commit:
                raise PluginManagerError("Checked out commit does not match requested pinned commit")
            return tmp_dir
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise

    def install_from_git(self, repo_url: str, commit: str, installed_by: Optional[int]) -> Dict[str, Any]:
        """Install plugin from allowlisted repo+commit into local storage."""
        self._assert_repo_commit_allowed(repo_url, commit)
        source_dir = self._checkout_plugin(repo_url, commit)
        try:
            manifest = self._read_manifest(source_dir)
            plugin_id = manifest["id"]
            destination = self.plugins_root / plugin_id / commit
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source_dir, destination)

            plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
            if plugin is None:
                plugin = PluginInstallation(plugin_id=plugin_id)
                db.session.add(plugin)

            plugin.name = manifest["name"]
            plugin.version = manifest["version"]
            plugin.mko_plugin_api = manifest["mko_plugin_api"]
            plugin.repo_url = repo_url
            plugin.previous_commit = plugin.current_commit
            plugin.current_commit = commit
            plugin.installed_path = str(destination)
            plugin.manifest_json = json.dumps(manifest)
            plugin.status = "installed"
            plugin.enabled = False
            plugin.last_error = None
            plugin.installed_by = installed_by
            plugin.updated_by = installed_by
            plugin.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            if self.auto_apply_configmap:
                try:
                    self.apply_plugin_to_cluster(plugin_id, installed_by)
                except Exception as exc:  # fail closed for install state
                    plugin.status = "apply_failed"
                    plugin.last_error = str(exc)
                    db.session.commit()
                    raise

            return plugin.to_dict()
        finally:
            shutil.rmtree(source_dir, ignore_errors=True)

    def list_plugins(self) -> list[Dict[str, Any]]:
        plugins = PluginInstallation.query.order_by(PluginInstallation.plugin_id.asc()).all()
        return [plugin.to_dict() for plugin in plugins]

    def enable_plugin(self, plugin_id: str, updated_by: Optional[int]) -> Dict[str, Any]:
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")
        plugin.enabled = True
        plugin.status = "enabled_pending_restart"
        plugin.updated_by = updated_by
        plugin.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return plugin.to_dict()

    def disable_plugin(self, plugin_id: str, updated_by: Optional[int]) -> Dict[str, Any]:
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")
        plugin.enabled = False
        plugin.status = "disabled"
        plugin.updated_by = updated_by
        plugin.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return plugin.to_dict()

    def rollback_plugin(self, plugin_id: str, updated_by: Optional[int]) -> Dict[str, Any]:
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")
        if not plugin.previous_commit:
            raise PluginManagerError("No previous plugin revision available")

        rollback_path = self.plugins_root / plugin_id / plugin.previous_commit
        if not rollback_path.exists():
            raise PluginManagerError("Previous plugin revision files are missing")

        current = plugin.current_commit
        plugin.current_commit = plugin.previous_commit
        plugin.previous_commit = current
        plugin.installed_path = str(rollback_path)
        plugin.status = "rolled_back_pending_restart"
        plugin.updated_by = updated_by
        plugin.updated_at = datetime.now(timezone.utc)
        plugin.last_error = None
        db.session.commit()
        return plugin.to_dict()

    def apply_plugin_to_cluster(self, plugin_id: str, updated_by: Optional[int]) -> Dict[str, Any]:
        """Apply plugin bundle as ConfigMap and trigger deployment restart annotation."""
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")
        if not plugin.current_commit or not plugin.installed_path:
            raise PluginManagerError("Plugin has no installed bundle")

        namespace = config.get("plugins.k8s.namespace", "orchestrator")
        deployment = config.get("plugins.k8s.deployment", "microk8s-cluster-orchestrator")
        configmap_name = f"mko-plugin-{plugin_id}"

        with tempfile.TemporaryDirectory(prefix="mko-plugin-tar-") as tmp:
            archive_base = Path(tmp) / "plugin_bundle"
            archive_path = shutil.make_archive(str(archive_base), "gztar", plugin.installed_path)

            apply_cmd = (
                f"kubectl -n {namespace} create configmap {configmap_name} "
                f"--from-file=plugin.tgz={archive_path} --dry-run=client -o yaml | kubectl apply -f -"
            )
            subprocess.run(apply_cmd, shell=True, check=True, capture_output=True, text=True)

            patch_payload = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                f"plugins.mko.dev/{plugin_id}": plugin.current_commit,
                                "plugins.mko.dev/restartedAt": datetime.now(timezone.utc).isoformat(),
                            }
                        }
                    }
                }
            }
            subprocess.run(
                [
                    "kubectl",
                    "-n",
                    namespace,
                    "patch",
                    "deployment",
                    deployment,
                    "--type",
                    "merge",
                    "-p",
                    json.dumps(patch_payload),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        plugin.status = "applied"
        plugin.updated_by = updated_by
        plugin.updated_at = datetime.now(timezone.utc)
        plugin.last_error = None
        db.session.commit()
        return plugin.to_dict()

    def _load_enabled_plugins(self) -> None:
        enabled_plugins = PluginInstallation.query.filter_by(enabled=True).all()
        for plugin in enabled_plugins:
            try:
                self._get_plugin_runtime(plugin)
                plugin.status = "enabled"
                plugin.last_error = None
            except Exception as exc:  # pragma: no cover - safety path
                plugin.status = "load_failed"
                plugin.last_error = str(exc)
                logger.exception("Failed to load plugin %s", plugin.plugin_id)
        db.session.commit()

    def _get_plugin_runtime(self, plugin: PluginInstallation) -> LoadedPluginRuntime:
        cache_key = f"{plugin.plugin_id}:{plugin.current_commit}"
        cached = self._runtime_cache.get(cache_key)
        if cached is not None:
            return cached

        if not plugin.installed_path:
            raise PluginManagerError("Plugin has no installed path")

        manifest = json.loads(plugin.manifest_json or "{}")
        entrypoints = manifest.get("entrypoints") or {}
        module_rel = entrypoints.get("module")
        if not module_rel:
            raise PluginManagerError("Plugin manifest missing entrypoints.module")

        module_path = Path(plugin.installed_path) / module_rel
        if not module_path.exists():
            raise PluginManagerError("Plugin module file is missing")

        module_name = f"mko_plugin_{plugin.plugin_id}_{(plugin.current_commit or '')[:8]}"
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        if spec is None or spec.loader is None:
            raise PluginManagerError("Unable to load plugin module spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        actions_factory_name = entrypoints.get("actions_factory", "get_actions")
        health_factory_name = entrypoints.get("health_factory", "collect_health")

        actions_factory = getattr(module, actions_factory_name, None)
        actions = actions_factory() if callable(actions_factory) else []
        if not isinstance(actions, list):
            raise PluginManagerError("Plugin actions factory must return a list")
        action_map = {action["id"]: action for action in actions if isinstance(action, dict) and action.get("id")}

        health_collector = getattr(module, health_factory_name, None)
        if health_collector is not None and not callable(health_collector):
            raise PluginManagerError("Plugin health factory must be callable")

        runtime = LoadedPluginRuntime(module=module, actions=action_map, health_collector=health_collector)
        self._runtime_cache[cache_key] = runtime
        return runtime

    def collect_health(self, plugin_id: str) -> Dict[str, Any]:
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")

        runtime = self._get_plugin_runtime(plugin)
        if runtime.health_collector is None:
            return {
                "plugin_id": plugin_id,
                "status": "unknown",
                "checks": [],
                "message": "Plugin does not provide health collector",
            }

        payload = runtime.health_collector()
        if not isinstance(payload, dict):
            raise PluginManagerError("Plugin health collector must return a dict")
        payload.setdefault("plugin_id", plugin_id)
        payload.setdefault("status", "unknown")
        payload.setdefault("checks", [])
        return payload

    def plan_action(self, plugin_id: str, action_id: str, params: Dict[str, Any], planned_by: Optional[int]) -> Dict[str, Any]:
        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")

        runtime = self._get_plugin_runtime(plugin)
        action = runtime.actions.get(action_id)
        if action is None:
            raise PluginManagerError("Plugin action not found")

        if action.get("type") != "ansible_playbook":
            raise PluginManagerError("Only ansible_playbook actions are supported in v1")

        serializer = self._require_serializer()
        plan_payload = {
            "plugin_id": plugin_id,
            "action_id": action_id,
            "params": params or {},
            "planned_by": planned_by,
            "planned_at": datetime.now(timezone.utc).isoformat(),
        }
        token = serializer.dumps(plan_payload)
        return {
            "confirmation_token": token,
            "token_ttl_seconds": self.plan_ttl_seconds,
            "action": action,
            "params": params or {},
            "plugin": plugin.to_dict(),
        }

    def execute_action(
        self,
        confirmation_token: str,
        execute_reason: str,
        executed_by: Optional[int],
    ) -> Dict[str, Any]:
        serializer = self._require_serializer()
        try:
            payload = serializer.loads(confirmation_token, max_age=self.plan_ttl_seconds)
        except SignatureExpired as exc:
            raise PluginManagerError("Action confirmation token expired") from exc
        except BadData as exc:
            raise PluginManagerError("Invalid action confirmation token") from exc

        plugin_id = payload.get("plugin_id")
        action_id = payload.get("action_id")
        params = payload.get("params") or {}

        plugin = PluginInstallation.query.filter_by(plugin_id=plugin_id).one_or_none()
        if plugin is None:
            raise PluginManagerError("Plugin not found")

        runtime = self._get_plugin_runtime(plugin)
        action = runtime.actions.get(action_id)
        if action is None:
            raise PluginManagerError("Plugin action no longer exists")

        playbook_rel = action.get("playbook_path")
        if not playbook_rel:
            raise PluginManagerError("Plugin action missing playbook_path")

        playbook_path = Path(plugin.installed_path) / playbook_rel
        if not playbook_path.exists():
            raise PluginManagerError("Plugin action playbook file not found")

        targets = action.get("targets") or [{"type": "all_nodes"}]

        audit = PluginActionAudit(
            plugin_id=plugin_id,
            action_id=action_id,
            execute_reason=execute_reason,
            requested_by=payload.get("planned_by"),
            approved_by=executed_by,
            status="running",
            token_hash=hashlib.sha256(confirmation_token.encode("utf-8")).hexdigest(),
            plan_payload=json.dumps(payload),
            started_at=datetime.now(timezone.utc),
        )
        db.session.add(audit)
        db.session.flush()

        try:
            playbook_content = playbook_path.read_text(encoding="utf-8")
            execution = PlaybookService().execute_playbook(
                execution_name=f"plugin:{plugin_id}:{action_id}:{audit.id}",
                yaml_content=playbook_content,
                targets=targets,
                extra_vars=params,
                created_by=executed_by,
            )
            audit.status = "queued"
            audit.result_payload = json.dumps({"playbook_execution_id": execution.id})
            audit.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return {
                "plugin_id": plugin_id,
                "action_id": action_id,
                "audit_id": audit.id,
                "playbook_execution_id": execution.id,
                "status": "queued",
            }
        except Exception as exc:
            audit.status = "failed"
            audit.error_message = str(exc)
            audit.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            raise
