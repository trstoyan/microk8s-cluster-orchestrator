#!/usr/bin/env python3
"""
Diagnose why cluster scan failed
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models.database import db
from app.models.flask_models import Operation, Cluster, Node

def diagnose_last_scan_failure():
    """Diagnose the last failed scan operation"""
    app = create_app()
    
    with app.app_context():
        # Get the last failed scan operation
        failed_scan = Operation.query.filter(
            Operation.operation_type == 'scan',
            Operation.status == 'failed'
        ).order_by(Operation.created_at.desc()).first()
        
        if not failed_scan:
            print("✅ No failed scan operations found!")
            return
        
        print("🔍 Diagnosing Failed Cluster Scan")
        print("=" * 60)
        print(f"📅 Date: {failed_scan.created_at}")
        print(f"🏷️  Operation: {failed_scan.operation_name}")
        print(f"📝 Description: {failed_scan.description}")
        print()
        
        # Get the cluster
        cluster = Cluster.query.get(failed_scan.cluster_id) if failed_scan.cluster_id else None
        
        if cluster:
            print(f"🎯 Cluster: {cluster.name}")
            print(f"   Nodes in cluster: {len(cluster.nodes)}")
            print()
            
            # Check nodes
            if not cluster.nodes:
                print("❌ ISSUE: Cluster has NO nodes!")
                print("   ➜ Add at least one node to the cluster")
                print()
            else:
                print("📊 Node Status:")
                for node in cluster.nodes:
                    print(f"\n   Node: {node.hostname} ({node.ip_address})")
                    
                    # Check SSH key
                    if not node.ssh_key_path:
                        print(f"      ❌ No SSH key configured")
                        print(f"         ➜ Go to node details and generate SSH key")
                    elif not Path(node.ssh_key_path).exists():
                        print(f"      ❌ SSH key file not found: {node.ssh_key_path}")
                        print(f"         ➜ Re-generate SSH key for this node")
                    else:
                        print(f"      ✅ SSH key exists: {node.ssh_key_path}")
                    
                    # Check SSH connection test
                    if not node.ssh_connection_tested:
                        print(f"      ⚠️  SSH connection not tested")
                        print(f"         ➜ Run 'Check SSH Connection' for this node")
                    else:
                        print(f"      ✅ SSH connection tested")
                    
                    # Check MicroK8s
                    if node.microk8s_status == 'not_installed':
                        print(f"      ⚠️  MicroK8s not installed")
                        print(f"         ➜ This node needs MicroK8s installed")
                    else:
                        print(f"      ✅ MicroK8s: {node.microk8s_status}")
        
        print()
        print("=" * 60)
        print("❌ Error Message:")
        print(failed_scan.error_message or "No error message recorded")
        print()
        
        if failed_scan.output:
            print("=" * 60)
            print("📋 Operation Output (last 500 chars):")
            print(failed_scan.output[-500:] if len(failed_scan.output) > 500 else failed_scan.output)
            print()
        
        print("=" * 60)
        print("\n💡 Common Solutions:")
        print("   1. Ensure all cluster nodes have SSH keys generated")
        print("   2. Test SSH connection to each node")
        print("   3. Make sure nodes are accessible via SSH")
        print("   4. Check if MicroK8s is running on nodes")
        print("   5. Verify network connectivity between orchestrator and nodes")
        print()
        print("🔧 Quick Fix Commands:")
        print("   • Generate SSH keys: Go to node details → SSH Setup")
        print("   • Test SSH: Node details → Check SSH Connection")
        print("   • Install MicroK8s: Node details → Install MicroK8s")
        print()

if __name__ == '__main__':
    diagnose_last_scan_failure()

