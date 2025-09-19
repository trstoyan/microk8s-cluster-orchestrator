#!/usr/bin/env python3
"""Manually update node MicroK8s status."""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import get_session
from app.models.node import Node

def update_node_microk8s_status(node_id, status='running'):
    """Update a node's MicroK8s status."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print(f"✗ Node with ID {node_id} not found")
            return False
        
        old_status = node.microk8s_status
        node.microk8s_status = status
        node.last_seen = datetime.utcnow()
        node.status = 'online'
        
        session.commit()
        
        print(f"✓ Updated node '{node.hostname}' MicroK8s status:")
        print(f"  From: {old_status}")
        print(f"  To: {status}")
        print(f"  Last seen: {node.last_seen}")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"✗ Failed to update node status: {e}")
        return False
    finally:
        session.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Update node MicroK8s status')
    parser.add_argument('node_id', type=int, help='Node ID to update')
    parser.add_argument('--status', default='running',
                       choices=['not_installed', 'installed', 'running', 'stopped', 'error'],
                       help='MicroK8s status to set (default: running)')
    
    args = parser.parse_args()
    
    success = update_node_microk8s_status(args.node_id, args.status)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
