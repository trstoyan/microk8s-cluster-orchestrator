import sqlite3
import tempfile
import types
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "add_plugin_platform_tables.py"


class PluginPlatformMigrationTests(unittest.TestCase):
    def test_migration_adds_new_columns_and_indexes(self):
        with tempfile.TemporaryDirectory(prefix="mko-plugin-migration-") as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE plugin_installations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    version VARCHAR(100) NOT NULL,
                    mko_plugin_api VARCHAR(50) NOT NULL DEFAULT 'v1',
                    repo_url VARCHAR(1024) NOT NULL,
                    current_commit VARCHAR(64) NOT NULL,
                    previous_commit VARCHAR(64),
                    installed_path VARCHAR(1024) NOT NULL,
                    manifest_json TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 0,
                    status VARCHAR(64) NOT NULL DEFAULT 'installed',
                    last_error TEXT,
                    installed_by INTEGER,
                    updated_by INTEGER
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE plugin_action_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id VARCHAR(255) NOT NULL,
                    action_id VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(128) NOT NULL,
                    execute_reason TEXT NOT NULL,
                    status VARCHAR(64) NOT NULL DEFAULT 'planned'
                )
                """
            )
            conn.commit()
            conn.close()

            module = types.ModuleType("plugin_migration")
            module.__file__ = str(MIGRATION_PATH)
            exec(MIGRATION_PATH.read_text(encoding="utf-8"), module.__dict__)
            module.DB_PATH = db_path
            self.assertTrue(module.run_migration())

            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(plugin_installations)")
            install_columns = {row[1] for row in cur.fetchall()}
            self.assertIn("bundle_sha256", install_columns)

            cur.execute("PRAGMA table_info(plugin_action_audits)")
            audit_columns = {row[1] for row in cur.fetchall()}
            self.assertIn("idempotency_key", audit_columns)

            cur.execute("PRAGMA index_list(plugin_action_audits)")
            indexes = {row[1] for row in cur.fetchall()}
            self.assertIn("idx_plugin_action_audits_idempotency", indexes)
            conn.close()


if __name__ == "__main__":
    unittest.main()
