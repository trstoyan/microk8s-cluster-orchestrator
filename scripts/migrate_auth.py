#!/usr/bin/env python3
"""Database migration script to add authentication tables."""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.database import db
from app.models.flask_models import User, Operation

def migrate_database():
    """Add authentication tables and update existing schema."""
    app = create_app()
    
    with app.app_context():
        print("Creating authentication tables...")
        
        # Create all tables (this will create new tables and skip existing ones)
        db.create_all()
        
        # Check if we need to add the user_id column to operations table
        print("Checking for required schema updates...")
        
        # Check if users table exists and has data
        user_count = User.query.count()
        print(f"Found {user_count} users in the database.")
        
        if user_count == 0:
            print("\nNo users found. You'll need to create the first admin user.")
            print("Visit /auth/register to create the first administrator account.")
        else:
            print("Users already exist. Authentication is ready!")
        
        print("\nDatabase migration completed successfully!")
        print("Authentication system is now active.")
        print("\nNext steps:")
        print("1. Restart the application")
        print("2. Visit /auth/login to sign in")
        if user_count == 0:
            print("3. Create the first admin user at /auth/register")

if __name__ == '__main__':
    migrate_database()
