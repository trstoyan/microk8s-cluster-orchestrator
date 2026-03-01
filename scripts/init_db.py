#!/usr/bin/env python3
"""Initialize the database using the current Flask-SQLAlchemy models."""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules.
sys.path.append(str(Path(__file__).parent.parent))

from app import create_app
from app.models.database import db, DATABASE_PATH


def init_database(force: bool = False) -> bool:
    """Initialize all database tables from the active Flask models."""
    abs_db_path = os.path.abspath(DATABASE_PATH)
    db_exists = os.path.exists(abs_db_path)

    if db_exists and not force:
        print(f"Database already exists at: {abs_db_path}")
        print("Use --force to recreate the database")
        return False

    app = create_app()
    with app.app_context():
        if force and db_exists:
            db.drop_all()
            print(f"Dropped existing tables in: {abs_db_path}")

        db.create_all()
        print(f"Initialized database at: {abs_db_path}")
        print("Tables available:")
        for table in sorted(db.metadata.tables.keys()):
            print(f"  - {table}")

    return True


def main() -> None:
    """Parse CLI args and initialize database."""
    parser = argparse.ArgumentParser(
        description="Initialize the MicroK8s Orchestrator database"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of database schema even if database exists",
    )
    args = parser.parse_args()

    try:
        success = init_database(force=args.force)
        if success:
            print("\n✓ Database initialization completed successfully!")
            print("You can now use the CLI commands to manage nodes and clusters.")
            return
        print("\n⚠ Database initialization skipped.")
        sys.exit(1)
    except Exception as exc:
        print(f"\n✗ Database initialization failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
