#!/usr/bin/env python3
"""
Fix SSH Key Paths Migration
Converts relative SSH key paths to absolute paths for existing nodes
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models.database import db
from app.models.flask_models import Node

def fix_ssh_key_paths():
    """Convert relative SSH key paths to absolute paths"""
    app = create_app()
    
    with app.app_context():
        # Get project root
        project_root = Path(__file__).parent.parent.absolute()
        
        print("🔧 Fixing SSH key paths for existing nodes...")
        print(f"📁 Project root: {project_root}")
        print()
        
        nodes = Node.query.all()
        fixed_count = 0
        
        for node in nodes:
            if not node.ssh_key_path:
                print(f"⏭️  Node {node.hostname} (ID: {node.id}): No SSH key path set")
                continue
            
            # Check if path is already absolute
            key_path = Path(node.ssh_key_path)
            if key_path.is_absolute():
                print(f"✅ Node {node.hostname} (ID: {node.id}): Already absolute path")
                continue
            
            # Convert to absolute path
            absolute_path = (project_root / node.ssh_key_path).absolute()
            
            # Verify the key file exists
            if not absolute_path.exists():
                print(f"⚠️  Node {node.hostname} (ID: {node.id}): Key file not found at {absolute_path}")
                print(f"    Original path: {node.ssh_key_path}")
                continue
            
            # Update the node
            old_path = node.ssh_key_path
            node.ssh_key_path = str(absolute_path)
            fixed_count += 1
            
            print(f"🔄 Node {node.hostname} (ID: {node.id}):")
            print(f"    Old: {old_path}")
            print(f"    New: {node.ssh_key_path}")
            print()
        
        if fixed_count > 0:
            db.session.commit()
            print(f"✅ Fixed {fixed_count} node(s) with relative SSH key paths")
        else:
            print("✅ All nodes already have correct SSH key paths (or no keys)")
        
        print()
        print("Migration complete!")

if __name__ == '__main__':
    fix_ssh_key_paths()

