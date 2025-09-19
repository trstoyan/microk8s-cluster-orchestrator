#!/usr/bin/env python3
"""Detect MicroK8s status on nodes via SSH."""

import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import get_session
from app.models.node import Node

def check_microk8s_on_node(node):
    """Check MicroK8s status on a node via SSH."""
    try:
        # Build SSH command
        ssh_cmd = [
            'ssh',
            '-i', node.ssh_key_path.replace('~', str(Path.home())) if node.ssh_key_path else '',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f"{node.ssh_user}@{node.ip_address}",
            'which microk8s && microk8s status'
        ]
        
        # Remove empty key path if not provided
        if not node.ssh_key_path:
            ssh_cmd = [cmd for cmd in ssh_cmd if cmd != '-i' and cmd != '']
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            output = result.stdout.lower()
            if 'microk8s is running' in output:
                return 'running', result.stdout
            elif 'microk8s is not running' in output:
                return 'stopped', result.stdout
            elif '/snap/bin/microk8s' in output or 'microk8s' in output:
                return 'installed', result.stdout
            else:
                return 'installed', result.stdout
        else:
            # MicroK8s not found or other error
            return 'not_installed', result.stderr
            
    except subprocess.TimeoutExpired:
        return 'error', 'SSH connection timeout'
    except Exception as e:
        return 'error', str(e)

def detect_and_update_node(node_id):
    """Detect and update MicroK8s status for a specific node."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print(f"✗ Node with ID {node_id} not found")
            return False
        
        print(f"🔍 Checking MicroK8s status on {node.hostname} ({node.ip_address})...")
        
        status, output = check_microk8s_on_node(node)
        
        # Update node status
        old_status = node.microk8s_status
        node.microk8s_status = status
        node.last_seen = datetime.utcnow()
        node.status = 'online' if status != 'error' else 'offline'
        
        session.commit()
        
        print(f"✓ Updated node '{node.hostname}':")
        print(f"  MicroK8s status: {old_status} → {status}")
        print(f"  Node status: {node.status}")
        print(f"  Last seen: {node.last_seen}")
        
        if status == 'running':
            print(f"\n📋 MicroK8s details:")
            # Show first few lines of status output
            lines = output.strip().split('\n')[:10]
            for line in lines:
                print(f"    {line}")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"✗ Failed to update node status: {e}")
        return False
    finally:
        session.close()

def detect_all_nodes():
    """Detect MicroK8s status on all nodes."""
    session = get_session()
    try:
        nodes = session.query(Node).all()
        if not nodes:
            print("ℹ No nodes found in database")
            return True
        
        success_count = 0
        for node in nodes:
            print(f"\n{'='*60}")
            if detect_and_update_node(node.id):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"✓ Updated {success_count}/{len(nodes)} nodes successfully")
        return success_count == len(nodes)
        
    finally:
        session.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Detect MicroK8s status on nodes')
    parser.add_argument('--node-id', type=int, help='Specific node ID to check')
    parser.add_argument('--all', action='store_true', help='Check all nodes')
    
    args = parser.parse_args()
    
    if args.node_id:
        success = detect_and_update_node(args.node_id)
    elif args.all:
        success = detect_all_nodes()
    else:
        print("Please specify --node-id or --all")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
