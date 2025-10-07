#!/usr/bin/env python3
"""Migration to add Longhorn prerequisites fields to nodes table."""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add Longhorn prerequisites fields to the nodes table."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'cluster_data.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('longhorn_prerequisites_met', 'BOOLEAN DEFAULT 0'),
            ('longhorn_prerequisites_status', 'VARCHAR(50) DEFAULT "not_checked"'),
            ('longhorn_missing_packages', 'TEXT'),
            ('longhorn_missing_commands', 'TEXT'),
            ('longhorn_services_status', 'TEXT'),
            ('longhorn_storage_info', 'TEXT'),
            ('longhorn_last_check', 'DATETIME')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE nodes ADD COLUMN {column_name} {column_type}")
            else:
                print(f"Column {column_name} already exists, skipping")
        
        conn.commit()
        conn.close()
        
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    migrate_database()
