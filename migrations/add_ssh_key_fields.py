#!/usr/bin/env python3
"""
Database migration to add SSH key management fields to the nodes table.

This migration adds the following fields to the nodes table:
- ssh_key_generated: Boolean indicating if SSH key pair has been generated
- ssh_public_key: Text field containing the public key content
- ssh_key_fingerprint: String field for key fingerprint identification
- ssh_key_status: String field for key status (not_generated, generated, deployed, tested, failed)
- ssh_connection_tested: Boolean indicating if SSH connection has been tested
- ssh_connection_test_result: Text field for last SSH connection test result (JSON)
- ssh_setup_instructions: Text field for setup instructions for the user

This migration can be run in two ways:
1. Through the migration manager: python cli.py migrate
2. Directly: python migrations/add_ssh_key_fields.py
"""

import sys
import os
import sqlite3
from pathlib import Path

def run_migration():
    """Run the database migration."""
    # Database path
    db_path = Path(__file__).parent.parent / "cluster_data.db"
    
    if not db_path.exists():
        print("Database file not found. Please run the application first to create the database.")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Running SSH key fields migration...")
        
        # Check if the new fields already exist
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_fields = [
            ('ssh_key_generated', 'BOOLEAN DEFAULT 0'),
            ('ssh_public_key', 'TEXT'),
            ('ssh_key_fingerprint', 'VARCHAR(100)'),
            ('ssh_key_status', 'VARCHAR(50) DEFAULT "not_generated"'),
            ('ssh_connection_tested', 'BOOLEAN DEFAULT 0'),
            ('ssh_connection_test_result', 'TEXT'),
            ('ssh_setup_instructions', 'TEXT')
        ]
        
        # Add new fields if they don't exist
        for field_name, field_definition in new_fields:
            if field_name not in columns:
                print(f"Adding field: {field_name}")
                cursor.execute(f"ALTER TABLE nodes ADD COLUMN {field_name} {field_definition}")
            else:
                print(f"Field {field_name} already exists, skipping...")
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
        # Show current table structure
        print("\nCurrent nodes table structure:")
        cursor.execute("PRAGMA table_info(nodes)")
        columns = cursor.fetchall()
        for column in columns:
            print(f"  {column[1]} ({column[2]})")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def rollback_migration():
    """Rollback the migration by removing the new fields."""
    db_path = project_root / "cluster_data.db"
    
    if not db_path.exists():
        print("Database file not found.")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Rolling back SSH key fields migration...")
        
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # This is a destructive operation, so we'll create a backup first
        
        # Create backup
        backup_path = project_root / f"cluster_data_backup_{int(__import__('time').time())}.db"
        print(f"Creating backup: {backup_path}")
        
        # Copy the database
        import shutil
        shutil.copy2(db_path, backup_path)
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(nodes)")
        columns = cursor.fetchall()
        
        # Filter out the new SSH key fields
        old_columns = [col for col in columns if not col[1].startswith('ssh_') or col[1] == 'ssh_key_path']
        
        # Create new table without SSH key fields
        old_column_defs = []
        for col in old_columns:
            col_def = f"{col[1]} {col[2]}"
            if col[3]:  # NOT NULL
                col_def += " NOT NULL"
            if col[4] is not None:  # DEFAULT value
                col_def += f" DEFAULT {col[4]}"
            old_column_defs.append(col_def)
        
        # Create new table
        cursor.execute(f"""
            CREATE TABLE nodes_new (
                {', '.join(old_column_defs)}
            )
        """)
        
        # Copy data from old table (excluding SSH key fields)
        old_column_names = [col[1] for col in old_columns]
        cursor.execute(f"""
            INSERT INTO nodes_new ({', '.join(old_column_names)})
            SELECT {', '.join(old_column_names)} FROM nodes
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE nodes")
        cursor.execute("ALTER TABLE nodes_new RENAME TO nodes")
        
        conn.commit()
        print("Rollback completed successfully!")
        print(f"Backup saved as: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"Rollback failed: {e}")
        if conn:
            conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SSH key fields migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        if input("Are you sure you want to rollback the migration? This will remove SSH key fields. (y/N): ").lower() == 'y':
            success = rollback_migration()
        else:
            print("Rollback cancelled.")
            success = True
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
