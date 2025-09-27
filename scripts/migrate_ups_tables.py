#!/usr/bin/env python3
"""
Database migration script to add UPS and UPS-Cluster rules tables.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.database import db, Base
from app.models.ups import UPS
from app.models.ups_cluster_rule import UPSClusterRule


def migrate_ups_tables():
    """Create UPS and UPS-Cluster rules tables."""
    try:
        print("Creating UPS and UPS-Cluster rules tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=db.engine)
        
        print("✅ UPS and UPS-Cluster rules tables created successfully")
        
        # Verify tables were created
        with db.engine.connect() as conn:
            # Check UPS table
            result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='ups'"))
            if result.fetchone():
                print("✅ UPS table created")
            else:
                print("❌ UPS table not found")
                return False
            
            # Check UPS-Cluster rules table
            result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='ups_cluster_rules'"))
            if result.fetchone():
                print("✅ UPS-Cluster rules table created")
            else:
                print("❌ UPS-Cluster rules table not found")
                return False
            
            # Show table schemas
            print("\n📋 UPS Table Schema:")
            result = conn.execute(db.text("PRAGMA table_info(ups)"))
            for row in result:
                print(f"  {row[1]} ({row[2]})")
            
            print("\n📋 UPS-Cluster Rules Table Schema:")
            result = conn.execute(db.text("PRAGMA table_info(ups_cluster_rules)"))
            for row in result:
                print(f"  {row[1]} ({row[2]})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating UPS tables: {e}")
        return False


def main():
    """Main migration function."""
    print("🚀 Starting UPS database migration...")
    
    # Initialize Flask app context
    from app import create_app
    app = create_app()
    
    with app.app_context():
        success = migrate_ups_tables()
        
        if success:
            print("\n🎉 UPS database migration completed successfully!")
            print("\nNext steps:")
            print("1. Install NUT packages: sudo apt install nut nut-client nut-server nut-driver")
            print("2. Use the UPS scanner to detect connected UPS devices")
            print("3. Configure power management rules for your clusters")
        else:
            print("\n💥 UPS database migration failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
