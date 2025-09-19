#!/usr/bin/env python3
"""Initialize the database with proper table creation."""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from app.models.database import Base, DATABASE_URL
from app.models.node import Node
from app.models.cluster import Cluster
from app.models.operation import Operation
from app.models.configuration import Configuration
from app.models.router_switch import RouterSwitch

def init_database(force=False):
    """Initialize the database with all tables."""
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    if os.path.exists(db_path) and not force:
        print(f"Database already exists at: {db_path}")
        print("Use --force to recreate the database")
        return False
    
    if force and os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    print(f"Creating database at: {DATABASE_URL}")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database tables created successfully!")
    print("Tables created:")
    for table in Base.metadata.tables.keys():
        print(f"  - {table}")
    
    return True

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Initialize the MicroK8s Orchestrator database')
    parser.add_argument('--force', action='store_true', 
                       help='Force recreation of database if it already exists')
    
    args = parser.parse_args()
    
    try:
        success = init_database(force=args.force)
        if success:
            print("\n✓ Database initialization completed successfully!")
            print("You can now use the CLI commands to manage nodes and clusters.")
        else:
            print("\n⚠ Database initialization skipped.")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
