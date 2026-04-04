import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK_DIR = PROJECT_ROOT / "ansible" / "playbooks"


class K3sPlaybookContractTests(unittest.TestCase):
    def load_playbook(self, filename: str):
        content = (PLAYBOOK_DIR / filename).read_text(encoding="utf-8")
        documents = list(yaml.safe_load_all(content))
        self.assertTrue(documents, f"{filename} should contain at least one YAML document")
        return documents[0]

    def test_check_k3s_status_playbook_targets_k3s_nodes(self):
        playbook = self.load_playbook("check_k3s_status.yml")
        self.assertEqual(playbook[0]["hosts"], "k3s_nodes")

    def test_setup_k3s_cluster_playbook_targets_cluster_nodes(self):
        playbook = self.load_playbook("setup_k3s_cluster.yml")
        self.assertEqual(playbook[0]["hosts"], "cluster_nodes")
        task_names = [task["name"] for task in playbook[0]["tasks"]]
        self.assertIn("Install primary k3s server", task_names)
        self.assertIn("Install worker agents", task_names)

    def test_scan_k3s_cluster_state_emits_structured_markers(self):
        raw_content = (PLAYBOOK_DIR / "scan_k3s_cluster_state.yml").read_text(encoding="utf-8")
        self.assertIn("CLUSTER_SCAN_RESULTS:", raw_content)
        self.assertIn("DISCOVERED_NODES_JSON:", raw_content)

    def test_shutdown_k3s_cluster_mentions_k3s_services(self):
        raw_content = (PLAYBOOK_DIR / "shutdown_k3s_cluster.yml").read_text(encoding="utf-8")
        self.assertIn("name: k3s", raw_content)
        self.assertIn("name: k3s-agent", raw_content)


if __name__ == "__main__":
    unittest.main()
