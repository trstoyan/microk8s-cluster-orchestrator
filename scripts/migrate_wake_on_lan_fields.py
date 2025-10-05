#!/usr/bin/env python3
"""
Database migration script to add Wake-on-LAN fields to the nodes table.
This script adds the necessary columns for Wake-on-LAN functionality.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the parent directory to the Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def backup_database(db_path):
    """Create a backup of the database before migration."""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Creating database backup: {backup_path}")
    
    # Copy the database file
    import shutil
    shutil.copy2(db_path, backup_path)
    
    return backup_path

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_nodes_table(cursor):
    """Add Wake-on-LAN fields to the nodes table."""
    print("Checking nodes table structure...")
    
    # Check if nodes table exists
    if not check_table_exists(cursor, 'nodes'):
        print("ERROR: nodes table does not exist!")
        return False
    
    # List of new columns to add
    new_columns = [
        ('wol_enabled', 'BOOLEAN DEFAULT 0'),
        ('wol_mac_address', 'VARCHAR(17)'),
        ('wol_method', 'VARCHAR(20) DEFAULT "ethernet"'),
        ('wol_broadcast_address', 'VARCHAR(45)'),
        ('wol_port', 'INTEGER DEFAULT 9'),
        ('is_virtual_node', 'BOOLEAN DEFAULT 0'),
        ('proxmox_vm_id', 'INTEGER'),
        ('proxmox_host_id', 'INTEGER')
    ]
    
    # Add each column if it doesn't exist
    for column_name, column_definition in new_columns:
        if not check_column_exists(cursor, 'nodes', column_name):
            print(f"Adding column: {column_name}")
            cursor.execute(f"ALTER TABLE nodes ADD COLUMN {column_name} {column_definition}")
        else:
            print(f"Column {column_name} already exists, skipping...")
    
    return True

def update_existing_nodes(cursor):
    """Update existing nodes with default Wake-on-LAN values."""
    print("Updating existing nodes with default Wake-on-LAN values...")
    
    # Get all existing nodes
    cursor.execute("SELECT id, hostname FROM nodes")
    nodes = cursor.fetchall()
    
    if not nodes:
        print("No existing nodes found.")
        return True
    
    print(f"Found {len(nodes)} existing nodes.")
    
    # Update each node with default values
    for node_id, hostname in nodes:
        print(f"Updating node {hostname} (ID: {node_id})")
        
        # Set default values for new columns
        cursor.execute("""
            UPDATE nodes SET 
                wol_enabled = 0,
                wol_method = 'ethernet',
                wol_port = 9,
                is_virtual_node = 0
            WHERE id = ?
        """, (node_id,))
    
    print("All existing nodes updated with default Wake-on-LAN values.")
    return True

def verify_migration(cursor):
    """Verify that the migration was successful."""
    print("Verifying migration...")
    
    # Check if all new columns exist
    required_columns = [
        'wol_enabled', 'wol_mac_address', 'wol_method', 'wol_broadcast_address',
        'wol_port', 'is_virtual_node', 'proxmox_vm_id', 'proxmox_host_id'
    ]
    
    cursor.execute("PRAGMA table_info(nodes)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    missing_columns = [col for col in required_columns if col not in existing_columns]
    
    if missing_columns:
        print(f"ERROR: Missing columns after migration: {missing_columns}")
        return False
    
    print("All required Wake-on-LAN columns are present.")
    
    # Check node count
    cursor.execute("SELECT COUNT(*) FROM nodes")
    node_count = cursor.fetchone()[0]
    print(f"Total nodes in database: {node_count}")
    
    # Check nodes with WoL enabled
    cursor.execute("SELECT COUNT(*) FROM nodes WHERE wol_enabled = 1")
    wol_enabled_count = cursor.fetchone()[0]
    print(f"Nodes with Wake-on-LAN enabled: {wol_enabled_count}")
    
    # Check virtual nodes
    cursor.execute("SELECT COUNT(*) FROM nodes WHERE is_virtual_node = 1")
    virtual_nodes_count = cursor.fetchone()[0]
    print(f"Virtual nodes: {virtual_nodes_count}")
    
    return True

def main():
    """Main migration function."""
    print("Wake-on-LAN Database Migration Script")
    print("=" * 40)
    
    # Determine database path
    db_path = "cluster_data.db"
    if not os.path.exists(db_path):
        db_path = "instance/cluster_data.db"
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        print("Please ensure you're running this script from the project root directory.")
        return 1
    
    print(f"Using database: {db_path}")
    
    # Create backup
    backup_path = backup_database(db_path)
    print(f"Backup created: {backup_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\nStarting migration...")
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Migrate nodes table
        if not migrate_nodes_table(cursor):
            print("ERROR: Failed to migrate nodes table")
            return 1
        
        # Update existing nodes
        if not update_existing_nodes(cursor):
            print("ERROR: Failed to update existing nodes")
            return 1
        
        # Commit changes
        conn.commit()
        print("\nMigration completed successfully!")
        
        # Verify migration
        if not verify_migration(cursor):
            print("ERROR: Migration verification failed")
            return 1
        
        print("\nMigration verification passed!")
        print("\nNext steps:")
        print("1. Restart the orchestrator application")
        print("2. Use the web interface or API to configure Wake-on-LAN settings for your nodes")
        print("3. Collect MAC addresses using the 'Collect MAC Addresses' functionality")
        print("4. Configure Wake-on-LAN rules in the UPS power management section")
        
        # Close connection
        conn.close()
        
        return 0
        
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        
        # Restore from backup
        print(f"Restoring from backup: {backup_path}")
        import shutil
        shutil.copy2(backup_path, db_path)
        print("Database restored from backup.")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())

