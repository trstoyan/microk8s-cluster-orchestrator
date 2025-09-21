"""Core orchestration service for managing MicroK8s operations."""

import os
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..models.database import db
from ..models.node import Node
from ..models.cluster import Cluster
from ..models.operation import Operation
from ..models.router_switch import RouterSwitch
from .network_monitor import NetworkMonitorService

class OrchestrationService:
    """Service for orchestrating MicroK8s operations using Ansible."""
    
    def __init__(self):
        self.ansible_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ansible')
        self.playbooks_dir = os.path.join(self.ansible_dir, 'playbooks')
        self.inventory_dir = os.path.join(self.ansible_dir, 'inventory')
        self.network_monitor = NetworkMonitorService()
    
    def _get_ansible_playbook_path(self) -> str:
        """Get the path to ansible-playbook executable, preferring virtual environment."""
        # Check if we're in a virtual environment
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            venv_ansible = os.path.join(venv_path, 'bin', 'ansible-playbook')
            if os.path.exists(venv_ansible):
                return venv_ansible
        
        # Check for .venv in project directory
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        venv_ansible = os.path.join(project_root, '.venv', 'bin', 'ansible-playbook')
        if os.path.exists(venv_ansible):
            return venv_ansible
        
        # Check for venv in project directory  
        venv_ansible = os.path.join(project_root, 'venv', 'bin', 'ansible-playbook')
        if os.path.exists(venv_ansible):
            return venv_ansible
        
        # Fall back to system ansible-playbook
        return 'ansible-playbook'
    
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
        # Use the ansible-playbook from the virtual environment if available
        ansible_playbook_cmd = self._get_ansible_playbook_path()
        
        cmd = [
            ansible_playbook_cmd,
            '-i', inventory_file,
            playbook_path
        ]
        
        if extra_vars:
            cmd.extend(['--extra-vars', json.dumps(extra_vars)])
        
        try:
            # Log the command being executed for debugging
            cmd_str = ' '.join(cmd)
            print(f"Executing: {cmd_str}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.ansible_dir)
            success = result.returncode == 0
            
            # Provide more detailed output
            output_parts = []
            if result.stdout.strip():
                output_parts.append(f"STDOUT:\n{result.stdout}")
            if result.stderr.strip():
                output_parts.append(f"STDERR:\n{result.stderr}")
            if not output_parts:
                output_parts.append("No output from ansible-playbook")
                
            output = "\n\n".join(output_parts)
            
            if not success:
                output = f"Command failed with return code {result.returncode}\n\n{output}"
            
            return success, output
        except FileNotFoundError as e:
            return False, f"Ansible executable not found: {str(e)}\nTried to execute: {ansible_playbook_cmd}"
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
        """Backup router switch configuration with improved timeout handling."""
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
                
                # Test connectivity first
                ping_result = subprocess.run(['ping', '-c', '3', '-W', '5', router_switch.ip_address], 
                                           capture_output=True, text=True, timeout=20)
                
                if ping_result.returncode != 0:
                    self._update_operation_status(operation, 'failed', success=False,
                                                error_message=f"Router {router_switch.hostname} is not reachable via ping")
                    return operation
                
                # Use SSH to backup configuration with proper timeouts
                ssh_cmd = [
                    'ssh', 
                    '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=5',
                    '-o', 'ServerAliveCountMax=3',
                    '-o', 'BatchMode=yes',
                    '-o', 'StrictHostKeyChecking=no',
                    f'{router_switch.ip_address}',
                    '-p', str(router_switch.management_port),
                    '/export file=backup_config'
                ]
                
                try:
                    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        # Download the backup file with timeout
                        scp_cmd = [
                            'scp',
                            '-o', 'ConnectTimeout=10',
                            '-o', 'ServerAliveInterval=5',
                            '-o', 'ServerAliveCountMax=3',
                            '-o', 'BatchMode=yes',
                            '-o', 'StrictHostKeyChecking=no',
                            f'{router_switch.ip_address}:backup_config.rsc',
                            backup_path
                        ]
                        
                        try:
                            scp_result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
                            
                            if scp_result.returncode == 0:
                                # Cleanup remote backup file
                                cleanup_cmd = [
                                    'ssh', 
                                    '-o', 'ConnectTimeout=10',
                                    '-o', 'BatchMode=yes',
                                    '-o', 'StrictHostKeyChecking=no',
                                    f'{router_switch.ip_address}',
                                    '-p', str(router_switch.management_port),
                                    '/file remove backup_config.rsc'
                                ]
                                subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
                                
                                # Update router switch record
                                router_switch.last_config_backup = datetime.utcnow()
                                router_switch.config_backup_path = backup_path
                                db.session.commit()
                                
                                # Get file size for output
                                file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
                                
                                self._update_operation_status(operation, 'completed', success=True, 
                                                            output=f"Configuration backed up successfully\nFile: {backup_path}\nSize: {file_size} bytes\nBackup created: {datetime.utcnow()}")
                            else:
                                self._update_operation_status(operation, 'failed', success=False,
                                                            output=scp_result.stderr, 
                                                            error_message=f"Failed to download backup file: {scp_result.stderr}")
                        except subprocess.TimeoutExpired:
                            self._update_operation_status(operation, 'failed', success=False,
                                                        error_message="SCP download timed out after 60 seconds")
                    else:
                        self._update_operation_status(operation, 'failed', success=False,
                                                    output=result.stderr, 
                                                    error_message=f"Failed to create backup on router: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self._update_operation_status(operation, 'failed', success=False,
                                                error_message="SSH export command timed out after 60 seconds")
            else:
                # For other device types, we would implement specific backup methods
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message=f"Backup not implemented for device type: {router_switch.device_type}")
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False, 
                                        error_message=f"Backup operation failed: {str(e)}")
        
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
    
    def scan_dhcp_leases(self, router_switch: RouterSwitch) -> Operation:
        """Scan router for DHCP leases and update database."""
        operation = self._create_operation(
            operation_type='network_scan',
            operation_name='Scan DHCP Leases',
            description=f'Scan DHCP leases on {router_switch.hostname}',
            router_switch=router_switch
        )
        
        try:
            operation.status = 'running'
            operation.started_at = datetime.utcnow()
            db.session.commit()
            
            # Perform the scan
            result = self.network_monitor.scan_dhcp_leases(router_switch)
            
            # Update operation with results
            operation.success = result.get('success', False)
            operation.output = json.dumps(result, indent=2)
            
            if not operation.success:
                operation.error_message = result.get('error', 'Unknown error occurred')
                operation.status = 'failed'
            else:
                operation.status = 'completed'
            
            operation.completed_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            operation.status = 'failed'
            operation.success = False
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            db.session.commit()
        
        return operation
    
    def scan_network_interfaces(self, router_switch: RouterSwitch) -> Operation:
        """Scan router for network interfaces and update database."""
        operation = self._create_operation(
            operation_type='network_scan',
            operation_name='Scan Network Interfaces',
            description=f'Scan network interfaces on {router_switch.hostname}',
            router_switch=router_switch
        )
        
        try:
            operation.status = 'running'
            operation.started_at = datetime.utcnow()
            db.session.commit()
            
            # Perform the scan
            result = self.network_monitor.scan_network_interfaces(router_switch)
            
            # Update operation with results
            operation.success = result.get('success', False)
            operation.output = json.dumps(result, indent=2)
            
            if not operation.success:
                operation.error_message = result.get('error', 'Unknown error occurred')
                operation.status = 'failed'
            else:
                operation.status = 'completed'
            
            operation.completed_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            operation.status = 'failed'
            operation.success = False
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            db.session.commit()
        
        return operation
    
    def match_leases_to_nodes(self) -> Dict[str, Any]:
        """Match network leases to cluster nodes based on IP addresses."""
        try:
            matched_count = self.network_monitor.match_leases_to_nodes()
            return {
                'success': True,
                'matched_count': matched_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def cleanup_stuck_operations(self, timeout_hours: int = 2) -> Dict[str, Any]:
        """Clean up operations that have been running too long."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=timeout_hours)
            
            stuck_operations = Operation.query.filter(
                Operation.status == 'running',
                Operation.started_at < cutoff_time
            ).all()
            
            if not stuck_operations:
                return {
                    'success': True,
                    'message': 'No stuck operations found',
                    'cleaned_count': 0
                }
            
            for operation in stuck_operations:
                runtime = datetime.utcnow() - operation.started_at if operation.started_at else None
                operation.status = 'failed'
                operation.success = False
                operation.error_message = f'Operation timed out after {runtime} - automatically terminated'
                operation.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Cleaned up {len(stuck_operations)} stuck operations',
                'cleaned_count': len(stuck_operations)
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0
            }
    
    def scan_cluster_state(self, cluster: Cluster) -> Operation:
        """Scan cluster to validate configuration and detect drift from desired state."""
        operation = self._create_operation(
            operation_type='scan',
            operation_name='Scan Cluster State',
            description=f'Validate configuration and check for drift in cluster {cluster.name}',
            cluster=cluster,
            playbook_path='playbooks/scan_cluster_state.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message="Cluster has no nodes to scan")
                return operation
            
            inventory_file = self._generate_inventory(nodes)
            playbook_path = os.path.join(self.playbooks_dir, 'scan_cluster_state.yml')
            
            extra_vars = {
                'cluster_name': cluster.name,
                'expected_ha_enabled': cluster.ha_enabled,
                'expected_network_cidr': cluster.network_cidr,
                'expected_service_cidr': cluster.service_cidr,
                'expected_addons': ['dns', 'storage', 'ingress', 'dashboard']
            }
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            if success:
                # Parse scan results and update cluster status
                scan_results = self._parse_scan_results(output)
                cluster_healthy = scan_results.get('overall_health', False)
                
                if cluster_healthy:
                    cluster.status = 'active'
                    cluster.health_score = scan_results.get('health_score', 100)
                else:
                    cluster.status = 'degraded'
                    cluster.health_score = scan_results.get('health_score', 50)
                
                db.session.commit()
                self._update_operation_status(operation, 'completed', success=True, output=output)
            else:
                cluster.status = 'error'
                cluster.health_score = 0
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False,
                                            output=output, error_message='Cluster scan failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False,
                                        error_message=f"Cluster scan failed: {str(e)}")
        
        return operation
    
    def _parse_scan_results(self, ansible_output: str) -> Dict[str, Any]:
        """Parse Ansible scan output and extract health metrics."""
        results = {
            'overall_health': True,
            'health_score': 100,
            'issues': [],
            'nodes_status': {},
            'addons_status': {},
            'network_status': {}
        }
        
        try:
            # Look for specific markers in the output
            if 'CLUSTER_SCAN_RESULTS:' in ansible_output:
                # Extract JSON results if present
                import re
                json_match = re.search(r'CLUSTER_SCAN_RESULTS: ({.*?})', ansible_output, re.DOTALL)
                if json_match:
                    scan_data = json.loads(json_match.group(1))
                    results.update(scan_data)
            
            # Fallback: Parse output for common issues
            if 'NotReady' in ansible_output:
                results['overall_health'] = False
                results['health_score'] -= 30
                results['issues'].append('Some nodes are not ready')
            
            if 'addon not enabled' in ansible_output:
                results['overall_health'] = False
                results['health_score'] -= 20
                results['issues'].append('Required addons are not enabled')
            
            if 'network configuration mismatch' in ansible_output:
                results['overall_health'] = False
                results['health_score'] -= 25
                results['issues'].append('Network configuration drift detected')
                
        except Exception as e:
            results['issues'].append(f'Failed to parse scan results: {str(e)}')
        
        return results
