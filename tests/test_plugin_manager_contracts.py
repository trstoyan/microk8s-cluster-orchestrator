import os
import sys
import tempfile
import unittest
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class PluginManagerContractTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mko-plugin-tests-")
        self.database_path = str(Path(self.tmpdir.name) / "test.db")
        os.environ["DATABASE_PATH"] = self.database_path

        from app.utils.config import config
        from app.models import database as database_module

        database_module.DATABASE_PATH = self.database_path
        database_module.DATABASE_URL = f"sqlite:///{self.database_path}"

        self.plugins_storage = str(Path(self.tmpdir.name) / "installed_plugins")
        config.set("plugins.storage_dir", self.plugins_storage)
        config.set("plugins.auto_apply_configmap", False)

        from app import create_app

        self.app = create_app()
        self.ctx = self.app.app_context()
        self.ctx.push()

        from app.models.database import db
        from app.models.flask_models import User

        db.create_all()
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("test123")
        db.session.add(admin)
        db.session.commit()
        self.admin_id = admin.id

    def tearDown(self):
        from app.models.database import db

        db.session.remove()
        self.ctx.pop()
        self.tmpdir.cleanup()

    def _create_plugin_repo(self) -> tuple[str, str]:
        repo_dir = Path(self.tmpdir.name) / "plugin_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / ".mko-plugin").mkdir(parents=True, exist_ok=True)

        (repo_dir / ".mko-plugin" / "plugin.json").write_text(
            '{"id":"test_plugin","name":"Test Plugin","version":"0.1.0","mko_plugin_api":"v1","entrypoints":{"module":"plugin.py","actions_factory":"get_actions","health_factory":"collect_health"}}',
            encoding="utf-8",
        )
        (repo_dir / "plugin.py").write_text(
            "def collect_health():\n"
            "    return {'status': 'ok', 'checks': []}\n\n"
            "def get_actions():\n"
            "    return [{'id': 'noop', 'name': 'Noop', 'description': 'noop', 'type': 'ansible_playbook', 'playbook_path': 'playbook.yml'}]\n",
            encoding="utf-8",
        )
        (repo_dir / "playbook.yml").write_text(
            "---\n- name: noop\n  hosts: all\n  tasks:\n    - debug:\n        msg: noop\n",
            encoding="utf-8",
        )

        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return str(repo_dir), commit

    def test_install_from_allowlisted_repo_and_commit(self):
        from app.utils.config import config

        repo_url, commit = self._create_plugin_repo()
        config.set("plugins.allowed_repositories", [repo_url])
        config.set("plugins.allowed_commits", {repo_url: [commit]})

        manager = self.app.extensions["plugin_manager"]
        plugin = manager.install_from_git(repo_url, commit, self.admin_id)

        self.assertEqual(plugin["plugin_id"], "test_plugin")
        self.assertEqual(plugin["current_commit"], commit)
        self.assertEqual(plugin["status"], "installed")
        self.assertIsNotNone(plugin["bundle_sha256"])
        self.assertEqual(len(plugin["bundle_sha256"]), 64)

    def test_install_rejects_non_allowlisted_commit(self):
        from app.utils.config import config
        from app.services.plugin_manager import PluginManagerError

        repo_url, commit = self._create_plugin_repo()
        config.set("plugins.allowed_repositories", [repo_url])
        config.set("plugins.allowed_commits", {repo_url: []})

        manager = self.app.extensions["plugin_manager"]
        with self.assertRaises(PluginManagerError):
            manager.install_from_git(repo_url, commit, self.admin_id)

    def test_plan_and_execute_action_generates_audit(self):
        from app.utils.config import config
        from app.models.flask_models import PluginActionAudit

        repo_url, commit = self._create_plugin_repo()
        config.set("plugins.allowed_repositories", [repo_url])
        config.set("plugins.allowed_commits", {repo_url: [commit]})

        manager = self.app.extensions["plugin_manager"]
        manager.install_from_git(repo_url, commit, self.admin_id)

        plan = manager.plan_action("test_plugin", "noop", {}, self.admin_id)
        self.assertIn("confirmation_token", plan)

        with patch("app.services.plugin_manager.PlaybookService.execute_playbook", return_value=SimpleNamespace(id=1234)):
            result = manager.execute_action(plan["confirmation_token"], "test run", self.admin_id)
        self.assertIn("audit_id", result)
        self.assertIn("playbook_execution_id", result)

        audit = PluginActionAudit.query.get(result["audit_id"])
        self.assertIsNotNone(audit)
        self.assertEqual(audit.plugin_id, "test_plugin")
        self.assertEqual(audit.action_id, "noop")

    def test_execute_action_with_idempotency_key_replays_result(self):
        from app.utils.config import config
        from app.models.flask_models import PluginActionAudit

        repo_url, commit = self._create_plugin_repo()
        config.set("plugins.allowed_repositories", [repo_url])
        config.set("plugins.allowed_commits", {repo_url: [commit]})

        manager = self.app.extensions["plugin_manager"]
        manager.install_from_git(repo_url, commit, self.admin_id)
        plan = manager.plan_action("test_plugin", "noop", {}, self.admin_id)

        with patch("app.services.plugin_manager.PlaybookService.execute_playbook", return_value=SimpleNamespace(id=2222)):
            first = manager.execute_action(
                plan["confirmation_token"],
                "first execution",
                self.admin_id,
                idempotency_key="idem-1",
            )
            replay = manager.execute_action(
                plan["confirmation_token"],
                "first execution",
                self.admin_id,
                idempotency_key="idem-1",
            )

        self.assertFalse(first.get("replayed", False))
        self.assertTrue(replay.get("replayed", False))
        self.assertEqual(first["playbook_execution_id"], replay["playbook_execution_id"])

        audits = PluginActionAudit.query.filter_by(plugin_id="test_plugin", action_id="noop").all()
        self.assertEqual(len(audits), 1)


if __name__ == "__main__":
    unittest.main()
