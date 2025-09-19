"""Core orchestration service for managing MicroK8s operations."""

import os
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.database import db
from ..models.node import Node
from ..models.cluster import Cluster
from ..models.operation import Operation

class OrchestrationService:
    """Service for orchestrating MicroK8s operations using Ansible."""
    
    def __init__(self):
        self.ansible_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ansible')
        self.playbooks_dir = os.path.join(self.ansible_dir, 'playbooks')
        self.inventory_dir = os.path.join(self.ansible_dir, 'inventory')
    
    def _create_operation(self, operation_type: str, operation_name: str, 
                         description: str, node: Optional[Node] = None, 
                         cluster: Optional[Cluster] = None, 
                         playbook_path: str = None) -> Operation:
        """Create a new operation record."""
        operation = Operation(
            operation_type=operation_type,
            operation_name=operation_name,
            description=description,
            playbook_path=playbook_path,
            node_id=node.id if node else None,
            cluster_id=cluster.id if cluster else None,
            status='pending'
        )
        db.session.add(operation)
        db.session.commit()
        return operation
    
    def _update_operation_status(self, operation: Operation, status: str, 
                               success: bool = None, output: str = None, 
                               error_message: str = None):
        """Update operation status."""
        operation.status = status
        if status == 'running' and not operation.started_at:
            operation.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            operation.completed_at = datetime.utcnow()
            if success is not None:
                operation.success = success
        
        if output:
            operation.output = output
        if error_message:
            operation.error_message = error_message
        
        db.session.commit()
    
    def _generate_inventory(self, nodes: list[Node]) -> str:
        """Generate Ansible inventory for given nodes."""
        inventory = {
            'all': {
                'children': {
                    'microk8s_nodes': {
                        'hosts': {}
                    }
                }
            }
        }
        
        for node in nodes:
            inventory['all']['children']['microk8s_nodes']['hosts'][node.hostname] = {
                'ansible_host': node.ip_address,
                'ansible_user': node.ssh_user,
                'ansible_port': node.ssh_port,
                'ansible_ssh_private_key_file': node.ssh_key_path,
                'node_id': node.id
            }
        
        # Write inventory to temporary file
        inventory_file = os.path.join(self.inventory_dir, f'temp_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f, indent=2)
        
        return inventory_file
    
    def _run_ansible_playbook(self, playbook_path: str, inventory_file: str, 
                            extra_vars: Dict[str, Any] = None) -> tuple[bool, str]:
        """Run an Ansible playbook."""
        cmd = [
            'ansible-playbook',
            '-i', inventory_file,
            playbook_path
        ]
        
        if extra_vars:
            cmd.extend(['--extra-vars', json.dumps(extra_vars)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.ansible_dir)
            success = result.returncode == 0
            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return success, output
        except Exception as e:
            return False, f"Error running playbook: {str(e)}"
        finally:
            # Clean up temporary inventory file
            if os.path.exists(inventory_file):
                os.remove(inventory_file)
    
    def install_microk8s(self, node: Node) -> Operation:
        """Install MicroK8s on a node."""
        operation = self._create_operation(
            operation_type='install',
            operation_name='Install MicroK8s',
            description=f'Install MicroK8s on node {node.hostname}',
            node=node,
            playbook_path='playbooks/install_microk8s.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            inventory_file = self._generate_inventory([node])
            playbook_path = os.path.join(self.playbooks_dir, 'install_microk8s.yml')
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                node.microk8s_status = 'installed'
                node.status = 'online'
                db.session.commit()
                self._update_operation_status(operation, 'completed', success=True, output=output)
            else:
                node.status = 'error'
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False, 
                                            output=output, error_message='Installation failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def check_node_status(self, node: Node) -> Operation:
        """Check the status of a node."""
        operation = self._create_operation(
            operation_type='troubleshoot',
            operation_name='Check Node Status',
            description=f'Check status of node {node.hostname}',
            node=node,
            playbook_path='playbooks/check_node_status.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            inventory_file = self._generate_inventory([node])
            playbook_path = os.path.join(self.playbooks_dir, 'check_node_status.yml')
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                # Update node status based on check results
                node.last_seen = datetime.utcnow()
                node.status = 'online'
                db.session.commit()
                self._update_operation_status(operation, 'completed', success=True, output=output)
            else:
                node.status = 'offline'
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False, 
                                            output=output, error_message='Status check failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def setup_cluster(self, cluster: Cluster) -> Operation:
        """Set up a MicroK8s cluster."""
        operation = self._create_operation(
            operation_type='configure',
            operation_name='Setup Cluster',
            description=f'Setup cluster {cluster.name}',
            cluster=cluster,
            playbook_path='playbooks/setup_cluster.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                raise ValueError("Cluster has no nodes")
            
            inventory_file = self._generate_inventory(nodes)
            playbook_path = os.path.join(self.playbooks_dir, 'setup_cluster.yml')
            
            extra_vars = {
                'cluster_name': cluster.name,
                'ha_enabled': cluster.ha_enabled,
                'network_cidr': cluster.network_cidr,
                'service_cidr': cluster.service_cidr
            }
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            if success:
                cluster.status = 'active'
                db.session.commit()
                self._update_operation_status(operation, 'completed', success=True, output=output)
            else:
                cluster.status = 'error'
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False, 
                                            output=output, error_message='Cluster setup failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
