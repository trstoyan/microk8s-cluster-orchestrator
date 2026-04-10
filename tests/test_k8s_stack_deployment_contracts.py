import stat
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
K8S_DIR = PROJECT_ROOT / "deployment" / "k8s"


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        docs = [doc for doc in yaml.safe_load_all(handle) if doc]
    if not docs:
        raise AssertionError(f"No YAML docs in {path}")
    return docs


class K8sStackDeploymentContractsTests(unittest.TestCase):
    def test_k8s_manifests_exist(self):
        required = [
            "kustomization.yaml",
            "namespace.yaml",
            "serviceaccount-rbac.yaml",
            "pvc.yaml",
            "configmap.yaml",
            "secret.example.yaml",
            "deployment.yaml",
            "service.yaml",
        ]
        for name in required:
            self.assertTrue((K8S_DIR / name).exists(), f"Missing manifest: {name}")

    def test_deployment_contracts(self):
        deployment_doc = _load_yaml(K8S_DIR / "deployment.yaml")[0]
        self.assertEqual(deployment_doc["kind"], "Deployment")
        container = deployment_doc["spec"]["template"]["spec"]["containers"][0]

        env_by_name = {entry["name"]: entry for entry in container["env"]}
        self.assertEqual(env_by_name["DATABASE_PATH"]["value"], "/app/data/cluster_data.db")
        self.assertEqual(env_by_name["ORCHESTRATOR_CONFIG"]["value"], "/app/config/cluster.yml")
        self.assertEqual(env_by_name["ORCHESTRATOR_AUTO_MIGRATE"]["value"], "true")

        self.assertEqual(
            deployment_doc["spec"]["template"]["spec"]["serviceAccountName"],
            "mko",
        )

    def test_plugin_apply_rbac_contract(self):
        docs = _load_yaml(K8S_DIR / "serviceaccount-rbac.yaml")
        kinds = {doc["kind"] for doc in docs}
        self.assertEqual(kinds, {"ServiceAccount", "Role", "RoleBinding"})

        role = next(doc for doc in docs if doc["kind"] == "Role")
        rules = role["rules"]
        resources = {(tuple(rule.get("apiGroups", [])), tuple(rule.get("resources", []))) for rule in rules}
        self.assertIn((("",), ("configmaps",)), resources)
        self.assertIn((("apps",), ("deployments",)), resources)

    def test_secret_template_has_required_keys(self):
        secret_doc = _load_yaml(K8S_DIR / "secret.example.yaml")[0]
        self.assertEqual(secret_doc["kind"], "Secret")
        string_data = secret_doc["stringData"]
        self.assertIn("FLASK_SECRET_KEY", string_data)
        self.assertIn("SECRET_KEY", string_data)

    def test_container_image_contracts(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("kubectl", dockerfile)
        self.assertIn("gunicorn", dockerfile)
        self.assertIn("wsgi:application", dockerfile)

    def test_stack_deploy_script_exists_and_executable(self):
        script = PROJECT_ROOT / "deployment" / "scripts" / "deploy_k8s_stack.sh"
        self.assertTrue(script.exists())
        mode = script.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
