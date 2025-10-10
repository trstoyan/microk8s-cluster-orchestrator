#!/usr/bin/env python3
"""
Add metadata column to operations table
For storing discovered nodes and other scan results
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / 'cluster_data.db'

def migrate():
    """Add metadata column to operations table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(operations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'metadata' in columns:
            print("✅ Column 'metadata' already exists in operations table")
            return
        
        print("🔄 Adding 'metadata' column to operations table...")
        
        # Add the column
        cursor.execute("""
            ALTER TABLE operations 
            ADD COLUMN metadata TEXT
        """)
        
        conn.commit()
        print("✅ Successfully added 'metadata' column to operations table")
        print("   This column stores discovered nodes and other scan results")
        
    except sqlite3.Error as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

