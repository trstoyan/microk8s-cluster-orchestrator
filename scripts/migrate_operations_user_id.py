#!/usr/bin/env python3
"""Database migration script to add user_id column to operations table."""

import os
import sys
import sqlite3

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.database import db
from app.utils.config import config

def migrate_operations_table():
    """Add user_id column to operations table."""
    
    # Get database path from config
    db_path = config.get('database.path', 'cluster_data.db')
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect directly to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(operations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("✓ user_id column already exists in operations table")
            conn.close()
            return
        
        print("Adding user_id column to operations table...")
        
        # Add the user_id column
        cursor.execute("ALTER TABLE operations ADD COLUMN user_id INTEGER")
        
        # Add foreign key constraint (SQLite doesn't support adding foreign keys to existing tables)
        # We'll handle the relationship in the model
        
        conn.commit()
        print("✓ Successfully added user_id column to operations table")
        
        # Update existing operations to set user_id to NULL (they'll show as 'system' operations)
        cursor.execute("SELECT COUNT(*) FROM operations WHERE user_id IS NULL")
        null_operations = cursor.fetchone()[0]
        
        if null_operations > 0:
            print(f"ℹ {null_operations} existing operations will show as 'system' operations")
        
        conn.close()
        
        print("\nDatabase migration completed successfully!")
        print("The application can now track which user initiated each operation.")
        
    except sqlite3.Error as e:
        print(f"✗ Database migration failed: {e}")
        if conn:
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

def verify_migration():
    """Verify the migration was successful using SQLAlchemy."""
    try:
        app = create_app()
        with app.app_context():
            # Try to query operations with user_id
            from app.models.flask_models import Operation
            operations = Operation.query.limit(1).all()
            print("✓ Migration verification successful - operations table can be queried with user_id")
            
    except Exception as e:
        print(f"✗ Migration verification failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("MicroK8s Cluster Orchestrator - Operations Table Migration")
    print("=" * 60)
    print()
    
    migrate_operations_table()
    
    print("\nVerifying migration...")
    if verify_migration():
        print("\n🎉 Migration completed successfully!")
        print("You can now restart the web application.")
    else:
        print("\n❌ Migration verification failed!")
        print("Please check the error messages above.")
        sys.exit(1)
