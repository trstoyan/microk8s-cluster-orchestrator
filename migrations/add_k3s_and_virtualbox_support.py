#!/usr/bin/env python3
"""Add k3s runtime and VirtualBox provider support fields."""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "cluster_data.db"


def run_migration():
    """Add runtime/provider fields to clusters and nodes tables."""
    if not DB_PATH.exists():
        print("Database file not found. Please run the application first to create the database.")
        return False

    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        table_columns = {}
        for table in ("clusters", "nodes"):
            cursor.execute(f"PRAGMA table_info({table})")
            table_columns[table] = {column[1] for column in cursor.fetchall()}

        cluster_columns = [
            ("kubernetes_distribution", 'VARCHAR(50) DEFAULT "microk8s"'),
            ("infrastructure_provider", 'VARCHAR(50) DEFAULT "generic"'),
        ]
        node_columns = [
            ("kubernetes_version", "VARCHAR(50)"),
            ("kubernetes_status", 'VARCHAR(50) DEFAULT "not_installed"'),
            ("virtualization_provider", 'VARCHAR(50) DEFAULT "generic"'),
            ("provider_vm_name", "VARCHAR(255)"),
            ("provider_vm_group", "VARCHAR(255)"),
            ("provider_metadata", "TEXT"),
        ]

        for column_name, definition in cluster_columns:
            if column_name not in table_columns["clusters"]:
                print(f"Adding clusters.{column_name}")
                cursor.execute(f"ALTER TABLE clusters ADD COLUMN {column_name} {definition}")

        for column_name, definition in node_columns:
            if column_name not in table_columns["nodes"]:
                print(f"Adding nodes.{column_name}")
                cursor.execute(f"ALTER TABLE nodes ADD COLUMN {column_name} {definition}")

        # Backfill generic runtime fields from existing MicroK8s fields.
        cursor.execute(
            """
            UPDATE clusters
            SET kubernetes_distribution = COALESCE(NULLIF(kubernetes_distribution, ''), 'microk8s'),
                infrastructure_provider = COALESCE(NULLIF(infrastructure_provider, ''), 'generic')
            """
        )
        cursor.execute(
            """
            UPDATE nodes
            SET kubernetes_status = COALESCE(NULLIF(microk8s_status, ''), NULLIF(kubernetes_status, ''), 'not_installed'),
                kubernetes_version = COALESCE(NULLIF(kubernetes_version, ''), microk8s_version),
                virtualization_provider = COALESCE(NULLIF(virtualization_provider, ''), 'generic')
            """
        )

        conn.commit()
        print("k3s/VirtualBox support migration completed successfully.")
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
