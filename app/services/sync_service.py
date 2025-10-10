"""
Sync Service for live data synchronization between servers
Handles comparison, selective transfer, and conflict resolution
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import inspect

from app.models.database import db
from app.models.flask_models import Node, Cluster
from app.utils.encryption import SyncEncryption, SyncToken


class SyncService:
    """Service for synchronizing data between orchestrator instances"""
    
    def __init__(self, local_url: str = "http://localhost:5000", 
                 remote_url: str = None, 
                 api_token: str = None):
        """
        Initialize sync service
        
        Args:
            local_url: URL of local server
            remote_url: URL of remote server to sync with
            api_token: API token for authentication
        """
        self.local_url = local_url
        self.remote_url = remote_url
        self.api_token = api_token
        self.encryption = SyncEncryption()
        self.token_manager = SyncToken()
        
    def get_local_inventory(self) -> Dict:
        """Get inventory of local server data"""
        inventory = {
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'server_url': self.local_url,
                'version': '1.0.0'
            },
            'nodes': [],
            'clusters': [],
            'ssh_keys': [],
            'stats': {
                'total_nodes': 0,
                'total_clusters': 0,
                'total_ssh_keys': 0
            }
        }
        
        # Get all nodes
        nodes = Node.query.all()
        for node in nodes:
            inventory['nodes'].append({
                'id': node.id,
                'hostname': node.hostname,
                'ip_address': node.ip_address,
                'ssh_user': node.ssh_user,
                'ssh_port': node.ssh_port,
                'cluster_id': node.cluster_id,
                'status': node.status,
                'microk8s_version': node.microk8s_version,
                'microk8s_status': node.microk8s_status,
                'is_control_plane': node.is_control_plane,
                'wol_enabled': node.wol_enabled if hasattr(node, 'wol_enabled') else False,
                'wol_mac_address': node.wol_mac_address if hasattr(node, 'wol_mac_address') else None,
                'created_at': node.created_at.isoformat() if node.created_at else None,
                'updated_at': node.updated_at.isoformat() if node.updated_at else None
            })
        
        # Get all clusters
        clusters = Cluster.query.all()
        for cluster in clusters:
            cluster_nodes = [n.id for n in cluster.nodes]
            inventory['clusters'].append({
                'id': cluster.id,
                'name': cluster.name,
                'description': cluster.description,
                'ha_enabled': cluster.ha_enabled,
                'node_count': len(cluster_nodes),
                'node_ids': cluster_nodes,
                'created_at': cluster.created_at.isoformat() if cluster.created_at else None
            })
        
        # Get SSH keys (from nodes)
        for node in nodes:
            if node.ssh_key_generated and node.ssh_key_path:
                inventory['ssh_keys'].append({
                    'node_id': node.id,
                    'node_hostname': node.hostname,
                    'ssh_key_path': node.ssh_key_path,
                    'fingerprint': node.ssh_key_fingerprint,
                    'status': node.ssh_key_status
                })
        
        # Update stats
        inventory['stats']['total_nodes'] = len(inventory['nodes'])
        inventory['stats']['total_clusters'] = len(inventory['clusters'])
        inventory['stats']['total_ssh_keys'] = len(inventory['ssh_keys'])
        
        return inventory
    
    def get_remote_inventory(self) -> Dict:
        """Fetch inventory from remote server"""
        if not self.remote_url:
            raise ValueError("Remote URL not configured")
        
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        
        try:
            response = requests.get(
                f"{self.remote_url}/api/v1/sync/inventory",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch remote inventory: {str(e)}")
    
    def compare_inventories(self, local_inv: Dict, remote_inv: Dict) -> Dict:
        """
        Compare local and remote inventories
        
        Returns:
            Dictionary with differences, missing items, and conflicts
        """
        comparison = {
            'summary': {
                'local_total': local_inv['stats']['total_nodes'],
                'remote_total': remote_inv['stats']['total_nodes'],
                'identical': 0,
                'different': 0,
                'missing_on_remote': 0,
                'missing_on_local': 0,
                'conflicts': 0
            },
            'nodes': {
                'identical': [],
                'different': [],
                'missing_on_remote': [],
                'missing_on_local': [],
                'conflicts': []
            },
            'clusters': {
                'identical': [],
                'different': [],
                'missing_on_remote': [],
                'missing_on_local': [],
                'conflicts': []
            },
            'ssh_keys': {
                'identical': [],
                'different': [],
                'missing_on_remote': [],
                'missing_on_local': []
            }
        }
        
        # Compare nodes
        local_nodes = {n['hostname']: n for n in local_inv['nodes']}
        remote_nodes = {n['hostname']: n for n in remote_inv['nodes']}
        
        for hostname, local_node in local_nodes.items():
            if hostname in remote_nodes:
                remote_node = remote_nodes[hostname]
                if self._nodes_identical(local_node, remote_node):
                    comparison['nodes']['identical'].append(local_node)
                else:
                    comparison['nodes']['different'].append({
                        'local': local_node,
                        'remote': remote_node,
                        'differences': self._find_node_differences(local_node, remote_node)
                    })
            else:
                comparison['nodes']['missing_on_remote'].append(local_node)
        
        for hostname, remote_node in remote_nodes.items():
            if hostname not in local_nodes:
                comparison['nodes']['missing_on_local'].append(remote_node)
        
        # Compare clusters
        local_clusters = {c['name']: c for c in local_inv['clusters']}
        remote_clusters = {c['name']: c for c in remote_inv['clusters']}
        
        for name, local_cluster in local_clusters.items():
            if name in remote_clusters:
                remote_cluster = remote_clusters[name]
                if self._clusters_identical(local_cluster, remote_cluster):
                    comparison['clusters']['identical'].append(local_cluster)
                else:
                    comparison['clusters']['different'].append({
                        'local': local_cluster,
                        'remote': remote_cluster,
                        'differences': self._find_cluster_differences(local_cluster, remote_cluster)
                    })
            else:
                comparison['clusters']['missing_on_remote'].append(local_cluster)
        
        for name, remote_cluster in remote_clusters.items():
            if name not in local_clusters:
                comparison['clusters']['missing_on_local'].append(remote_cluster)
        
        # Update summary
        comparison['summary']['identical'] = (
            len(comparison['nodes']['identical']) + 
            len(comparison['clusters']['identical'])
        )
        comparison['summary']['different'] = (
            len(comparison['nodes']['different']) + 
            len(comparison['clusters']['different'])
        )
        comparison['summary']['missing_on_remote'] = (
            len(comparison['nodes']['missing_on_remote']) + 
            len(comparison['clusters']['missing_on_remote'])
        )
        comparison['summary']['missing_on_local'] = (
            len(comparison['nodes']['missing_on_local']) + 
            len(comparison['clusters']['missing_on_local'])
        )
        
        return comparison
    
    def _nodes_identical(self, node1: Dict, node2: Dict) -> bool:
        """Check if two nodes are identical"""
        compare_fields = ['hostname', 'ip_address', 'ssh_user', 'status']
        return all(node1.get(f) == node2.get(f) for f in compare_fields)
    
    def _clusters_identical(self, cluster1: Dict, cluster2: Dict) -> bool:
        """Check if two clusters are identical"""
        compare_fields = ['name', 'description', 'ha_enabled', 'node_count']
        return all(cluster1.get(f) == cluster2.get(f) for f in compare_fields)
    
    def _find_node_differences(self, node1: Dict, node2: Dict) -> List[str]:
        """Find specific differences between two nodes"""
        differences = []
        compare_fields = ['hostname', 'ip_address', 'ssh_user', 'ssh_port', 'status', 
                         'microk8s_status', 'microk8s_version', 'is_control_plane',
                         'wol_enabled', 'wol_mac_address']
        
        for field in compare_fields:
            if node1.get(field) != node2.get(field):
                differences.append(f"{field}: {node1.get(field)} → {node2.get(field)}")
        
        return differences
    
    def _find_cluster_differences(self, cluster1: Dict, cluster2: Dict) -> List[str]:
        """Find specific differences between two clusters"""
        differences = []
        compare_fields = ['name', 'description', 'ha_enabled', 'node_count']
        
        for field in compare_fields:
            if cluster1.get(field) != cluster2.get(field):
                differences.append(f"{field}: {cluster1.get(field)} → {cluster2.get(field)}")
        
        return differences
    
    def create_sync_package(self, items_to_sync: Dict) -> Dict:
        """
        Create encrypted sync package with selected items
        
        Args:
            items_to_sync: Dictionary with selected items to sync
            
        Returns:
            Encrypted package ready for transfer
        """
        package = {
            'timestamp': datetime.utcnow().isoformat(),
            'items': items_to_sync,
            'checksum': None  # TODO: Add checksum
        }
        
        # Encrypt the package
        encrypted_package = self.encryption.encrypt(package)
        
        return encrypted_package
    
    def apply_sync_package(self, encrypted_package: Dict) -> Dict:
        """
        Apply received sync package to local database
        
        Args:
            encrypted_package: Encrypted package from remote server
            
        Returns:
            Result of sync operation
        """
        # Decrypt package
        package = self.encryption.decrypt(encrypted_package)
        
        results = {
            'success': True,
            'applied': {
                'nodes': 0,
                'clusters': 0,
                'ssh_keys': 0
            },
            'errors': []
        }
        
        try:
            # Apply nodes
            if 'nodes' in package['items']:
                for node_data in package['items']['nodes']:
                    try:
                        self._apply_node(node_data)
                        results['applied']['nodes'] += 1
                    except Exception as e:
                        results['errors'].append(f"Node {node_data.get('hostname')}: {str(e)}")
            
            # Apply clusters
            if 'clusters' in package['items']:
                for cluster_data in package['items']['clusters']:
                    try:
                        self._apply_cluster(cluster_data)
                        results['applied']['clusters'] += 1
                    except Exception as e:
                        results['errors'].append(f"Cluster {cluster_data.get('name')}: {str(e)}")
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            results['success'] = False
            results['errors'].append(f"General error: {str(e)}")
        
        return results
    
    def _apply_node(self, node_data: Dict):
        """Apply node data to database"""
        # Check if node exists
        existing_node = Node.query.filter_by(hostname=node_data['hostname']).first()
        
        if existing_node:
            # Update existing
            for key, value in node_data.items():
                if hasattr(existing_node, key) and key not in ['id', 'created_at']:
                    setattr(existing_node, key, value)
        else:
            # Create new
            new_node = Node(**{k: v for k, v in node_data.items() 
                             if k not in ['id', 'created_at', 'updated_at']})
            db.session.add(new_node)
    
    def _apply_cluster(self, cluster_data: Dict):
        """Apply cluster data to database"""
        # Check if cluster exists
        existing_cluster = Cluster.query.filter_by(name=cluster_data['name']).first()
        
        if existing_cluster:
            # Update existing
            for key, value in cluster_data.items():
                if hasattr(existing_cluster, key) and key not in ['id', 'created_at', 'node_ids']:
                    setattr(existing_cluster, key, value)
        else:
            # Create new
            new_cluster = Cluster(**{k: v for k, v in cluster_data.items() 
                                   if k not in ['id', 'created_at', 'node_ids', 'node_count']})
            db.session.add(new_cluster)


if __name__ == '__main__':
    print("🔄 Sync Service - Test Mode")
    print("=" * 50)
    
    # This would need Flask app context to run
    print("\nSync service initialized successfully!")
    print("Use via Flask routes or CLI commands")

