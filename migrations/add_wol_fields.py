#!/usr/bin/env python3
"""
Database migration to add Wake-on-LAN (WoL) fields to the nodes table.

This migration adds the following fields to the nodes table:
- wol_enabled: Boolean indicating if WoL is enabled
- wol_mac_address: MAC address for WoL (format: XX:XX:XX:XX:XX:XX)
- wol_method: Wake method (ethernet, wifi, pci, usb)
- wol_broadcast_address: Broadcast address for WoL packet (optional)
- wol_port: UDP port for WoL packet (default: 9)
- is_virtual_node: Boolean indicating if this is a virtual node
- proxmox_vm_id: Proxmox VM ID if this is a virtual node
- proxmox_host_id: ID of the Proxmox host running this VM

This migration can be run in two ways:
1. Through the migration manager: python cli.py migrate
2. Directly: python migrations/add_wol_fields.py
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
        
        print("Running WoL fields migration...")
        
        # Check if the new fields already exist
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_fields = [
            ('wol_enabled', 'BOOLEAN DEFAULT 0'),
            ('wol_mac_address', 'VARCHAR(17)'),
            ('wol_method', 'VARCHAR(20) DEFAULT "ethernet"'),
            ('wol_broadcast_address', 'VARCHAR(45)'),
            ('wol_port', 'INTEGER DEFAULT 9'),
            ('is_virtual_node', 'BOOLEAN DEFAULT 0'),
            ('proxmox_vm_id', 'INTEGER'),
            ('proxmox_host_id', 'INTEGER')
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

def rollback_migration():
    """Rollback the migration by removing the new fields."""
    db_path = Path(__file__).parent.parent / "cluster_data.db"
    
    if not db_path.exists():
        print("Database file not found.")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Rolling back WoL fields migration...")
        
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # This is a destructive operation, so we'll create a backup first
        
        # Create backup
        backup_path = Path(__file__).parent.parent / f"cluster_data_backup_{int(__import__('time').time())}.db"
        print(f"Creating backup: {backup_path}")
        
        # Copy the database
        import shutil
        shutil.copy2(db_path, backup_path)
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(nodes)")
        columns = cursor.fetchall()
        
        # Filter out the new WoL fields
        wol_fields = {'wol_enabled', 'wol_mac_address', 'wol_method', 'wol_broadcast_address', 
                     'wol_port', 'is_virtual_node', 'proxmox_vm_id', 'proxmox_host_id'}
        old_columns = [col for col in columns if col[1] not in wol_fields]
        
        # Create new table without WoL fields
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
        
        # Copy data from old table (excluding WoL fields)
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
    
    parser = argparse.ArgumentParser(description="WoL fields migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        if input("Are you sure you want to rollback the migration? This will remove WoL fields. (y/N): ").lower() == 'y':
            success = rollback_migration()
        else:
            print("Rollback cancelled.")
            success = True
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
