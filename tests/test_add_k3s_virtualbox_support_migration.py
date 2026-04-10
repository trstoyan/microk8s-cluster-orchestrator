import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "add_k3s_and_virtualbox_support.py"


def load_migration_module():
    spec = importlib.util.spec_from_file_location("add_k3s_virtualbox_support", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AddK3sVirtualBoxSupportMigrationTests(unittest.TestCase):
    def test_migration_adds_runtime_and_provider_columns(self):
        module = load_migration_module()

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "cluster_data.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    ha_enabled BOOLEAN,
                    addons TEXT,
                    network_cidr VARCHAR(50),
                    service_cidr VARCHAR(50),
                    status VARCHAR(50),
                    health_score INTEGER,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname VARCHAR(255) UNIQUE NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    ssh_user VARCHAR(100),
                    ssh_port INTEGER,
                    ssh_key_path VARCHAR(500),
                    status VARCHAR(50),
                    last_seen DATETIME,
                    microk8s_version VARCHAR(50),
                    microk8s_status VARCHAR(50),
                    is_control_plane BOOLEAN,
                    created_at DATETIME,
                    updated_at DATETIME,
                    cluster_id INTEGER
                )
                """
            )
            cursor.execute(
                "INSERT INTO clusters (name, network_cidr, service_cidr) VALUES (?, ?, ?)",
                ("verify", "10.1.0.0/16", "10.152.183.0/24"),
            )
            cursor.execute(
                "INSERT INTO nodes (hostname, ip_address, microk8s_version, microk8s_status, is_control_plane) VALUES (?, ?, ?, ?, ?)",
                ("cp1", "192.0.2.10", "1.30", "running", 1),
            )
            conn.commit()
            conn.close()

            original_db_path = module.DB_PATH
            module.DB_PATH = db_path
            try:
                self.assertTrue(module.run_migration())
            finally:
                module.DB_PATH = original_db_path

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(clusters)")
            cluster_columns = {row[1] for row in cursor.fetchall()}
            self.assertIn("kubernetes_distribution", cluster_columns)
            self.assertIn("infrastructure_provider", cluster_columns)

            cursor.execute("PRAGMA table_info(nodes)")
            node_columns = {row[1] for row in cursor.fetchall()}
            self.assertIn("kubernetes_version", node_columns)
            self.assertIn("kubernetes_status", node_columns)
            self.assertIn("virtualization_provider", node_columns)
            self.assertIn("provider_vm_name", node_columns)
            self.assertIn("provider_vm_group", node_columns)
            self.assertIn("provider_metadata", node_columns)

            cursor.execute(
                "SELECT kubernetes_distribution, infrastructure_provider FROM clusters WHERE name = ?",
                ("verify",),
            )
            self.assertEqual(cursor.fetchone(), ("microk8s", "generic"))

            cursor.execute(
                "SELECT kubernetes_version, kubernetes_status, virtualization_provider FROM nodes WHERE hostname = ?",
                ("cp1",),
            )
            self.assertEqual(cursor.fetchone(), ("1.30", "running", "generic"))
            conn.close()


if __name__ == "__main__":
    unittest.main()
