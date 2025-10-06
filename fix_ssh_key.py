#!/usr/bin/env python3
"""Fix SSH key path issues."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.database import db
from app.models.flask_models import Node
from pathlib import Path

def main():
    app = create_app()
    
    with app.app_context():
        # Get node 1
        node = Node.query.get(1)
        if not node:
            print("Node 1 not found")
            return
            
        print(f"Current SSH key path: {node.ssh_key_path}")
        
        # Check if the key exists with tilde expansion
        if node.ssh_key_path and node.ssh_key_path.startswith('~/'):
            expanded_path = os.path.expanduser(node.ssh_key_path)
            print(f"Expanded path: {expanded_path}")
            
            if os.path.exists(expanded_path):
                print("Key file exists with tilde expansion")
                # Update the path to absolute path
                node.ssh_key_path = expanded_path
                node.ssh_key_generated = True
                node.ssh_key_status = 'generated'
                
                # Get key info
                from app.services.ssh_key_manager import SSHKeyManager
                ssh_manager = SSHKeyManager()
                try:
                    key_info = ssh_manager.get_key_info(expanded_path)
                    if key_info:
                        node.ssh_public_key = key_info.get('public_key', '')
                        node.ssh_key_fingerprint = key_info.get('fingerprint', '')
                        print(f"Updated key info: {key_info}")
                except Exception as e:
                    print(f"Error getting key info: {e}")
                
                db.session.commit()
                print("Node SSH key path updated successfully")
            else:
                print("Key file does not exist even with tilde expansion")
                
                # Check if there are keys in the ssh_keys directory
                ssh_keys_dir = Path('ssh_keys')
                if ssh_keys_dir.exists():
                    print("Available keys in ssh_keys directory:")
                    for key_file in ssh_keys_dir.glob('node_1_*'):
                        if not key_file.name.endswith('.pub'):
                            print(f"  {key_file}")
                            
                            # Update to use this key
                            node.ssh_key_path = str(key_file.absolute())
                            node.ssh_key_generated = True
                            node.ssh_key_status = 'generated'
                            
                            # Get key info
                            try:
                                key_info = ssh_manager.get_key_info(str(key_file))
                                if key_info:
                                    node.ssh_public_key = key_info.get('public_key', '')
                                    node.ssh_key_fingerprint = key_info.get('fingerprint', '')
                                    print(f"Updated to use key: {key_file}")
                                    print(f"Key info: {key_info}")
                            except Exception as e:
                                print(f"Error getting key info: {e}")
                            
                            db.session.commit()
                            print("Node SSH key updated to use ssh_keys directory")
                            break
        else:
            print("SSH key path does not start with ~/")

if __name__ == "__main__":
    main()
