#!/usr/bin/env python3
"""Add plugin platform registry and action audit tables."""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "cluster_data.db"


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def run_migration():
    """Create plugin_installations and plugin_action_audits tables if missing."""
    if not DB_PATH.exists():
        print("Database file not found. Please run the application first to create the database.")
        return False

    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        if not _table_exists(cursor, "plugin_installations"):
            cursor.execute(
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
                    updated_by INTEGER,
                    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (installed_by) REFERENCES users(id),
                    FOREIGN KEY (updated_by) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX idx_plugin_installations_enabled ON plugin_installations(enabled)"
            )

        if not _table_exists(cursor, "plugin_action_audits"):
            cursor.execute(
                """
                CREATE TABLE plugin_action_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id VARCHAR(255) NOT NULL,
                    action_id VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(128) NOT NULL,
                    execute_reason TEXT NOT NULL,
                    status VARCHAR(64) NOT NULL DEFAULT 'planned',
                    plan_payload TEXT,
                    result_payload TEXT,
                    error_message TEXT,
                    requested_by INTEGER,
                    approved_by INTEGER,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    FOREIGN KEY (requested_by) REFERENCES users(id),
                    FOREIGN KEY (approved_by) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX idx_plugin_action_audits_plugin_action ON plugin_action_audits(plugin_id, action_id)"
            )
            cursor.execute(
                "CREATE INDEX idx_plugin_action_audits_status ON plugin_action_audits(status)"
            )

        conn.commit()
        print("Plugin platform tables migration completed successfully.")
        return True
    except Exception as exc:
        print(f"Migration failed: {exc}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
