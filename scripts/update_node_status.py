#!/usr/bin/env python3
"""
Script to manually update node status by running health checks.
Useful for testing and fixing status detection issues.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.database import get_session
from app.models.node import Node
from app.services.orchestrator import OrchestrationService

def update_all_nodes():
    """Update status for all nodes."""
    session = get_session()
    orchestrator = OrchestrationService()
    
    try:
        nodes = session.query(Node).all()
        print(f"Found {len(nodes)} nodes to check")
        
        for node in nodes:
            print(f"\nChecking node: {node.hostname} ({node.ip_address})")
            print(f"Current status: {node.status}, MicroK8s: {node.microk8s_status}")
            
            try:
                operation = orchestrator.check_node_status(node)
                
                # Refresh node from database to see updated status
                session.refresh(node)
                print(f"Updated status: {node.status}, MicroK8s: {node.microk8s_status}")
                print(f"Operation result: {operation.status}")
                
            except Exception as e:
                print(f"Error checking node {node.hostname}: {e}")
        
        print("\nNode status update completed!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

def update_specific_node(hostname):
    """Update status for a specific node."""
    session = get_session()
    orchestrator = OrchestrationService()
    
    try:
        node = session.query(Node).filter_by(hostname=hostname).first()
        if not node:
            print(f"Node '{hostname}' not found")
            return
        
        print(f"Checking node: {node.hostname} ({node.ip_address})")
        print(f"Current status: {node.status}, MicroK8s: {node.microk8s_status}")
        
        operation = orchestrator.check_node_status(node)
        
        # Refresh node from database to see updated status
        session.refresh(node)
        print(f"Updated status: {node.status}, MicroK8s: {node.microk8s_status}")
        print(f"Operation result: {operation.status}")
        
        if operation.output:
            print(f"\nOperation output:\n{operation.output}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        hostname = sys.argv[1]
        update_specific_node(hostname)
    else:
        update_all_nodes()