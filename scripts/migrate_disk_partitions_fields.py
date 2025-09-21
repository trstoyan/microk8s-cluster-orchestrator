#!/usr/bin/env python3
"""
Database migration script to add detailed disk partition and storage volume fields to nodes table.
Run this script to update the database schema for enhanced storage reporting functionality.
"""

import os
import sys
import sqlite3
from datetime import datetime

def get_db_path():
    """Get the path to the database file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return os.path.join(project_root, 'cluster_data.db')

def backup_database(db_path):
    """Create a backup of the database before migration."""
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'cluster_data_backup_{timestamp}_disk_partitions_migration.db')
    
    # Copy database file
    with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
        dst.write(src.read())
    
    print(f"Database backed up to: {backup_path}")
    return backup_path

def check_columns_exist(cursor, table_name, columns):
    """Check if columns already exist in the table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    missing_columns = []
    for column in columns:
        if column not in existing_columns:
            missing_columns.append(column)
    
    return missing_columns

def migrate_database():
    """Add detailed disk partition and storage volume fields to the nodes table."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        print("Please ensure the application has been initialized and the database exists.")
        return False
    
    print(f"Migrating database at: {db_path}")
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Define new columns to add
        new_columns = [
            'disk_partitions_info',
            'storage_volumes_info'
        ]
        
        # Check which columns are missing
        missing_columns = check_columns_exist(cursor, 'nodes', new_columns)
        
        if not missing_columns:
            print("All disk partition columns already exist. No migration needed.")
            conn.close()
            return True
        
        print(f"Adding {len(missing_columns)} new columns to nodes table...")
        
        # Add missing columns
        column_definitions = {
            'disk_partitions_info': 'TEXT',
            'storage_volumes_info': 'TEXT'
        }
        
        for column in missing_columns:
            column_type = column_definitions[column]
            sql = f"ALTER TABLE nodes ADD COLUMN {column} {column_type}"
            print(f"  Adding column: {column} ({column_type})")
            cursor.execute(sql)
        
        # Commit changes
        conn.commit()
        print(f"Successfully added {len(missing_columns)} columns to nodes table.")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(nodes)")
        all_columns = [row[1] for row in cursor.fetchall()]
        
        print("\nCurrent nodes table schema:")
        for i, column in enumerate(all_columns, 1):
            print(f"  {i:2d}. {column}")
        
        # Check if all new columns are present
        verification_missing = check_columns_exist(cursor, 'nodes', new_columns)
        if verification_missing:
            print(f"\nWarning: Some columns are still missing: {verification_missing}")
            return False
        else:
            print(f"\nMigration completed successfully! All {len(new_columns)} disk partition columns are now present.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        print(f"Database backup is available at: {backup_path}")
        
        # Try to restore from backup
        try:
            print("Attempting to restore from backup...")
            with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
                dst.write(src.read())
            print("Database restored from backup.")
        except Exception as restore_error:
            print(f"Failed to restore backup: {restore_error}")
            print("Please manually restore from backup if needed.")
        
        return False

def main():
    """Main function."""
    print("MicroK8s Cluster Orchestrator - Disk Partitions Fields Migration")
    print("=" * 70)
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("This script adds detailed disk partition and storage volume fields to the nodes table.")
        print("Usage: python migrate_disk_partitions_fields.py")
        print("\nThis migration adds the following fields:")
        print("- disk_partitions_info: Detailed disk partitions, LVM, RAID info (JSON)")
        print("- storage_volumes_info: PVCs, PVs, Docker volumes info (JSON)")
        print("\nThese fields will contain:")
        print("- Physical disk information")
        print("- All partitions and filesystems")
        print("- LVM volume groups and logical volumes")
        print("- RAID information")
        print("- Kubernetes PVCs and PVs")
        print("- Docker/Podman volumes")
        return
    
    success = migrate_database()
    
    if success:
        print("\n✓ Migration completed successfully!")
        print("You can now collect detailed disk partition and storage volume information.")
        print("To collect hardware data, use the Hardware Report page in the web interface")
        print("or run: python cli.py hardware-report collect")
    else:
        print("\n✗ Migration failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == '__main__':
    main()
