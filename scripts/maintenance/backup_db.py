#!/usr/bin/env python3
"""Backup utility for the MicroK8s Orchestrator database."""

import sys
import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import DATABASE_URL

def backup_database(backup_dir="backups"):
    """Create a backup of the database."""
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print(f"✗ Database not found at: {db_path}")
        return False
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"cluster_data_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Get file sizes for verification
        original_size = os.path.getsize(db_path)
        backup_size = os.path.getsize(backup_path)
        
        if original_size == backup_size:
            print(f"✓ Database backed up successfully!")
            print(f"  Original: {db_path} ({original_size} bytes)")
            print(f"  Backup: {backup_path} ({backup_size} bytes)")
            return True
        else:
            print(f"✗ Backup verification failed - size mismatch")
            return False
            
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return False

def list_backups(backup_dir="backups"):
    """List available backups."""
    if not os.path.exists(backup_dir):
        print(f"No backup directory found at: {backup_dir}")
        return
    
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('cluster_data_backup_') and f.endswith('.db')]
    
    if not backup_files:
        print(f"No backups found in: {backup_dir}")
        return
    
    print(f"Available backups in {backup_dir}:")
    backup_files.sort(reverse=True)  # Show newest first
    
    for backup_file in backup_files:
        backup_path = os.path.join(backup_dir, backup_file)
        size = os.path.getsize(backup_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
        print(f"  - {backup_file} ({size} bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

def restore_database(backup_file, backup_dir="backups"):
    """Restore database from backup."""
    backup_path = os.path.join(backup_dir, backup_file)
    
    if not os.path.exists(backup_path):
        print(f"✗ Backup file not found: {backup_path}")
        return False
    
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    try:
        # Create backup of current database if it exists
        if os.path.exists(db_path):
            current_backup = f"{db_path}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, current_backup)
            print(f"✓ Current database backed up to: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
        
        print(f"✓ Database restored successfully from: {backup_file}")
        return True
        
    except Exception as e:
        print(f"✗ Restore failed: {e}")
        return False

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Backup and restore MicroK8s Orchestrator database')
    parser.add_argument('action', choices=['backup', 'list', 'restore'], 
                       help='Action to perform')
    parser.add_argument('--backup-dir', default='backups',
                       help='Directory for backup files (default: backups)')
    parser.add_argument('--file', 
                       help='Backup file name for restore operation')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'backup':
            success = backup_database(args.backup_dir)
            sys.exit(0 if success else 1)
            
        elif args.action == 'list':
            list_backups(args.backup_dir)
            
        elif args.action == 'restore':
            if not args.file:
                print("✗ --file argument required for restore operation")
                sys.exit(1)
            success = restore_database(args.file, args.backup_dir)
            sys.exit(0 if success else 1)
            
    except Exception as e:
        print(f"✗ Operation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
