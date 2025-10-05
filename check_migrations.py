#!/usr/bin/env python3
"""
Simple script to check and apply database migrations.

This script provides a user-friendly way to check for pending migrations
and apply them automatically.

Usage:
    python check_migrations.py
    python check_migrations.py --status
    python check_migrations.py --dry-run
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check and apply database migrations")
    parser.add_argument("--status", action="store_true", help="Show migration status only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be run without executing")
    
    args = parser.parse_args()
    
    try:
        from app.utils.migration_manager import MigrationManager
        
        manager = MigrationManager()
        
        if args.status:
            # Show status only
            status = manager.get_migration_status()
            
            print("🔍 Migration Status")
            print("=" * 50)
            print(f"Database exists: {'✅' if status['database_exists'] else '❌'}")
            print(f"Migrations table exists: {'✅' if status['migrations_table_exists'] else '❌'}")
            print(f"Applied migrations: {len(status['applied_migrations'])}")
            print(f"Pending migrations: {len(status['pending_migrations'])}")
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Status: {status['status']}")
            
            if status['applied_migrations']:
                print("\n✅ Applied migrations:")
                for migration in status['applied_migrations']:
                    print(f"  • {migration}")
            
            if status['pending_migrations']:
                print("\n⏳ Pending migrations:")
                for migration in status['pending_migrations']:
                    print(f"  • {migration}")
            else:
                print("\n🎉 No pending migrations - database is up to date!")
                
        else:
            # Run migrations
            print("🚀 Checking for pending migrations...")
            success, messages = manager.run_all_pending_migrations(args.dry_run)
            
            if args.dry_run:
                print("\n📋 DRY RUN - What would be executed:")
                print("=" * 50)
            else:
                print("\n🔄 Running migrations:")
                print("=" * 50)
            
            for message in messages:
                if "successfully" in message.lower():
                    print(f"✅ {message}")
                elif "failed" in message.lower() or "error" in message.lower():
                    print(f"❌ {message}")
                elif "found" in message.lower() and "pending" in message.lower():
                    print(f"🔍 {message}")
                else:
                    print(f"ℹ️  {message}")
            
            if not args.dry_run:
                if success:
                    print("\n🎉 All migrations completed successfully!")
                    print("✅ Your database is now up to date.")
                else:
                    print("\n❌ Some migrations failed.")
                    print("🔧 Please check the error messages above and try again.")
                    sys.exit(1)
            else:
                print("\n💡 This was a dry run. Use 'python check_migrations.py' to apply migrations.")
                
    except ImportError as e:
        print(f"❌ Failed to import migration manager: {e}")
        print("🔧 Make sure you're running this from the project root directory.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
