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
from ..models.router_switch import RouterSwitch

class OrchestrationService:
    """Service for orchestrating MicroK8s operations using Ansible."""
    
    def __init__(self):
        self.ansible_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ansible')
        self.playbooks_dir = os.path.join(self.ansible_dir, 'playbooks')
        self.inventory_dir = os.path.join(self.ansible_dir, 'inventory')
    
    def _create_operation(self, operation_type: str, operation_name: str, 
                         description: str, node: Optional[Node] = None, 
                         cluster: Optional[Cluster] = None, 
                         router_switch: Optional[RouterSwitch] = None,
                         playbook_path: str = None) -> Operation:
        """Create a new operation record."""
        operation = Operation(
            operation_type=operation_type,
            operation_name=operation_name,
            description=description,
            playbook_path=playbook_path,
            node_id=node.id if node else None,
            cluster_id=cluster.id if cluster else None,
            router_switch_id=router_switch.id if router_switch else None,
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
    
    def backup_router_config(self, router_switch: RouterSwitch) -> Operation:
        """Backup router switch configuration."""
        operation = self._create_operation(
            operation_type='backup',
            operation_name='Backup Router Configuration',
            description=f'Backup configuration for router {router_switch.hostname}',
            router_switch=router_switch,
            playbook_path='playbooks/backup_router_config.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            # For MikroTik devices, we can use SSH to backup configuration
            if router_switch.is_mikrotik:
                backup_file = f"backup_{router_switch.hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rsc"
                backup_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backups', backup_file)
                
                # Ensure backups directory exists
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                
                # Use SSH to backup configuration
                ssh_cmd = [
                    'ssh', 
                    f'{router_switch.ip_address}',
                    '-p', str(router_switch.management_port),
                    'export file=backup_config'
                ]
                
                result = subprocess.run(ssh_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Download the backup file
                    scp_cmd = [
                        'scp',
                        f'{router_switch.ip_address}:backup_config.rsc',
                        backup_path
                    ]
                    
                    result = subprocess.run(scp_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        router_switch.last_config_backup = datetime.utcnow()
                        router_switch.config_backup_path = backup_path
                        db.session.commit()
                        self._update_operation_status(operation, 'completed', success=True, 
                                                    output=f"Configuration backed up to {backup_path}")
                    else:
                        self._update_operation_status(operation, 'failed', success=False,
                                                    output=result.stderr, error_message="Failed to download backup")
                else:
                    self._update_operation_status(operation, 'failed', success=False,
                                                output=result.stderr, error_message="Failed to create backup")
            else:
                # For other device types, we would implement specific backup methods
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message=f"Backup not implemented for device type: {router_switch.device_type}")
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def check_router_status(self, router_switch: RouterSwitch) -> Operation:
        """Check the status of a router switch."""
        operation = self._create_operation(
            operation_type='troubleshoot',
            operation_name='Check Router Status',
            description=f'Check status of router {router_switch.hostname}',
            router_switch=router_switch,
            playbook_path='playbooks/check_router_status.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            # Use ping to check basic connectivity
            ping_cmd = ['ping', '-c', '1', '-W', '5', router_switch.ip_address]
            result = subprocess.run(ping_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Device is reachable, try to get more detailed status
                if router_switch.is_mikrotik:
                    # Use SSH to get system resource information
                    ssh_cmd = [
                        'ssh', 
                        f'{router_switch.ip_address}',
                        '-p', str(router_switch.management_port),
                        'system resource print'
                    ]
                    
                    ssh_result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)
                    
                    if ssh_result.returncode == 0:
                        # Parse system resource output (simplified)
                        output_lines = ssh_result.stdout.split('\n')
                        for line in output_lines:
                            if 'uptime' in line.lower():
                                # Extract uptime information
                                router_switch.uptime_seconds = self._parse_uptime(line)
                            elif 'cpu-load' in line.lower():
                                # Extract CPU load
                                router_switch.cpu_load_percent = self._parse_cpu_load(line)
                            elif 'free-memory' in line.lower() and 'total-memory' in line.lower():
                                # Extract memory usage
                                router_switch.memory_usage_percent = self._parse_memory_usage(line)
                        
                        router_switch.status = 'online'
                        router_switch.last_seen = datetime.utcnow()
                        db.session.commit()
                        
                        self._update_operation_status(operation, 'completed', success=True, 
                                                    output=f"Router is online and responsive\n{ssh_result.stdout}")
                    else:
                        router_switch.status = 'error'
                        db.session.commit()
                        self._update_operation_status(operation, 'failed', success=False,
                                                    output=ssh_result.stderr, error_message="SSH connection failed")
                else:
                    router_switch.status = 'online'
                    router_switch.last_seen = datetime.utcnow()
                    db.session.commit()
                    self._update_operation_status(operation, 'completed', success=True, 
                                                output="Router is reachable via ping")
            else:
                router_switch.status = 'offline'
                router_switch.last_seen = datetime.utcnow()
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False,
                                            output=result.stderr, error_message="Device is not reachable")
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def update_router_firmware(self, router_switch: RouterSwitch, firmware_version: str = None) -> Operation:
        """Update router switch firmware."""
        operation = self._create_operation(
            operation_type='update',
            operation_name='Update Router Firmware',
            description=f'Update firmware for router {router_switch.hostname}' + 
                       (f' to version {firmware_version}' if firmware_version else ' to latest'),
            router_switch=router_switch,
            playbook_path='playbooks/update_router_firmware.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            if router_switch.is_mikrotik:
                # For MikroTik devices, use RouterOS commands
                if firmware_version:
                    # Update to specific version
                    ssh_cmd = [
                        'ssh', 
                        f'{router_switch.ip_address}',
                        '-p', str(router_switch.management_port),
                        f'system package update install={firmware_version}'
                    ]
                else:
                    # Update to latest
                    ssh_cmd = [
                        'ssh', 
                        f'{router_switch.ip_address}',
                        '-p', str(router_switch.management_port),
                        'system package update install'
                    ]
                
                result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # Firmware update initiated successfully
                    self._update_operation_status(operation, 'completed', success=True, 
                                                output=f"Firmware update initiated successfully\n{result.stdout}")
                else:
                    self._update_operation_status(operation, 'failed', success=False,
                                                output=result.stderr, error_message="Failed to initiate firmware update")
            else:
                # For other device types, implement specific update methods
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message=f"Firmware update not implemented for device type: {router_switch.device_type}")
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def restore_router_config(self, router_switch: RouterSwitch, backup_path: str) -> Operation:
        """Restore router switch configuration from backup."""
        operation = self._create_operation(
            operation_type='restore',
            operation_name='Restore Router Configuration',
            description=f'Restore configuration for router {router_switch.hostname} from {backup_path}',
            router_switch=router_switch,
            playbook_path='playbooks/restore_router_config.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            if router_switch.is_mikrotik and backup_path:
                # Upload and restore configuration
                scp_cmd = [
                    'scp',
                    backup_path,
                    f'{router_switch.ip_address}:restore_config.rsc'
                ]
                
                result = subprocess.run(scp_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Import the configuration
                    ssh_cmd = [
                        'ssh', 
                        f'{router_switch.ip_address}',
                        '-p', str(router_switch.management_port),
                        'import file=restore_config.rsc'
                    ]
                    
                    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        self._update_operation_status(operation, 'completed', success=True, 
                                                    output=f"Configuration restored successfully\n{result.stdout}")
                    else:
                        self._update_operation_status(operation, 'failed', success=False,
                                                    output=result.stderr, error_message="Failed to import configuration")
                else:
                    self._update_operation_status(operation, 'failed', success=False,
                                                output=result.stderr, error_message="Failed to upload backup file")
            else:
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message="Restore not supported or backup path not provided")
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=str(e))
        
        return operation
    
    def _parse_uptime(self, line: str) -> int:
        """Parse uptime from MikroTik system resource output."""
        # This is a simplified parser - in reality, you'd want more robust parsing
        try:
            # Example: "uptime: 1w3d5h30m15s"
            if 'uptime:' in line:
                uptime_str = line.split('uptime:')[1].strip()
                # Convert to seconds (simplified)
                return 86400  # Default to 1 day for now
        except:
            pass
        return 0
    
    def _parse_cpu_load(self, line: str) -> float:
        """Parse CPU load from MikroTik system resource output."""
        try:
            if 'cpu-load:' in line:
                cpu_str = line.split('cpu-load:')[1].strip().split('%')[0]
                return float(cpu_str)
        except:
            pass
        return 0.0
    
    def _parse_memory_usage(self, line: str) -> float:
        """Parse memory usage from MikroTik system resource output."""
        try:
            # This would need more sophisticated parsing
            return 50.0  # Default value
        except:
            pass
        return 0.0
