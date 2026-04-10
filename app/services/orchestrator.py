"""Core orchestration service for managing Kubernetes runtime operations."""

import os
import json
import re
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch
from .network_monitor import NetworkMonitorService
from ..utils.config import ConfigManager

# Module-level logger
logger = logging.getLogger(__name__)

class OrchestrationService:
    """Service for orchestrating cluster operations using Ansible."""
    
    def __init__(self):
        self.ansible_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ansible')
        self.playbooks_dir = os.path.join(self.ansible_dir, 'playbooks')
        self.inventory_dir = self._resolve_writable_inventory_dir(
            os.path.join(self.ansible_dir, 'inventory')
        )
        self.network_monitor = NetworkMonitorService()
        self.config = ConfigManager()
        self.logger = logger  # Instance reference to module logger

    def _resolve_cluster_runtime(
        self,
        cluster: Optional[Cluster] = None,
        node: Optional[Node] = None,
    ) -> str:
        """Resolve the effective Kubernetes distribution for an operation."""
        if cluster and getattr(cluster, 'kubernetes_distribution', None):
            return (cluster.kubernetes_distribution or 'microk8s').lower()
        if node and node.cluster and getattr(node.cluster, 'kubernetes_distribution', None):
            return (node.cluster.kubernetes_distribution or 'microk8s').lower()
        return 'microk8s'

    def _runtime_display_name(self, runtime: str) -> str:
        """Return a user-facing runtime name."""
        return 'k3s' if runtime == 'k3s' else 'MicroK8s'

    def _runtime_playbook(self, operation_kind: str, runtime: str) -> Optional[str]:
        """Return the playbook filename for a runtime-aware operation."""
        playbook_map = {
            'install': {
                'microk8s': 'install_microk8s.yml',
                'k3s': None,
            },
            'status': {
                'microk8s': 'check_node_status.yml',
                'k3s': 'check_k3s_status.yml',
            },
            'setup': {
                'microk8s': 'setup_cluster.yml',
                'k3s': 'setup_k3s_cluster.yml',
            },
            'scan': {
                'microk8s': 'scan_cluster_state.yml',
                'k3s': 'scan_k3s_cluster_state.yml',
            },
            'shutdown': {
                'microk8s': 'shutdown_cluster.yml',
                'k3s': 'shutdown_k3s_cluster.yml',
            },
        }
        return playbook_map.get(operation_kind, {}).get(runtime)

    def _set_node_runtime_state(
        self,
        node: Node,
        runtime: str,
        status: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        """Update generic runtime fields and preserve MicroK8s compatibility."""
        if status is not None:
            node.kubernetes_status = status
            if runtime == 'microk8s':
                node.microk8s_status = status
        if version:
            node.kubernetes_version = version
            if runtime == 'microk8s':
                node.microk8s_version = version

    def _resolve_writable_inventory_dir(self, preferred_dir: str) -> str:
        """Return a writable inventory directory, with a temp fallback."""
        try:
            os.makedirs(preferred_dir, exist_ok=True)
            test_file = os.path.join(preferred_dir, '.write_test')
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('ok')
            os.remove(test_file)
            return preferred_dir
        except Exception:
            fallback_dir = os.path.join('/tmp', 'microk8s-orchestrator-inventory')
            os.makedirs(fallback_dir, exist_ok=True)
            logger.warning(
                "Inventory directory '%s' is not writable; using fallback '%s'",
                preferred_dir,
                fallback_dir
            )
            return fallback_dir
    
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
    
    def _generate_inventory(
        self,
        nodes: list[Node],
        runtime: str = 'microk8s',
        cluster: Optional[Cluster] = None,
    ) -> str:
        """Generate Ansible inventory for given nodes."""
        # Ensure inventory directory exists
        os.makedirs(self.inventory_dir, exist_ok=True)
        
        inventory = {
            'all': {
                'children': {
                    'cluster_nodes': {
                        'hosts': {}
                    },
                    'microk8s_nodes': {
                        'hosts': {}
                    },
                    'k3s_nodes': {
                        'hosts': {}
                    }
                }
            }
        }
        
        # Validate nodes and collect SSH connection issues
        ssh_issues = []
        
        for node in nodes:
            # Check if node has SSH key ready
            if not node.ssh_connection_ready:
                ssh_issues.append(f"Node '{node.hostname}' SSH connection not ready: {node.get_ssh_status_description()}")
                continue
            
            # Verify SSH key file exists
            if not node.ssh_key_path or not os.path.exists(node.ssh_key_path):
                ssh_issues.append(f"Node '{node.hostname}' SSH private key file not found: {node.ssh_key_path}")
                continue
            
            # Add node to inventory
            host_vars = {
                'ansible_host': node.ip_address,
                'ansible_user': node.ssh_user,
                'ansible_port': node.ssh_port,
                'ansible_ssh_private_key_file': node.ssh_key_path,
                'node_id': node.id,
                'is_control_plane': node.is_control_plane,
                'ssh_key_fingerprint': node.ssh_key_fingerprint,
                'node_runtime': runtime,
                'virtualization_provider': getattr(node, 'virtualization_provider', 'generic'),
                'provider_vm_name': getattr(node, 'provider_vm_name', None),
                'provider_vm_group': getattr(node, 'provider_vm_group', None),
            }
            inventory['all']['children']['cluster_nodes']['hosts'][node.hostname] = host_vars
            inventory['all']['children']['microk8s_nodes']['hosts'][node.hostname] = dict(host_vars)
            inventory['all']['children']['k3s_nodes']['hosts'][node.hostname] = dict(host_vars)

        # Fail fast if any target node is not ready. Partial execution causes
        # misleading "success" status for cluster-wide operations.
        if ssh_issues:
            issues_text = "\n".join(ssh_issues)
            raise ValueError(f"SSH validation failed for inventory generation:\n{issues_text}")

        # Guard against empty inventories: ansible may return 0 with "no hosts matched".
        if not inventory['all']['children']['cluster_nodes']['hosts']:
            raise ValueError("No SSH-ready nodes available for inventory generation")
        
        # Add common variables
        common_vars = {
            'ansible_python_interpreter': '/usr/bin/python3',
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null',
            'ansible_become': True,  # Enable privilege escalation (sudo)
            'ansible_become_method': 'sudo',  # Use sudo for privilege escalation
            'ansible_become_user': 'root',  # Become root user
            'ansible_become_flags': '-H -S -n',  # -n = non-interactive
            'cluster_runtime': runtime,
            'cluster_name': cluster.name if cluster else 'ad-hoc',
            'cluster_provider': getattr(cluster, 'infrastructure_provider', 'generic') if cluster else 'generic',
        }
        inventory['all']['children']['cluster_nodes']['vars'] = dict(common_vars)
        inventory['all']['children']['microk8s_nodes']['vars'] = dict(common_vars)
        inventory['all']['children']['k3s_nodes']['vars'] = dict(common_vars)
        
        # Write inventory to temporary file
        inventory_file = os.path.join(self.inventory_dir, f'temp_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f, indent=2)
        
        return inventory_file
    
    def _validate_ssh_connections(self, nodes: list[Node]) -> tuple[bool, list[str]]:
        """
        Validate SSH connections for all nodes.
        
        Returns:
            Tuple of (all_ready, list_of_issues)
        """
        issues = []
        
        for node in nodes:
            if not node.ssh_connection_ready:
                issues.append(f"Node '{node.hostname}': {node.get_ssh_status_description()}")
                continue
            
            # Test SSH connection
            try:
                from .ssh_key_manager import SSHKeyManager
                ssh_manager = SSHKeyManager()
                
                test_result = ssh_manager.validate_ssh_connection(
                    node.hostname,
                    node.ip_address,
                    node.ssh_user,
                    node.ssh_port,
                    node.ssh_key_path
                )
                
                if not test_result['success']:
                    issues.append(f"Node '{node.hostname}': SSH connection test failed - {test_result.get('message', 'Unknown error')}")
                elif not test_result.get('sudo_access', False):
                    issues.append(f"Node '{node.hostname}': SSH connection OK but sudo access failed")
                    
            except Exception as e:
                issues.append(f"Node '{node.hostname}': SSH connection test error - {str(e)}")
        
        return len(issues) == 0, issues
    
    def _run_ansible_playbook(self, playbook_path: str, inventory_file: str, 
                            extra_vars: Dict[str, Any] = None) -> tuple[bool, str]:
        """Run an Ansible playbook."""
        # Use the ansible-playbook from the virtual environment if available
        ansible_playbook_cmd = self._get_ansible_playbook_path()
        
        cmd = [
            ansible_playbook_cmd,
            '--forks', '1',
            '-i', inventory_file,
            playbook_path
        ]
        
        if extra_vars:
            cmd.extend(['--extra-vars', json.dumps(extra_vars)])
        
        try:
            # Log the command being executed for debugging
            cmd_str = ' '.join(cmd)
            print(f"Executing: {cmd_str}")

            # Use writable temp paths for constrained/runtime-sandboxed environments.
            env = os.environ.copy()
            env.setdefault('ANSIBLE_HOME', '/tmp/.ansible')
            env.setdefault('ANSIBLE_LOCAL_TEMP', '/tmp/ansible-local-tmp')
            # Use /tmp for remote temp to avoid ownership conflicts when switching
            # between connection user and become user across tasks.
            env.setdefault('ANSIBLE_REMOTE_TEMP', '/tmp')
            env.setdefault('ANSIBLE_LOG_PATH', '/tmp/ansible.log')
            os.makedirs(env['ANSIBLE_HOME'], exist_ok=True)
            os.makedirs(env['ANSIBLE_LOCAL_TEMP'], exist_ok=True)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.ansible_dir,
                env=env
            )
            success = result.returncode == 0

            stdout_lower = (result.stdout or "").lower()
            stderr_lower = (result.stderr or "").lower()
            if "no hosts matched" in stdout_lower or "no hosts matched" in stderr_lower:
                success = False
            
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
    
    def _parse_and_update_node_health(self, node: Node, output: str) -> None:
        """Parse health report from Ansible output and update node status."""
        try:
            import yaml
            import logging
            logger = logging.getLogger(__name__)
            
            # Look for health report in the YAML output from the debug task
            # The output format is YAML because of the ansible.builtin.yaml callback
            
            # Find the health_report section in the output
            health_report_start = output.find('health_report:')
            if health_report_start == -1:
                logger.warning(f"Could not find health_report in output for node {node.hostname}")
                return
            
            # Extract the health_report YAML block
            # Find the next TASK marker or end of output
            output_after_health = output[health_report_start:]
            next_task_pos = output_after_health.find('TASK [')
            
            if next_task_pos != -1:
                health_yaml = output_after_health[:next_task_pos]
            else:
                health_yaml = output_after_health
            
            # Parse the YAML
            try:
                # Parse just the health_report section
                parsed = yaml.safe_load(health_yaml)
                if parsed and 'health_report' in parsed:
                    health_data = parsed['health_report']
                    logger.info(f"Successfully parsed health data for node {node.hostname}: {health_data.keys()}")
                    self._update_node_from_health_data(node, health_data)
                    return
            except yaml.YAMLError as e:
                logger.warning(f"YAML parsing failed for node {node.hostname}: {e}")
            
            # Fallback: try to extract key information using regex
            logger.info(f"Falling back to regex extraction for node {node.hostname}")
            self._extract_health_info_from_text(node, output, output)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error parsing health report for node {node.hostname}: {e}")
    
    def _update_node_from_health_data(self, node: Node, health_data: dict) -> None:
        """Update node from parsed health data."""
        runtime = (
            health_data.get('kubernetes_distribution')
            or health_data.get('runtime')
            or node.cluster_runtime
            or 'microk8s'
        ).lower()

        runtime_status = None
        runtime_version = None

        if runtime == 'microk8s' and 'microk8s_installed' in health_data:
            if health_data['microk8s_installed']:
                microk8s_running = health_data.get('microk8s_running', False)
                service_active = health_data.get('service_active', False)
                runtime_status = 'running' if microk8s_running or service_active else 'installed'
            else:
                runtime_status = 'not_installed'
            runtime_version = health_data.get('microk8s_version')

        if runtime == 'k3s' and 'kubernetes_installed' in health_data:
            if health_data['kubernetes_installed']:
                runtime_status = 'running' if health_data.get('kubernetes_running', False) else 'installed'
            else:
                runtime_status = 'not_installed'
            runtime_version = health_data.get('kubernetes_version')

        if runtime_status:
            self._set_node_runtime_state(node, runtime, status=runtime_status, version=runtime_version)
        
        # Update control plane status (actual detection from Kubernetes)
        if 'is_control_plane' in health_data:
            # Convert string boolean to actual boolean
            if isinstance(health_data['is_control_plane'], str):
                node.is_control_plane = health_data['is_control_plane'].lower() in ('true', 'yes', '1')
            else:
                node.is_control_plane = bool(health_data['is_control_plane'])
        
        # Update network information
        if 'ip_address' in health_data and health_data['ip_address']:
            node.ip_address = health_data['ip_address']
        
        # Update system information
        if 'os_version' in health_data and health_data['os_version']:
            node.os_version = health_data['os_version']
        
        if 'kernel_version' in health_data and health_data['kernel_version']:
            node.kernel_version = health_data['kernel_version']
        
        if 'cpu_cores' in health_data:
            try:
                node.cpu_cores = int(health_data['cpu_cores'])
            except (ValueError, TypeError):
                pass
        
        if 'memory_gb' in health_data:
            try:
                node.memory_gb = float(health_data['memory_gb'])
            except (ValueError, TypeError):
                pass
        
        if 'disk_gb' in health_data:
            try:
                node.disk_gb = float(health_data['disk_gb'])
            except (ValueError, TypeError):
                pass
    
    def _extract_health_info_from_text(self, node: Node, health_text: str, full_output: str) -> None:
        """Extract health information from text output."""
        runtime = self._resolve_cluster_runtime(node=node)

        # Look for key indicators in the output
        if runtime == 'microk8s':
            if 'microk8s_installed.*true' in health_text.lower() or 'microk8s_installed": true' in health_text:
                if 'microk8s_running.*true' in health_text.lower() or 'microk8s_running": true' in health_text:
                    self._set_node_runtime_state(node, runtime, status='running')
                else:
                    self._set_node_runtime_state(node, runtime, status='installed')
            elif 'microk8s_installed.*false' in health_text.lower() or 'microk8s_installed": false' in health_text:
                self._set_node_runtime_state(node, runtime, status='not_installed')
            elif 'Not installed' in full_output:
                self._set_node_runtime_state(node, runtime, status='not_installed')
            elif 'microk8s status' in full_output.lower() and 'microk8s is running' in full_output.lower():
                self._set_node_runtime_state(node, runtime, status='running')
            elif 'microk8s' in full_output.lower() and 'command not found' in full_output.lower():
                self._set_node_runtime_state(node, runtime, status='not_installed')
        else:
            lowered = full_output.lower()
            if 'k3s service is running' in lowered or 'k3s agent service is running' in lowered:
                self._set_node_runtime_state(node, runtime, status='running')
            elif 'k3s not installed' in lowered or 'command not found' in lowered:
                self._set_node_runtime_state(node, runtime, status='not_installed')
            elif 'k3s is installed' in lowered:
                self._set_node_runtime_state(node, runtime, status='installed')
    
    def install_microk8s(self, node: Node) -> Operation:
        """Install MicroK8s on a node."""
        runtime = self._resolve_cluster_runtime(node=node)
        if runtime == 'k3s':
            raise ValueError(
                "Single-node runtime install is not supported for k3s worker flows. "
                "Use cluster setup/bootstrap instead."
            )

        operation = self._create_operation(
            operation_type='install',
            operation_name=f'Install {self._runtime_display_name(runtime)}',
            description=f'Install {self._runtime_display_name(runtime)} on node {node.hostname}',
            node=node,
            playbook_path='playbooks/install_microk8s.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            inventory_file = self._generate_inventory([node], runtime=runtime, cluster=node.cluster)
            playbook_path = os.path.join(self.playbooks_dir, self._runtime_playbook('install', runtime))
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                self._set_node_runtime_state(node, runtime, status='installed')
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
        runtime = self._resolve_cluster_runtime(node=node)
        playbook_name = self._runtime_playbook('status', runtime)
        operation = self._create_operation(
            operation_type='troubleshoot',
            operation_name=f'Check {self._runtime_display_name(runtime)} Node Status',
            description=f'Check status of node {node.hostname}',
            node=node,
            playbook_path=f'playbooks/{playbook_name}'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            inventory_file = self._generate_inventory([node], runtime=runtime, cluster=node.cluster)
            playbook_path = os.path.join(self.playbooks_dir, playbook_name)
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                # Update node status based on check results
                node.last_seen = datetime.utcnow()
                node.status = 'online'
                
                # Parse health report from output to update MicroK8s status
                self._parse_and_update_node_health(node, output)
                
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
        """Set up a cluster using the cluster's configured runtime."""
        runtime = self._resolve_cluster_runtime(cluster=cluster)
        playbook_name = self._runtime_playbook('setup', runtime)
        operation = self._create_operation(
            operation_type='configure',
            operation_name='Setup Cluster',
            description=f'Setup cluster {cluster.name}',
            cluster=cluster,
            playbook_path=f'playbooks/{playbook_name}'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                raise ValueError("Cluster has no nodes")
            
            inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster)
            playbook_path = os.path.join(self.playbooks_dir, playbook_name)
            
            extra_vars = {
                'cluster_name': cluster.name,
                'ha_enabled': cluster.ha_enabled,
                'network_cidr': cluster.network_cidr,
                'service_cidr': cluster.service_cidr,
                'kubernetes_distribution': runtime,
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
            
            stuck_operations = db.session.query(Operation).filter(
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
        runtime = self._resolve_cluster_runtime(cluster=cluster)
        playbook_name = self._runtime_playbook('scan', runtime)
        operation = self._create_operation(
            operation_type='scan',
            operation_name='Scan Cluster State',
            description=f'Validate configuration and check for drift in cluster {cluster.name}',
            cluster=cluster,
            playbook_path=f'playbooks/{playbook_name}'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message="Cluster has no nodes to scan")
                return operation
            
            inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster)
            playbook_path = os.path.join(self.playbooks_dir, playbook_name)
            
            extra_vars = {
                'cluster_name': cluster.name,
                'kubernetes_distribution': runtime,
                'expected_ha_enabled': cluster.ha_enabled,
                'expected_network_cidr': cluster.network_cidr,
                'expected_service_cidr': cluster.service_cidr,
                'expected_addons': ['coredns', 'local-path-provisioner'] if runtime == 'k3s' else ['dns', 'storage', 'ingress', 'dashboard']
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
                
                # Extract discovered nodes for auto-add feature
                discovered_nodes = self._extract_discovered_nodes(output)
                
                # Compare discovered nodes with existing nodes in orchestrator
                new_nodes = []
                if discovered_nodes:
                    # Get all existing node hostnames and IPs in this cluster
                    existing_hostnames = {node.hostname.lower() for node in cluster.nodes}
                    existing_ips = {node.ip_address for node in cluster.nodes if node.ip_address}
                    
                    # Find nodes that exist in cluster but not in orchestrator
                    for discovered in discovered_nodes:
                        hostname_lower = discovered['hostname'].lower()
                        ip = discovered['ip_address']
                        
                        # Check if this node is NOT already in orchestrator
                        if hostname_lower not in existing_hostnames and ip not in existing_ips:
                            new_nodes.append(discovered)
                    
                    # Store in operation metadata for display
                    operation.operation_metadata = json.dumps({
                        'scan_results': scan_results,
                        'discovered_nodes': discovered_nodes,
                        'new_nodes': new_nodes,  # Nodes that need to be added
                        'new_nodes_count': len(new_nodes)
                    })
                    
                    # Add a note in the output if new nodes were discovered
                    if new_nodes:
                        output += f"\n\n=== DISCOVERED NEW NODES ===\n"
                        output += f"Found {len(new_nodes)} node(s) in the cluster that are not yet in the orchestrator:\n"
                        for node in new_nodes:
                            output += f"  - {node['hostname']} ({node['ip_address']}) - Roles: {', '.join(node['roles'])}\n"
                        output += "\nThese nodes can be automatically added to the orchestrator.\n"
                
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
    
    def shutdown_cluster(self, cluster: Cluster, graceful: bool = True) -> Operation:
        """Gracefully shutdown a MicroK8s cluster."""
        runtime = self._resolve_cluster_runtime(cluster=cluster)
        playbook_name = self._runtime_playbook('shutdown', runtime)
        shutdown_type = 'graceful' if graceful else 'force'
        operation = self._create_operation(
            operation_type='shutdown',
            operation_name=f'Shutdown Cluster ({shutdown_type})',
            description=f'{shutdown_type.title()} shutdown of cluster {cluster.name}',
            cluster=cluster,
            playbook_path=f'playbooks/{playbook_name}'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message="Cluster has no nodes to shutdown")
                return operation
            
            inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster)
            playbook_path = os.path.join(self.playbooks_dir, playbook_name)
            
            extra_vars = {
                'cluster_name': cluster.name,
                'graceful_shutdown': graceful,
                'shutdown_timeout': 300 if graceful else 60  # 5 minutes for graceful, 1 minute for force
            }
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            if success:
                # Update cluster status
                cluster.status = 'shutdown'
                cluster.health_score = 0
                
                # Update node statuses
                for node in nodes:
                    self._set_node_runtime_state(node, runtime, status='shutdown')
                    node.last_seen = datetime.utcnow()
                
                db.session.commit()
                self._update_operation_status(operation, 'completed', success=True, output=output)
            else:
                self._update_operation_status(operation, 'failed', success=False,
                                            output=output, error_message='Cluster shutdown failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False,
                                        error_message=f"Cluster shutdown failed: {str(e)}")
        
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
    
    def _extract_discovered_nodes(self, ansible_output: str) -> list:
        """
        Extract discovered nodes from cluster scan output.
        This is used for the auto-discovery feature to suggest adding nodes.
        
        Args:
            ansible_output: Raw Ansible playbook output
            
        Returns:
            List of discovered node dictionaries with hostname, IP, labels, ready status
        """
        discovered = []
        try:
            import re
            json_match = re.search(r'DISCOVERED_NODES_JSON:\s*(\[.*\])', ansible_output, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, list):
                    return parsed
            
            # Look for the cluster_info data which contains total_nodes count
            # Then extract node hostnames and IPs from simpler patterns
            
            # Pattern 1: Extract from node status lines showing addresses
            # Format: 'addresses': [{'address': '192.0.2.68', 'type': 'InternalIP'}, {'address': 'devmod-02', 'type': 'Hostname'}]
            address_pattern = r"'addresses':\s*\[.*?'address':\s*'([\d.]+)',\s*'type':\s*'InternalIP'.*?'address':\s*'([\w-]+)',\s*'type':\s*'Hostname'"
            
            matches = re.finditer(address_pattern, ansible_output)
            
            for match in matches:
                ip_address = match.group(1)
                hostname = match.group(2)
                
                # Look for the labels section for this hostname to determine roles
                # Pattern: 'name': 'devmod-02', ... 'labels': {...}
                label_pattern = rf"'name':\s*'{re.escape(hostname)}'.*?'labels':\s*(\{{[^}}]*?microk8s[^}}]*?\}})"
                label_match = re.search(label_pattern, ansible_output, re.DOTALL)
                
                labels = {}
                roles = ['worker']  # Default
                
                if label_match:
                    # Check if it's a control plane node
                    if 'microk8s-controlplane' in label_match.group(1):
                        roles = ['control-plane']
                
                # Check if ready (look for Ready condition near this hostname)
                ready_pattern = rf"'name':\s*'{re.escape(hostname)}'.*?'type':\s*'Ready'.*?'status':\s*'(True|False)'"
                ready_match = re.search(ready_pattern, ansible_output, re.DOTALL)
                is_ready = ready_match and ready_match.group(1) == 'True'
                
                if hostname and ip_address:
                    # Avoid duplicates
                    if not any(d['hostname'] == hostname for d in discovered):
                        discovered.append({
                            'hostname': hostname,
                            'ip_address': ip_address,
                            'labels': labels,
                            'ready': is_ready,
                            'roles': roles
                        })
                    
            return discovered
            
        except Exception as e:
            print(f"Error extracting discovered nodes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_node_roles(self, labels: dict) -> list:
        """Extract node roles from Kubernetes labels."""
        roles = []
        for key in labels:
            if 'node-role.kubernetes.io/' in key:
                role = key.split('/')[-1]
                if role:
                    roles.append(role)
        return roles if roles else ['worker']
    
    def collect_hardware_report(self, cluster_id: int = None, node_id: int = None) -> Dict[str, Any]:
        """Collect comprehensive hardware information from cluster nodes."""
        try:
            # Determine which nodes to scan
            if node_id:
                nodes = [db.session.get(Node, node_id)]
                if not nodes[0]:
                    return {'success': False, 'error': 'Node not found'}
            elif cluster_id:
                cluster = db.session.get(Cluster, cluster_id)
                if not cluster:
                    return {'success': False, 'error': 'Cluster not found'}
                nodes = cluster.nodes
            else:
                nodes = db.session.query(Node).all()
            
            if not nodes:
                return {'success': False, 'error': 'No nodes found'}
            
            # Validate SSH connections before proceeding
            ssh_ready_nodes = [node for node in nodes if node.ssh_connection_ready]
            if not ssh_ready_nodes:
                ssh_issues = []
                for node in nodes:
                    ssh_issues.append(f"Node '{node.hostname}': {node.get_ssh_status_description()}")
                return {
                    'success': False, 
                    'error': f'No nodes with SSH connections ready. Issues: {"; ".join(ssh_issues)}'
                }
            
            # Use only SSH-ready nodes
            nodes = ssh_ready_nodes
            
            # Create operation record
            cluster_context = db.session.get(Cluster, cluster_id) if cluster_id else (nodes[0].cluster if nodes and nodes[0].cluster else None)
            operation = self._create_operation(
                operation_type='monitoring',
                operation_name='hardware_report',
                description=f'Collecting hardware report for {len(nodes)} node(s)',
                cluster=cluster_context,
                playbook_path='collect_hardware_report.yml'
            )
            
            # Generate inventory
            runtime = self._resolve_cluster_runtime(cluster=cluster_context, node=nodes[0] if nodes else None)
            inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster_context)
            
            # Verify inventory has valid hosts
            try:
                with open(inventory_file, 'r') as f:
                    inventory_data = json.load(f)
                valid_hosts = inventory_data.get('all', {}).get('children', {}).get('microk8s_nodes', {}).get('hosts', {})
                if not valid_hosts:
                    return {'success': False, 'error': 'No valid hosts in inventory - all nodes have SSH connection issues'}
            except Exception as e:
                return {'success': False, 'error': f'Failed to validate inventory: {str(e)}'}
            
            # Run hardware collection playbook
            playbook_path = os.path.join(self.playbooks_dir, 'collect_hardware_report.yml')
            
            self._update_operation_status(operation, 'running')
            
            ansible_playbook_cmd = self._get_ansible_playbook_path()
            cmd = [
                ansible_playbook_cmd,
                '-i', inventory_file,
                playbook_path,
                '-v'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.ansible_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout for hardware collection
            )
            
            # Parse results and update database
            hardware_data = self._parse_hardware_results(result.stdout, nodes)
            
            if result.returncode == 0:
                self._update_operation_status(
                    operation, 'completed', 
                    success=True, 
                    output=result.stdout
                )
                
                # Update nodes with hardware information
                self._update_nodes_hardware_info(hardware_data)
                
                return {
                    'success': True,
                    'operation_id': operation.id,
                    'hardware_data': hardware_data,
                    'nodes_updated': len(hardware_data)
                }
            else:
                self._update_operation_status(
                    operation, 'failed', 
                    success=False, 
                    output=result.stdout,
                    error_message=result.stderr
                )
                return {
                    'success': False,
                    'error': f'Hardware collection failed: {result.stderr}',
                    'operation_id': operation.id
                }
                
        except subprocess.TimeoutExpired:
            self._update_operation_status(
                operation, 'failed', 
                success=False,
                error_message='Hardware collection timed out'
            )
            return {'success': False, 'error': 'Hardware collection timed out'}
        except Exception as e:
            if 'operation' in locals():
                self._update_operation_status(
                    operation, 'failed', 
                    success=False,
                    error_message=str(e)
                )
            return {'success': False, 'error': str(e)}
        finally:
            # Clean up inventory file
            if 'inventory_file' in locals() and os.path.exists(inventory_file):
                os.remove(inventory_file)
    
    def _parse_hardware_results(self, ansible_output: str, nodes: list[Node]) -> Dict[str, Any]:
        """Parse hardware collection results from Ansible output."""
        hardware_data = {}
        
        try:
            # Look for hardware report data in the output
            lines = ansible_output.split('\n')
            current_host = None
            
            for line in lines:
                # Extract hostname from Ansible task output
                if 'ok: [' in line and ']' in line:
                    host_match = re.search(r'ok: \[([^\]]+)\]', line)
                    if host_match:
                        current_host = host_match.group(1)
                
                # Look for the JSON file path
                if current_host and 'HARDWARE_REPORT_JSON_FILE:' in line:
                    try:
                        # Extract file path from the line
                        file_start = line.find('HARDWARE_REPORT_JSON_FILE:') + len('HARDWARE_REPORT_JSON_FILE:')
                        json_file_path = line[file_start:].strip()
                        
                        # Remove any trailing quotes (both single and double quotes)
                        json_file_path = json_file_path.rstrip("'\"")
                        
                        # Remove any leading quotes if present
                        if json_file_path.startswith('"') or json_file_path.startswith("'"):
                            json_file_path = json_file_path[1:]
                        
                        # Fetch the JSON file from the remote node
                        hardware_info = self._fetch_json_from_remote(current_host, json_file_path, nodes)
                        if hardware_info:
                            hardware_data[current_host] = hardware_info
                            print(f"Successfully loaded hardware data from remote file for {current_host}")
                        else:
                            print(f"Failed to fetch hardware data file from {current_host}")
                            
                    except Exception as e:
                        print(f"Error processing hardware data file path for {current_host}: {e}")
                        
        except Exception as e:
            print(f"Error parsing hardware results: {e}")
        
        return hardware_data
    
    def execute_pending_operation(self, operation_id: int) -> Dict[str, Any]:
        """Execute a pending operation."""
        try:
            operation = db.session.get(Operation, operation_id)
            if not operation:
                return {'success': False, 'error': 'Operation not found'}
            
            if operation.status != 'pending':
                return {'success': False, 'error': f'Operation is not pending (status: {operation.status})'}
            
            # Update status to running
            self._update_operation_status(operation, 'running')
            
            # Get the target node or cluster
            if operation.node_id:
                node = db.session.get(Node, operation.node_id)
                if not node:
                    self._update_operation_status(operation, 'failed', success=False, error_message='Target node not found')
                    return {'success': False, 'error': 'Target node not found'}
                nodes = [node]
            elif operation.cluster_id:
                cluster = db.session.get(Cluster, operation.cluster_id)
                if not cluster:
                    self._update_operation_status(operation, 'failed', success=False, error_message='Target cluster not found')
                    return {'success': False, 'error': 'Target cluster not found'}
                nodes = cluster.nodes
            else:
                self._update_operation_status(operation, 'failed', success=False, error_message='No target specified')
                return {'success': False, 'error': 'No target specified'}
            
            # Check if playbook exists
            if operation.playbook_path:
                # operation.playbook_path already includes the ansible/ prefix, so use it directly
                playbook_path = os.path.join(os.path.dirname(self.ansible_dir), operation.playbook_path)
                if not os.path.exists(playbook_path):
                    self._update_operation_status(operation, 'failed', success=False, error_message=f'Playbook not found: {playbook_path}')
                    return {'success': False, 'error': f'Playbook not found: {playbook_path}'}

                # Validate SSH reachability/sudo before running Ansible.
                all_ready, ssh_issues = self._validate_ssh_connections(nodes)
                if not all_ready:
                    issues_text = "\n".join(ssh_issues)
                    self._update_operation_status(
                        operation,
                        'failed',
                        success=False,
                        output=issues_text,
                        error_message='SSH connection validation failed'
                    )
                    return {'success': False, 'error': f'SSH validation failed: {issues_text}'}
                
                # Generate inventory
                cluster_context = cluster if cluster_id else (nodes[0].cluster if nodes and nodes[0].cluster else None)
                runtime = self._resolve_cluster_runtime(cluster=cluster_context, node=nodes[0] if nodes else None)
                inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster_context)
                
                # Execute the playbook
                success, output = self._run_ansible_playbook(playbook_path, inventory_file)
                
                if success:
                    self._update_operation_status(operation, 'completed', success=True, output=output)
                    
                    # Parse and store Longhorn prerequisites results if this is a Longhorn operation
                    if operation.operation_name in ['check_longhorn_prerequisites', 'install_longhorn_prerequisites']:
                        self._parse_and_store_longhorn_results(output, nodes)
                else:
                    self._update_operation_status(operation, 'failed', success=False, output=output, error_message='Ansible playbook failed')
                
                return {'success': success, 'operation_id': operation.id, 'output': output}
            else:
                self._update_operation_status(operation, 'failed', success=False, error_message='No playbook specified')
                return {'success': False, 'error': 'No playbook specified'}
                
        except Exception as e:
            if 'operation' in locals():
                self._update_operation_status(operation, 'failed', success=False, error_message=str(e))
            return {'success': False, 'error': str(e)}

    def run_operation(self, operation_id: int) -> bool:
        """
        Backward-compatible wrapper used by legacy CLI commands.

        Returns True on success, False on failure.
        """
        result = self.execute_pending_operation(operation_id)
        return bool(result.get('success'))
    
    def _parse_and_store_longhorn_results(self, ansible_output: str, nodes: list[Node]):
        """Parse Longhorn prerequisites check results and update node records."""
        try:
            # Look for the longhorn report in the output (either check or install report)
            lines = ansible_output.split('\n')
            in_report = False
            report_lines = []
            
            for line in lines:
                if 'longhorn_check_report:' in line or 'longhorn_prerequisites_report:' in line:
                    in_report = True
                    continue
                elif in_report and line.strip().startswith('hostname:'):
                    # Start collecting the report
                    report_lines.append(line)
                elif in_report and line.strip() and not line.startswith('  ') and not line.startswith('-') and ':' in line and not line.startswith('    '):
                    # End of report section - we hit a main key that's not indented
                    if not line.startswith('hostname:') and not line.startswith('prerequisites_met:'):
                        break
                elif in_report:
                    report_lines.append(line)
            
            if report_lines:
                # Parse the YAML-like report
                report_data = self._parse_yaml_like_report('\n'.join(report_lines))
                
                # Update each node with the results
                for node in nodes:
                    node.longhorn_prerequisites_met = report_data.get('prerequisites_met', False)
                    node.longhorn_prerequisites_status = 'met' if report_data.get('prerequisites_met', False) else 'failed'
                    
                    # Handle different field names between check and install reports
                    if 'packages_status' in report_data:
                        # Check report format
                        node.longhorn_missing_packages = json.dumps(report_data.get('packages_status', {}).get('missing', []))
                        node.longhorn_missing_commands = json.dumps(report_data.get('commands_status', {}).get('missing', []))
                        node.longhorn_services_status = json.dumps(report_data.get('services_status', {}))
                        node.longhorn_storage_info = json.dumps(report_data.get('storage_info', {}))
                    else:
                        # Install report format
                        node.longhorn_missing_packages = json.dumps(report_data.get('packages_installed', []))
                        node.longhorn_missing_commands = json.dumps(report_data.get('commands_missing', []))
                        node.longhorn_services_status = json.dumps(report_data.get('services_running', {}))
                        node.longhorn_storage_info = json.dumps({
                            'block_devices_count': report_data.get('block_devices_count', 0),
                            'filesystem_types': report_data.get('filesystem_types', [])
                        })
                    
                    node.longhorn_last_check = datetime.utcnow()
                    
                    db.session.commit()
                    print(f"Updated Longhorn prerequisites status for {node.hostname}")
                    
        except Exception as e:
            print(f"Error parsing Longhorn results: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_yaml_like_report(self, report_text: str) -> Dict[str, Any]:
        """Parse YAML-like report from Ansible output."""
        result = {}
        current_section = None
        
        for line in report_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('-') or line.startswith('hostname:'):
                continue
                
            if ':' in line and not line.startswith('  '):
                # Main section
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'prerequisites_met':
                    result[key] = value.lower() == 'true'
                elif key in ['packages_status', 'commands_status', 'services_status', 'storage_info', 'functionality_tests', 'configuration']:
                    result[key] = {}
                    current_section = result[key]
                else:
                    result[key] = value
                    
            elif line.startswith('  ') and current_section is not None:
                # Sub-section item
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in ['missing', 'available', 'installed']:
                        # Parse list items
                        if value.startswith('['):
                            # Already a JSON list
                            current_section[key] = json.loads(value)
                        else:
                            # Initialize empty list
                            current_section[key] = []
                    elif key in ['enabled', 'running']:
                        # Boolean values
                        current_section[key] = value.lower() == 'true'
                    else:
                        # Other values
                        current_section[key] = value
            elif line.startswith('- ') and current_section is not None:
                # This is a list item, add it to the current list
                item = line[2:].strip()
                if 'available' in current_section:
                    current_section['available'].append(item)
                elif 'installed' in current_section:
                    current_section['installed'].append(item)
        
        return result
    
    def _fetch_json_from_remote(self, hostname: str, remote_file_path: str, nodes: list[Node]) -> Dict[str, Any]:
        """Fetch JSON file from remote node using SCP."""
        try:
            # Find the node to get SSH connection details
            node = None
            for n in nodes:
                if n.hostname == hostname:
                    node = n
                    break
            
            if not node:
                print(f"Node {hostname} not found in nodes list")
                return None
            
            # Create local temporary file
            local_file_path = f"/tmp/hardware_report_{hostname}_local.json"
            
            # Build SCP command
            scp_cmd = [
                'scp',
                '-o', 'ConnectTimeout=10',
                '-o', 'ServerAliveInterval=5',
                '-o', 'ServerAliveCountMax=3',
                '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=no'
            ]
            
            # Add SSH key if specified (must be before source/destination)
            if node.ssh_key_path:
                # Expand ~ to home directory
                ssh_key_path = os.path.expanduser(node.ssh_key_path)
                if os.path.exists(ssh_key_path):
                    scp_cmd.extend(['-i', ssh_key_path])
            
            # Add custom port if specified (must be before source/destination)
            if node.ssh_port and node.ssh_port != 22:
                scp_cmd.extend(['-P', str(node.ssh_port)])
            
            # Add source and destination paths
            ssh_user = node.ssh_user or 'root'  # Default to root if no user specified
            scp_cmd.extend([
                f'{ssh_user}@{node.ip_address}:{remote_file_path}',
                local_file_path
            ])
            
            
            # Execute SCP command
            result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Read and parse the JSON file
                if os.path.exists(local_file_path):
                    with open(local_file_path, 'r') as f:
                        hardware_info = json.load(f)
                    
                    # Clean up local file
                    os.remove(local_file_path)
                    
                    return hardware_info
                else:
                    print(f"Local file {local_file_path} not found after SCP")
                    return None
            else:
                print(f"SCP failed for {hostname}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"SCP timed out for {hostname}")
            return None
        except Exception as e:
            print(f"Error fetching JSON from {hostname}: {e}")
            return None
    
    def _update_nodes_hardware_info(self, hardware_data: Dict[str, Any]):
        """Update node records with collected hardware information."""
        try:
            for hostname, hw_info in hardware_data.items():
                node = db.session.query(Node).filter_by(hostname=hostname).first()
                if node:
                    # Update basic info
                    node.os_version = hw_info.get('os_version', node.os_version)
                    node.kernel_version = hw_info.get('kernel_version', node.kernel_version)
                    
                    # Update CPU info
                    cpu_info = hw_info.get('cpu_info', {})
                    node.cpu_cores = cpu_info.get('cores', node.cpu_cores)
                    node.cpu_usage_percent = cpu_info.get('usage_percent')
                    node.cpu_info = json.dumps(cpu_info)
                    
                    # Update memory info
                    memory_info = hw_info.get('memory_info', {})
                    node.memory_gb = memory_info.get('total_gb', node.memory_gb)
                    node.memory_usage_percent = memory_info.get('usage_percent')
                    node.memory_info = json.dumps(memory_info)
                    
                    # Update disk info
                    disk_info = hw_info.get('disk_info', {})
                    node.disk_gb = disk_info.get('total_gb', node.disk_gb)
                    node.disk_usage_percent = disk_info.get('usage_percent')
                    node.disk_info = json.dumps(disk_info)
                    
                    # Update detailed disk and partition info
                    disk_partitions_info = hw_info.get('disk_partitions_info', {})
                    if hasattr(node, 'disk_partitions_info'):
                        node.disk_partitions_info = json.dumps(disk_partitions_info)
                    
                    # Update storage volumes info (PVCs, PVs, etc.)
                    storage_volumes_info = hw_info.get('storage_volumes_info', {})
                    if hasattr(node, 'storage_volumes_info'):
                        node.storage_volumes_info = json.dumps(storage_volumes_info)
                    
                    # Update other hardware info
                    node.network_info = json.dumps(hw_info.get('network_info', {}))
                    node.gpu_info = json.dumps(hw_info.get('gpu_info', {}))
                    node.thermal_info = json.dumps(hw_info.get('thermal_info', {}))
                    node.hardware_info = json.dumps(hw_info.get('hardware_general', {}))
                    
                    # Update performance metrics
                    performance = hw_info.get('performance', {})
                    node.load_average = performance.get('load_average')
                    node.uptime_seconds = performance.get('uptime_seconds')
                    
                    # Update timestamp
                    node.last_seen = datetime.utcnow()
                    
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating node hardware info: {e}")
            raise
    
    def configure_hosts_file(self, cluster: Cluster) -> Operation:
        """Configure /etc/hosts file on all cluster nodes for proper hostname resolution."""
        operation = self._create_operation(
            operation_type='configure',
            operation_name='Configure /etc/hosts',
            description=f'Configure /etc/hosts file for cluster {cluster.name} to ensure proper hostname resolution',
            cluster=cluster,
            playbook_path='playbooks/configure_hosts_file.yml'
        )
        
        try:
            self._update_operation_status(operation, 'running')
            
            nodes = cluster.nodes
            if not nodes:
                self._update_operation_status(operation, 'failed', success=False,
                                            error_message="Cluster has no nodes to configure")
                return operation
            
            # Validate SSH connections before proceeding
            all_ready, ssh_issues = self._validate_ssh_connections(nodes)
            if not all_ready:
                self._update_operation_status(operation, 'failed', success=False,
                                            output="\n".join(ssh_issues),
                                            error_message="SSH connection validation failed")
                return operation
            
            runtime = self._resolve_cluster_runtime(cluster=cluster, node=nodes[0] if nodes else None)
            inventory_file = self._generate_inventory(nodes, runtime=runtime, cluster=cluster)
            playbook_path = os.path.join(self.playbooks_dir, 'configure_hosts_file.yml')
            
            extra_vars = {
                'cluster_name': cluster.name,
                'backup_original': True
            }
            
            success, output = self._run_ansible_playbook(playbook_path, inventory_file, extra_vars)
            
            if success:
                # Parse configuration results
                config_results = self._parse_hosts_config_results(output)
                
                # Update cluster status
                cluster.status = 'active'
                cluster.health_score = min(100, cluster.health_score + 10)  # Boost health score
                
                # Update node statuses
                for node in nodes:
                    node.last_seen = datetime.utcnow()
                    if node.status != 'online':
                        node.status = 'online'
                
                db.session.commit()
                
                # Create detailed output with results
                detailed_output = f"Hosts file configuration completed successfully!\n\n"
                detailed_output += f"Cluster: {cluster.name}\n"
                detailed_output += f"Nodes configured: {len(nodes)}\n"
                detailed_output += f"Configuration results:\n{json.dumps(config_results, indent=2)}\n\n"
                detailed_output += f"Ansible output:\n{output}"
                
                self._update_operation_status(operation, 'completed', success=True, output=detailed_output)
            else:
                cluster.status = 'degraded'
                db.session.commit()
                self._update_operation_status(operation, 'failed', success=False,
                                            output=output, error_message='Hosts file configuration failed')
        
        except Exception as e:
            self._update_operation_status(operation, 'failed', success=False,
                                        error_message=f"Hosts file configuration failed: {str(e)}")
        
        return operation
    
    def _parse_hosts_config_results(self, ansible_output: str) -> Dict[str, Any]:
        """Parse hosts configuration results from Ansible output."""
        results = {
            'overall_success': True,
            'nodes_configured': 0,
            'nodes_failed': 0,
            'verification_results': {},
            'backup_info': {},
            'issues': []
        }
        
        try:
            # Look for configuration summary in the output
            lines = ansible_output.split('\n')
            current_node = None
            
            for line in lines:
                # Look for node configuration results
                if 'ok: [' in line and ']' in line:
                    host_match = re.search(r'ok: \[([^\]]+)\]', line)
                    if host_match:
                        current_node = host_match.group(1)
                        results['nodes_configured'] += 1
                
                # Look for verification results
                if 'Hostname' in line and 'resolves to:' in line:
                    hostname_match = re.search(r'Hostname ([^\s]+) resolves to: (.+)', line)
                    if hostname_match:
                        hostname = hostname_match.group(1)
                        resolution = hostname_match.group(2)
                        results['verification_results'][hostname] = resolution
                        if resolution == 'FAILED':
                            results['overall_success'] = False
                            results['issues'].append(f"Hostname resolution failed for {hostname}")
                
                # Look for backup information
                if 'Original /etc/hosts backed up to:' in line:
                    backup_match = re.search(r'Original /etc/hosts backed up to: (.+)', line)
                    if backup_match and current_node:
                        results['backup_info'][current_node] = backup_match.group(1)
                
                # Look for DNS test results
                if 'DNS resolution for' in line and ':' in line:
                    dns_match = re.search(r'DNS resolution for ([^:]+): (.+)', line)
                    if dns_match:
                        hostname = dns_match.group(1)
                        dns_result = dns_match.group(2)
                        if dns_result == 'FAILED':
                            results['issues'].append(f"DNS resolution failed for {hostname}")
                
                # Look for duplicate entries warning
                if 'WARNING: Duplicate entries found' in line:
                    results['issues'].append("Duplicate entries found in /etc/hosts file")
                    results['overall_success'] = False
            
            # Count failed nodes
            results['nodes_failed'] = len([line for line in lines if 'failed:' in line and ']' in line])
            
        except Exception as e:
            results['issues'].append(f"Failed to parse configuration results: {str(e)}")
            results['overall_success'] = False
        
        return results
