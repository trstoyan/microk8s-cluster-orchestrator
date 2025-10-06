"""CLI-compatible orchestration service for managing MicroK8s operations."""

import os
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.database import get_session
from ..models.flask_models import Node, Cluster, Operation

class CLIOrchestrationService:
    """Service for orchestrating MicroK8s operations using Ansible (CLI version)."""
    
    def __init__(self):
        self.ansible_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ansible')
        self.playbooks_dir = os.path.join(self.ansible_dir, 'playbooks')
        self.inventory_dir = os.path.join(self.ansible_dir, 'inventory')
    
    def _create_operation(self, session, operation_type: str, operation_name: str, 
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
        session.add(operation)
        session.commit()
        return operation
    
    def _update_operation_status(self, session, operation: Operation, status: str, 
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
        
        session.commit()
    
    def _generate_inventory(self, nodes: list) -> str:
        """Generate Ansible inventory file for nodes."""
        inventory_content = "[microk8s_nodes]\n"
        
        for node in nodes:
            inventory_content += f"{node.hostname} ansible_host={node.ip_address} "
            inventory_content += f"ansible_user={node.ssh_user} "
            inventory_content += f"ansible_port={node.ssh_port} "
            
            if node.ssh_key_path:
                # Expand user home directory
                key_path = os.path.expanduser(node.ssh_key_path)
                inventory_content += f"ansible_ssh_private_key_file={key_path} "
            
            inventory_content += "ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n"
        
        # Save inventory to file
        os.makedirs(self.inventory_dir, exist_ok=True)
        inventory_file = os.path.join(self.inventory_dir, 'dynamic_inventory.ini')
        
        with open(inventory_file, 'w') as f:
            f.write(inventory_content)
        
        return inventory_file
    
    def _run_ansible_playbook(self, playbook_path: str, inventory_file: str, 
                             extra_vars: Dict[str, Any] = None) -> tuple[bool, str]:
        """Run an Ansible playbook."""
        cmd = [
            'ansible-playbook',
            '-i', inventory_file,
            playbook_path,
            '-v'
        ]
        
        if extra_vars:
            cmd.extend(['--extra-vars', json.dumps(extra_vars)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Ansible playbook execution timed out"
        except Exception as e:
            return False, f"Failed to run ansible playbook: {str(e)}"
    
    def check_node_status(self, node: Node) -> Operation:
        """Check the status of a node."""
        session = get_session()
        try:
            # Re-fetch the node in this session to avoid detached instance issues
            node = session.query(Node).filter_by(id=node.id).first()
            if not node:
                raise ValueError("Node not found in database")
            
            operation = self._create_operation(
                session,
                operation_type='troubleshoot',
                operation_name='Check Node Status',
                description=f'Check status of node {node.hostname}',
                node=node,
                playbook_path='playbooks/check_node_status.yml'
            )
            
            self._update_operation_status(session, operation, 'running')
            
            inventory_file = self._generate_inventory([node])
            playbook_path = os.path.join(self.playbooks_dir, 'check_node_status.yml')
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                # Update node status based on check results
                node.last_seen = datetime.utcnow()
                node.status = 'online'
                
                # Try to extract MicroK8s status from output
                if 'microk8s is running' in output.lower():
                    node.microk8s_status = 'running'
                elif 'microk8s is not running' in output.lower():
                    node.microk8s_status = 'stopped'
                elif '/snap/bin/microk8s' in output or 'microk8s' in output:
                    node.microk8s_status = 'installed'
                
                session.commit()
                self._update_operation_status(session, operation, 'completed', success=True, output=output)
            else:
                node.status = 'offline'
                session.commit()
                self._update_operation_status(session, operation, 'failed', success=False, 
                                            output=output, error_message='Status check failed')
            
            return operation
            
        except Exception as e:
            if 'operation' in locals():
                self._update_operation_status(session, operation, 'failed', success=False, 
                                            error_message=str(e))
                return operation
            else:
                raise e
        finally:
            session.close()
