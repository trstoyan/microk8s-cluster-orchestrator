"""API endpoints for the MicroK8s Cluster Orchestrator."""

import os
import subprocess
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch, User, PlaybookTemplate, CustomPlaybook, PlaybookExecution, NodeGroup
from ..models.network_lease import NetworkLease, NetworkInterface
from ..services.orchestrator import OrchestrationService
from ..services.wake_on_lan import WakeOnLANService
from ..services.playbook_service import PlaybookService

bp = Blueprint('api', __name__)
orchestrator = OrchestrationService()
wol_service = WakeOnLANService()
playbook_service = PlaybookService()
logger = logging.getLogger(__name__)

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'microk8s-orchestrator'})

# Node endpoints
@bp.route('/nodes', methods=['GET'])
@login_required
def list_nodes():
    """List all nodes."""
    try:
        nodes = Node.query.all()
        return jsonify([node.to_dict() for node in nodes])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes', methods=['POST'])
@login_required
def create_node():
    """Create a new node."""
    try:
        data = request.get_json()
        node = Node(
            hostname=data['hostname'],
            ip_address=data['ip_address'],
            ssh_user=data.get('ssh_user', 'ubuntu'),
            ssh_port=data.get('ssh_port', 22),
            ssh_key_path=data.get('ssh_key_path'),
            cluster_id=data.get('cluster_id'),
            tags=data.get('tags'),
            notes=data.get('notes')
        )
        db.session.add(node)
        db.session.commit()
        return jsonify(node.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>', methods=['GET'])
@login_required
def get_node(node_id):
    """Get a specific node."""
    node = Node.query.get_or_404(node_id)
    return jsonify(node.to_dict())

@bp.route('/nodes/<int:node_id>', methods=['PUT'])
@login_required
def update_node(node_id):
    """Update a node."""
    try:
        node = Node.query.get_or_404(node_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Track changes for response
        changes = {}
        
        # Update allowed fields
        allowed_fields = ['hostname', 'ip_address', 'ssh_user', 'ssh_port', 'cluster_id', 'tags', 'notes']
        
        for field in allowed_fields:
            if field in data:
                old_value = getattr(node, field)
                new_value = data[field]
                
                # Handle special cases
                if field == 'cluster_id':
                    if new_value == 0 or new_value is None:
                        new_value = None
                    else:
                        # Verify cluster exists
                        cluster = Cluster.query.get(new_value)
                        if not cluster:
                            return jsonify({'error': f'Cluster with ID {new_value} not found'}), 400
                
                if field == 'ssh_port' and new_value is not None:
                    try:
                        new_value = int(new_value)
                        if not (1 <= new_value <= 65535):
                            return jsonify({'error': 'SSH port must be between 1 and 65535'}), 400
                    except (ValueError, TypeError):
                        return jsonify({'error': 'SSH port must be a valid integer'}), 400
                
                setattr(node, field, new_value)
                changes[field] = {'old': old_value, 'new': new_value}
        
        # Update timestamp
        from datetime import datetime
        node.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Node "{node.hostname}" updated successfully',
            'node': node.to_dict(),
            'changes': changes
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

@bp.route('/nodes/<int:node_id>', methods=['DELETE'])
@login_required
def delete_node(node_id):
    """Delete a node."""
    try:
        node = Node.query.get_or_404(node_id)
        db.session.delete(node)
        db.session.commit()
        return '', 204
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Cluster endpoints
@bp.route('/clusters', methods=['GET'])
@login_required
def list_clusters():
    """List all clusters."""
    try:
        clusters = Cluster.query.all()
        return jsonify([cluster.to_dict() for cluster in clusters])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters', methods=['POST'])
@login_required
def create_cluster():
    """Create a new cluster."""
    try:
        data = request.get_json()
        cluster = Cluster(
            name=data['name'],
            description=data.get('description'),
            ha_enabled=data.get('ha_enabled', False),
            addons=data.get('addons'),
            network_cidr=data.get('network_cidr', '10.1.0.0/16'),
            service_cidr=data.get('service_cidr', '10.152.183.0/24')
        )
        db.session.add(cluster)
        db.session.commit()
        return jsonify(cluster.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters/<int:cluster_id>', methods=['GET'])
@login_required
def get_cluster(cluster_id):
    """Get a specific cluster."""
    cluster = Cluster.query.get_or_404(cluster_id)
    return jsonify(cluster.to_dict())

# Router/Switch endpoints
@bp.route('/router-switches', methods=['GET'])
def list_router_switches():
    """List all router switches."""
    try:
        router_switches = RouterSwitch.query.all()
        return jsonify([rs.to_dict() for rs in router_switches])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches', methods=['POST'])
def create_router_switch():
    """Create a new router switch."""
    try:
        data = request.get_json()
        router_switch = RouterSwitch(
            hostname=data['hostname'],
            ip_address=data['ip_address'],
            device_type=data.get('device_type', 'mikrotik'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            mac_address=data.get('mac_address'),
            management_port=data.get('management_port', 22),
            cluster_id=data.get('cluster_id'),
            location=data.get('location'),
            contact_person=data.get('contact_person'),
            tags=data.get('tags'),
            notes=data.get('notes')
        )
        db.session.add(router_switch)
        db.session.commit()
        return jsonify(router_switch.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>', methods=['GET'])
def get_router_switch(router_switch_id):
    """Get a specific router switch."""
    router_switch = RouterSwitch.query.get_or_404(router_switch_id)
    return jsonify(router_switch.to_dict())

@bp.route('/router-switches/<int:router_switch_id>', methods=['PUT'])
def update_router_switch(router_switch_id):
    """Update a router switch."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(router_switch, key):
                setattr(router_switch, key, value)
        
        db.session.commit()
        return jsonify(router_switch.to_dict())
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>', methods=['DELETE'])
def delete_router_switch(router_switch_id):
    """Delete a router switch."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        db.session.delete(router_switch)
        db.session.commit()
        return '', 204
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Operation endpoints
@bp.route('/operations', methods=['GET'])
@login_required
def list_operations():
    """List all operations."""
    try:
        operations = Operation.query.order_by(Operation.created_at.desc()).all()
        return jsonify([op.to_dict() for op in operations])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/operations/<int:operation_id>', methods=['GET'])
@login_required
def get_operation(operation_id):
    """Get a specific operation."""
    operation = Operation.query.get_or_404(operation_id)
    return jsonify(operation.to_dict())

# Orchestration endpoints
@bp.route('/nodes/<int:node_id>/install-microk8s', methods=['POST'])
@login_required
def install_microk8s(node_id):
    """Install MicroK8s on a node."""
    try:
        node = Node.query.get_or_404(node_id)
        operation = orchestrator.install_microk8s(node)
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/check-status', methods=['POST'])
def check_node_status(node_id):
    """Check the status of a node."""
    try:
        node = Node.query.get_or_404(node_id)
        
        # Validate node has required SSH configuration
        if not node.ssh_key_path or not os.path.exists(node.ssh_key_path):
            return jsonify({
                'error': f'SSH key not configured or not found for node {node.hostname}',
                'details': 'Please configure SSH key in node settings'
            }), 400
        
        operation = orchestrator.check_node_status(node)
        return jsonify(operation.to_dict()), 202
    except FileNotFoundError as e:
        return jsonify({
            'error': 'Required file not found',
            'details': str(e)
        }), 500
    except PermissionError as e:
        return jsonify({
            'error': 'Permission denied',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to check node status',
            'details': str(e)
        }), 500

@bp.route('/nodes/<int:node_id>/check-longhorn-prerequisites', methods=['POST'])
@login_required
def check_longhorn_prerequisites(node_id):
    """Check Longhorn prerequisites on a node."""
    try:
        node = Node.query.get_or_404(node_id)
        
        # Create operation record
        operation = Operation(
            operation_type='check_longhorn_prerequisites',
            operation_name='Check Longhorn Prerequisites',
            description=f'Check Longhorn prerequisites on node {node.hostname}',
            playbook_path='ansible/playbooks/check_longhorn_prerequisites.yml',
            node_id=node_id,
            user_id=current_user.id
        )
        db.session.add(operation)
        db.session.commit()
        
        # Execute the operation immediately
        result = orchestrator.execute_pending_operation(operation.id)
        
        if result['success']:
            # Parse and save the Longhorn check results to the node
            try:
                output = result.get('output', '')
                # Look for the JSON report in the output
                import re
                json_match = re.search(r'"longhorn_check_report":\s*({.*?})\s*}', output, re.DOTALL)
                if json_match:
                    report_str = json_match.group(1) + '}'
                    # Clean up the JSON string
                    report_str = report_str.replace('\\"', '"').replace('\\n', '').replace('\n', '')
                    report = json.loads(report_str)
                    
                    # Update node with results
                    node.longhorn_prerequisites_met = report.get('prerequisites_met', False)
                    node.longhorn_prerequisites_status = 'met' if report.get('prerequisites_met') else 'failed'
                    node.longhorn_missing_packages = json.dumps(report.get('packages_status', {}).get('missing', []))
                    node.longhorn_missing_commands = json.dumps(report.get('commands_status', {}).get('missing', []))
                    node.longhorn_services_status = json.dumps(report.get('services_status', {}))
                    node.longhorn_storage_info = json.dumps(report.get('storage_info', {}))
                    node.longhorn_last_check = datetime.utcnow()
                    
                    db.session.commit()
                    logger.info(f"[LONGHORN] Updated node {node.hostname} prerequisites status: {node.longhorn_prerequisites_status}")
            except Exception as e:
                logger.error(f"[LONGHORN] Failed to parse check results: {str(e)}")
                # Don't fail the whole operation, just log the error
                pass
            
            return jsonify({
                'success': True,
                'operation_id': operation.id,
                'message': 'Longhorn prerequisites check completed successfully',
                'prerequisites_met': node.longhorn_prerequisites_met
            })
        else:
            return jsonify({
                'success': False,
                'operation_id': operation.id,
                'error': result['error'],
                'message': 'Longhorn prerequisites check failed'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/install-longhorn-prerequisites', methods=['POST'])
@login_required
def install_longhorn_prerequisites(node_id):
    """Install Longhorn prerequisites on a node."""
    try:
        node = Node.query.get_or_404(node_id)
        
        # Create operation record
        operation = Operation(
            operation_type='install_longhorn_prerequisites',
            operation_name='Install Longhorn Prerequisites',
            description=f'Install Longhorn prerequisites on node {node.hostname}',
            playbook_path='ansible/playbooks/install_longhorn_prerequisites.yml',
            node_id=node_id,
            user_id=current_user.id
        )
        db.session.add(operation)
        db.session.commit()
        
        # Execute the operation immediately
        result = orchestrator.execute_pending_operation(operation.id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'operation_id': operation.id,
                'message': 'Longhorn prerequisites installation completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'operation_id': operation.id,
                'error': result['error'],
                'message': 'Longhorn prerequisites installation failed'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/setup-new-node', methods=['POST'])
@login_required
def setup_new_node(node_id):
    """Setup a new node with all prerequisites and MicroK8s."""
    try:
        node = Node.query.get_or_404(node_id)
        
        # Create operation record
        operation = Operation(
            operation_type='setup_new_node',
            operation_name='Setup New Node',
            description=f'Complete setup of new node {node.hostname} with MicroK8s and Longhorn prerequisites',
            playbook_path='ansible/playbooks/setup_new_node.yml',
            node_id=node_id,
            user_id=current_user.id
        )
        db.session.add(operation)
        db.session.commit()
        
        # Execute the operation immediately
        result = orchestrator.execute_pending_operation(operation.id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'operation_id': operation.id,
                'message': 'New node setup completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'operation_id': operation.id,
                'error': result['error'],
                'message': 'New node setup failed'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters/<int:cluster_id>/setup', methods=['POST'])
@login_required
def setup_cluster(cluster_id):
    """Set up a cluster."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        operation = orchestrator.setup_cluster(cluster)
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters/<int:cluster_id>/configure-hosts', methods=['POST'])
@login_required
def configure_hosts_file(cluster_id):
    """Configure /etc/hosts file on all cluster nodes for proper hostname resolution."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        
        if not cluster.nodes:
            return jsonify({'error': 'Cluster has no nodes assigned'}), 400
        
        operation = orchestrator.configure_hosts_file(cluster)
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        
        return jsonify({
            'operation': operation.to_dict(),
            'message': f'Hosts file configuration started for cluster {cluster.name}',
            'nodes_count': len(cluster.nodes),
            'nodes': [{'hostname': node.hostname, 'ip_address': node.ip_address} for node in cluster.nodes]
        }), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/configure-hosts', methods=['POST'])
@login_required
def configure_all_nodes_hosts():
    """Configure /etc/hosts file on all nodes for proper hostname resolution."""
    try:
        nodes = Node.query.all()
        
        if not nodes:
            return jsonify({'error': 'No nodes found to configure'}), 400
        
        # Create a temporary cluster-like object for the operation
        class TempCluster:
            def __init__(self, nodes):
                self.name = "All Nodes"
                self.nodes = nodes
        
        temp_cluster = TempCluster(nodes)
        operation = orchestrator.configure_hosts_file(temp_cluster)
        
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        
        return jsonify({
            'operation': operation.to_dict(),
            'message': f'Hosts file configuration started for all {len(nodes)} nodes',
            'nodes_count': len(nodes),
            'nodes': [{'hostname': node.hostname, 'ip_address': node.ip_address, 'cluster': node.cluster.name if node.cluster else 'No cluster'} for node in nodes]
        }), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters/<int:cluster_id>/scan', methods=['POST'])
def scan_cluster_state(cluster_id):
    """Scan cluster to validate configuration and detect drift."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        
        # Validate cluster has nodes
        if not cluster.nodes:
            return jsonify({
                'error': f'Cluster {cluster.name} has no nodes to scan',
                'details': 'Please add nodes to the cluster before scanning'
            }), 400
        
        # Validate all nodes have SSH configuration
        for node in cluster.nodes:
            if not node.ssh_key_path or not os.path.exists(node.ssh_key_path):
                return jsonify({
                    'error': f'SSH key not configured for node {node.hostname}',
                    'details': 'Please configure SSH keys for all cluster nodes'
                }), 400
        
        operation = orchestrator.scan_cluster_state(cluster)
        return jsonify(operation.to_dict()), 202
    except FileNotFoundError as e:
        return jsonify({
            'error': 'Required file not found',
            'details': str(e)
        }), 500
    except PermissionError as e:
        return jsonify({
            'error': 'Permission denied',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to scan cluster state',
            'details': str(e)
        }), 500

@bp.route('/clusters/<int:cluster_id>/shutdown', methods=['POST'])
@login_required
def shutdown_cluster(cluster_id):
    """Gracefully shutdown a cluster."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        data = request.get_json() or {}
        graceful = data.get('graceful', True)  # Default to graceful shutdown
        
        operation = orchestrator.shutdown_cluster(cluster, graceful=graceful)
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Router/Switch orchestration endpoints
@bp.route('/router-switches/<int:router_switch_id>/backup-config', methods=['POST'])
def backup_router_config(router_switch_id):
    """Backup router switch configuration."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        operation = orchestrator.backup_router_config(router_switch)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>/check-status', methods=['POST'])
def check_router_status(router_switch_id):
    """Check the status of a router switch."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        operation = orchestrator.check_router_status(router_switch)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>/update-firmware', methods=['POST'])
def update_router_firmware(router_switch_id):
    """Update router switch firmware."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        data = request.get_json() or {}
        firmware_version = data.get('firmware_version')
        operation = orchestrator.update_router_firmware(router_switch, firmware_version)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>/restore-config', methods=['POST'])
def restore_router_config(router_switch_id):
    """Restore router switch configuration from backup."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        data = request.get_json() or {}
        backup_path = data.get('backup_path')
        operation = orchestrator.restore_router_config(router_switch, backup_path)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Network Lease endpoints
@bp.route('/network-leases', methods=['GET'])
def list_network_leases():
    """List all network leases."""
    try:
        # Query parameters for filtering
        router_switch_id = request.args.get('router_switch_id', type=int)
        node_id = request.args.get('node_id', type=int)
        status = request.args.get('status')
        is_active = request.args.get('is_active')
        is_cluster_node = request.args.get('is_cluster_node')
        
        query = NetworkLease.query
        
        # Apply filters
        if router_switch_id:
            query = query.filter(NetworkLease.router_switch_id == router_switch_id)
        if node_id:
            query = query.filter(NetworkLease.node_id == node_id)
        if status:
            query = query.filter(NetworkLease.status == status)
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            query = query.filter(NetworkLease.is_active == is_active_bool)
        if is_cluster_node is not None:
            is_cluster_node_bool = is_cluster_node.lower() in ('true', '1', 'yes')
            if is_cluster_node_bool:
                query = query.filter(NetworkLease.node_id.isnot(None))
            else:
                query = query.filter(NetworkLease.node_id.is_(None))
        
        # Order by last activity descending
        leases = query.order_by(NetworkLease.last_activity.desc()).all()
        return jsonify([lease.to_dict() for lease in leases])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/network-leases', methods=['POST'])
def create_network_lease():
    """Create a new network lease."""
    try:
        data = request.get_json()
        from datetime import datetime, timedelta
        
        # Calculate lease end time
        lease_duration = data.get('lease_duration_seconds', 86400)
        lease_start = datetime.utcnow()
        lease_end = lease_start + timedelta(seconds=lease_duration)
        
        lease = NetworkLease(
            mac_address=data['mac_address'],
            ip_address=data['ip_address'],
            hostname=data.get('hostname'),
            lease_start=lease_start,
            lease_end=lease_end,
            lease_duration_seconds=lease_duration,
            is_active=data.get('is_active', True),
            is_static=data.get('is_static', False),
            vlan_id=data.get('vlan_id'),
            subnet=data.get('subnet'),
            gateway=data.get('gateway'),
            dns_servers=data.get('dns_servers'),
            vendor_class=data.get('vendor_class'),
            client_id=data.get('client_id'),
            user_class=data.get('user_class'),
            device_type=data.get('device_type'),
            os_version=data.get('os_version'),
            device_model=data.get('device_model'),
            status=data.get('status', 'active'),
            router_switch_id=data['router_switch_id'],
            node_id=data.get('node_id'),
            discovered_by=data.get('discovered_by', 'manual'),
            tags=data.get('tags'),
            notes=data.get('notes')
        )
        db.session.add(lease)
        db.session.commit()
        return jsonify(lease.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/network-leases/<int:lease_id>', methods=['GET'])
def get_network_lease(lease_id):
    """Get a specific network lease."""
    lease = NetworkLease.query.get_or_404(lease_id)
    return jsonify(lease.to_dict())

@bp.route('/network-leases/<int:lease_id>', methods=['PUT'])
def update_network_lease(lease_id):
    """Update a network lease."""
    try:
        lease = NetworkLease.query.get_or_404(lease_id)
        data = request.get_json()
        
        # Update fields
        for key, value in data.items():
            if hasattr(lease, key) and key not in ['id', 'created_at']:
                setattr(lease, key, value)
        
        # Update last activity
        from datetime import datetime
        lease.last_activity = datetime.utcnow()
        
        db.session.commit()
        return jsonify(lease.to_dict())
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/network-leases/<int:lease_id>', methods=['DELETE'])
def delete_network_lease(lease_id):
    """Delete a network lease."""
    try:
        lease = NetworkLease.query.get_or_404(lease_id)
        db.session.delete(lease)
        db.session.commit()
        return '', 204
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Network Interface endpoints
@bp.route('/network-interfaces', methods=['GET'])
def list_network_interfaces():
    """List all network interfaces."""
    try:
        router_switch_id = request.args.get('router_switch_id', type=int)
        interface_type = request.args.get('interface_type')
        status = request.args.get('status')
        
        query = NetworkInterface.query
        
        if router_switch_id:
            query = query.filter(NetworkInterface.router_switch_id == router_switch_id)
        if interface_type:
            query = query.filter(NetworkInterface.interface_type == interface_type)
        if status:
            query = query.filter(NetworkInterface.status == status)
        
        interfaces = query.order_by(NetworkInterface.name).all()
        return jsonify([interface.to_dict() for interface in interfaces])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/network-interfaces', methods=['POST'])
def create_network_interface():
    """Create a new network interface."""
    try:
        data = request.get_json()
        interface = NetworkInterface(
            name=data['name'],
            interface_type=data['interface_type'],
            mac_address=data.get('mac_address'),
            enabled=data.get('enabled', True),
            mtu=data.get('mtu', 1500),
            speed_mbps=data.get('speed_mbps'),
            duplex=data.get('duplex'),
            ip_addresses=data.get('ip_addresses'),
            dhcp_server_enabled=data.get('dhcp_server_enabled', False),
            dhcp_pool_start=data.get('dhcp_pool_start'),
            dhcp_pool_end=data.get('dhcp_pool_end'),
            dhcp_lease_time=data.get('dhcp_lease_time', 86400),
            vlan_id=data.get('vlan_id'),
            vlan_mode=data.get('vlan_mode'),
            allowed_vlans=data.get('allowed_vlans'),
            status=data.get('status', 'unknown'),
            router_switch_id=data['router_switch_id'],
            description=data.get('description'),
            tags=data.get('tags')
        )
        db.session.add(interface)
        db.session.commit()
        return jsonify(interface.to_dict()), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/network-interfaces/<int:interface_id>', methods=['GET'])
def get_network_interface(interface_id):
    """Get a specific network interface."""
    interface = NetworkInterface.query.get_or_404(interface_id)
    return jsonify(interface.to_dict())

@bp.route('/network-interfaces/<int:interface_id>', methods=['PUT'])
def update_network_interface(interface_id):
    """Update a network interface."""
    try:
        interface = NetworkInterface.query.get_or_404(interface_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(interface, key) and key not in ['id', 'created_at']:
                setattr(interface, key, value)
        
        db.session.commit()
        return jsonify(interface.to_dict())
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/network-interfaces/<int:interface_id>', methods=['DELETE'])
def delete_network_interface(interface_id):
    """Delete a network interface."""
    try:
        interface = NetworkInterface.query.get_or_404(interface_id)
        db.session.delete(interface)
        db.session.commit()
        return '', 204
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Network discovery and monitoring endpoints
@bp.route('/router-switches/<int:router_switch_id>/scan-leases', methods=['POST'])
def scan_router_leases(router_switch_id):
    """Scan router for DHCP leases and update database."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        operation = orchestrator.scan_dhcp_leases(router_switch)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/router-switches/<int:router_switch_id>/scan-interfaces', methods=['POST'])
def scan_router_interfaces(router_switch_id):
    """Scan router for network interfaces and update database."""
    try:
        router_switch = RouterSwitch.query.get_or_404(router_switch_id)
        operation = orchestrator.scan_network_interfaces(router_switch)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/network/topology', methods=['GET'])
def get_network_topology():
    """Get network topology information including nodes and their connections."""
    try:
        # Get all active leases with node relationships
        leases = NetworkLease.query.filter(NetworkLease.is_active == True).all()
        
        # Get all router switches with their interfaces
        router_switches = RouterSwitch.query.all()
        
        # Get all cluster nodes
        nodes = Node.query.all()
        
        # Build topology data
        topology = {
            'router_switches': [rs.to_dict() for rs in router_switches],
            'network_leases': [lease.to_dict() for lease in leases],
            'cluster_nodes': [node.to_dict() for node in nodes],
            'connections': []
        }
        
        # Add connection information
        for lease in leases:
            if lease.node_id:
                topology['connections'].append({
                    'type': 'dhcp_lease',
                    'source': f'router_{lease.router_switch_id}',
                    'target': f'node_{lease.node_id}',
                    'lease_info': {
                        'ip_address': lease.ip_address,
                        'mac_address': lease.mac_address,
                        'hostname': lease.hostname,
                        'is_active': lease.is_active,
                        'time_remaining': lease.time_remaining
                    }
                })
        
        return jsonify(topology)
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

# Operation management endpoints
@bp.route('/operations/cleanup', methods=['POST'])
def cleanup_stuck_operations():
    """Clean up operations that have been running too long."""
    try:
        data = request.get_json() or {}
        timeout_hours = data.get('timeout_hours', 2)
        
        result = orchestrator.cleanup_stuck_operations(timeout_hours)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Hardware report endpoints
@bp.route('/hardware-report', methods=['POST'])
@login_required
def collect_hardware_report():
    """Collect hardware report for all nodes or specific cluster/node."""
    try:
        data = request.get_json() or {}
        cluster_id = data.get('cluster_id')
        node_id = data.get('node_id')
        
        result = orchestrator.collect_hardware_report(cluster_id=cluster_id, node_id=node_id)
        
        if result['success']:
            return jsonify({
                'message': 'Hardware report collection started',
                'operation_id': result['operation_id'],
                'nodes_updated': result.get('nodes_updated', 0)
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hardware-report/cluster/<int:cluster_id>', methods=['GET'])
@login_required
def get_cluster_hardware_report(cluster_id):
    """Get hardware report for a specific cluster."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        nodes_data = []
        
        for node in cluster.nodes:
            node_dict = node.to_dict()
            
            # Parse JSON fields for better display
            try:
                import json
                if node.cpu_info:
                    node_dict['cpu_info_parsed'] = json.loads(node.cpu_info)
                if node.memory_info:
                    node_dict['memory_info_parsed'] = json.loads(node.memory_info)
                if node.disk_info:
                    node_dict['disk_info_parsed'] = json.loads(node.disk_info)
                if node.network_info:
                    node_dict['network_info_parsed'] = json.loads(node.network_info)
                if node.gpu_info:
                    node_dict['gpu_info_parsed'] = json.loads(node.gpu_info)
                if node.thermal_info:
                    node_dict['thermal_info_parsed'] = json.loads(node.thermal_info)
                if node.hardware_info:
                    node_dict['hardware_info_parsed'] = json.loads(node.hardware_info)
            except json.JSONDecodeError:
                pass  # Keep original string if JSON parsing fails
                
            nodes_data.append(node_dict)
        
        return jsonify({
            'cluster': cluster.to_dict(),
            'nodes': nodes_data,
            'summary': {
                'total_nodes': len(nodes_data),
                'total_cpu_cores': sum(node.cpu_cores or 0 for node in cluster.nodes),
                'total_memory_gb': sum(node.memory_gb or 0 for node in cluster.nodes),
                'total_disk_gb': sum(node.disk_gb or 0 for node in cluster.nodes),
                'nodes_with_gpu': len([n for n in cluster.nodes if n.gpu_info and 'present": true' in n.gpu_info.lower()]),
                'average_cpu_usage': sum(node.cpu_usage_percent or 0 for node in cluster.nodes) / len(cluster.nodes) if cluster.nodes else 0,
                'average_memory_usage': sum(node.memory_usage_percent or 0 for node in cluster.nodes) / len(cluster.nodes) if cluster.nodes else 0,
                'average_disk_usage': sum(node.disk_usage_percent or 0 for node in cluster.nodes) / len(cluster.nodes) if cluster.nodes else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hardware-report/node/<int:node_id>', methods=['GET'])
@login_required
def get_node_hardware_report(node_id):
    """Get detailed hardware report for a specific node."""
    try:
        node = Node.query.get_or_404(node_id)
        node_dict = node.to_dict()
        
        # Parse JSON fields for detailed view
        try:
            import json
            if node.cpu_info:
                node_dict['cpu_info_parsed'] = json.loads(node.cpu_info)
            if node.memory_info:
                node_dict['memory_info_parsed'] = json.loads(node.memory_info)
            if node.disk_info:
                node_dict['disk_info_parsed'] = json.loads(node.disk_info)
            if node.network_info:
                node_dict['network_info_parsed'] = json.loads(node.network_info)
            if node.gpu_info:
                node_dict['gpu_info_parsed'] = json.loads(node.gpu_info)
            if node.thermal_info:
                node_dict['thermal_info_parsed'] = json.loads(node.thermal_info)
            if node.hardware_info:
                node_dict['hardware_info_parsed'] = json.loads(node.hardware_info)
        except json.JSONDecodeError:
            pass  # Keep original string if JSON parsing fails
        
        return jsonify(node_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hardware-report', methods=['GET'])
@login_required
def get_all_hardware_report():
    """Get hardware report for all nodes."""
    try:
        nodes = Node.query.all()
        nodes_data = []
        
        for node in nodes:
            node_dict = node.to_dict()
            
            # Parse JSON fields for better display
            try:
                import json
                if node.cpu_info:
                    node_dict['cpu_info_parsed'] = json.loads(node.cpu_info)
                if node.memory_info:
                    node_dict['memory_info_parsed'] = json.loads(node.memory_info)
                if node.disk_info:
                    node_dict['disk_info_parsed'] = json.loads(node.disk_info)
                if node.network_info:
                    node_dict['network_info_parsed'] = json.loads(node.network_info)
                if node.gpu_info:
                    node_dict['gpu_info_parsed'] = json.loads(node.gpu_info)
                if node.thermal_info:
                    node_dict['thermal_info_parsed'] = json.loads(node.thermal_info)
                if node.hardware_info:
                    node_dict['hardware_info_parsed'] = json.loads(node.hardware_info)
            except json.JSONDecodeError:
                pass  # Keep original string if JSON parsing fails
                
            nodes_data.append(node_dict)
        
        return jsonify({
            'nodes': nodes_data,
            'summary': {
                'total_nodes': len(nodes_data),
                'total_cpu_cores': sum(node.cpu_cores or 0 for node in nodes),
                'total_memory_gb': sum(node.memory_gb or 0 for node in nodes),
                'total_disk_gb': sum(node.disk_gb or 0 for node in nodes),
                'nodes_with_gpu': len([n for n in nodes if n.gpu_info and 'present": true' in n.gpu_info.lower()]),
                'average_cpu_usage': sum(node.cpu_usage_percent or 0 for node in nodes) / len(nodes) if nodes else 0,
                'average_memory_usage': sum(node.memory_usage_percent or 0 for node in nodes) / len(nodes) if nodes else 0,
                'average_disk_usage': sum(node.disk_usage_percent or 0 for node in nodes) / len(nodes) if nodes else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# UPS Management API Endpoints
# =============================================================================

@bp.route('/ups', methods=['GET'])
@login_required
def list_ups():
    """List all UPS devices."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        ups_devices = controller.get_all_ups()
        return jsonify(ups_devices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/scan', methods=['POST'])
@login_required
def scan_ups():
    """Scan for connected UPS devices and configure them automatically."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        ups_devices = controller.scan_and_configure_ups()
        return jsonify({
            'success': True,
            'message': f'Found and configured {len(ups_devices)} UPS device(s)',
            'ups_devices': ups_devices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/<int:ups_id>', methods=['GET'])
@login_required
def get_ups(ups_id):
    """Get UPS device by ID."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        ups_device = controller.get_ups_by_id(ups_id)
        
        if not ups_device:
            return jsonify({'error': 'UPS not found'}), 404
        
        return jsonify(ups_device)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/<int:ups_id>/status', methods=['GET'])
@login_required
def get_ups_status(ups_id):
    """Get detailed status of a specific UPS."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        status_info = controller.get_ups_status(ups_id)
        
        if 'error' in status_info:
            return jsonify(status_info), 500
        
        return jsonify(status_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/<int:ups_id>/test', methods=['POST'])
@login_required
def test_ups_connection(ups_id):
    """Test connection to a UPS."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.test_ups_connection(ups_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/<int:ups_id>', methods=['DELETE'])
@login_required
def remove_ups(ups_id):
    """Remove UPS configuration."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.remove_ups(ups_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/<int:ups_id>/settings', methods=['PUT'])
@login_required
def update_ups_settings(ups_id):
    """Update UPS settings."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        data = request.get_json() or {}
        result = controller.update_ups_settings(ups_id, **data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Power Management Rules API Endpoints
# =============================================================================

@bp.route('/ups/rules', methods=['GET'])
@login_required
def list_power_rules():
    """List power management rules."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        
        ups_id = request.args.get('ups_id', type=int)
        cluster_id = request.args.get('cluster_id', type=int)
        
        rules = controller.get_power_rules(ups_id, cluster_id)
        return jsonify(rules)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/rules', methods=['POST'])
@login_required
def create_power_rule():
    """Create a new power management rule."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['ups_id', 'cluster_id', 'power_event', 'cluster_action']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        result = controller.create_power_rule(
            ups_id=data['ups_id'],
            cluster_id=data['cluster_id'],
            power_event=data['power_event'],
            cluster_action=data['cluster_action'],
            name=data.get('name'),
            description=data.get('description'),
            battery_threshold=data.get('battery_threshold'),
            action_delay=data.get('action_delay', 0),
            action_timeout=data.get('action_timeout', 300),
            priority=data.get('priority', 100),
            auto_reverse=data.get('auto_reverse', False),
            notify_on_trigger=data.get('notify_on_trigger', True),
            notify_on_completion=data.get('notify_on_completion', True),
            notify_on_failure=data.get('notify_on_failure', True),
            enabled=data.get('enabled', True)
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_power_rule(rule_id):
    """Delete a power management rule."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.delete_power_rule(rule_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# Power Monitoring API Endpoints
# =============================================================================

@bp.route('/ups/monitor/start', methods=['POST'])
@login_required
def start_power_monitoring():
    """Start power event monitoring."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.start_power_monitoring()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/monitor/stop', methods=['POST'])
@login_required
def stop_power_monitoring():
    """Stop power event monitoring."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.stop_power_monitoring()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/monitor/status', methods=['GET'])
@login_required
def get_power_monitoring_status():
    """Get power monitoring status."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        status = controller.get_power_monitoring_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# NUT Services API Endpoints
# =============================================================================

@bp.route('/ups/services', methods=['GET'])
@login_required
def get_nut_service_status():
    """Get NUT service status."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.get_nut_service_status()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/services/restart', methods=['POST'])
@login_required
def restart_nut_services():
    """Restart NUT services."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        result = controller.restart_nut_services()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# UPS Configuration API Endpoints
# =============================================================================

@bp.route('/ups/events', methods=['GET'])
@login_required
def get_power_events():
    """Get available power event types."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        events = controller.get_power_events()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ups/actions', methods=['GET'])
@login_required
def get_cluster_actions():
    """Get available cluster action types."""
    try:
        from ..services.ups_controller import UPSController
        controller = UPSController()
        actions = controller.get_cluster_actions()
        return jsonify(actions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Wake-on-LAN endpoints
@bp.route('/nodes/<int:node_id>/wol/wake', methods=['POST'])
@login_required
def wake_node(node_id):
    """Send Wake-on-LAN packet to a node."""
    try:
        node = db.session.query(Node).filter(Node.id == node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        retries = request.json.get('retries', 3) if request.json else 3
        delay = request.json.get('delay', 1.0) if request.json else 1.0
        
        result = wol_service.wake_node(node, retries, delay)
        
        if result.get('success', False):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters/<int:cluster_id>/wol/wake', methods=['POST'])
@login_required
def wake_cluster(cluster_id):
    """Send Wake-on-LAN packets to all nodes in a cluster."""
    try:
        cluster = db.session.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            return jsonify({'error': 'Cluster not found'}), 404
        
        retries = request.json.get('retries', 3) if request.json else 3
        delay = request.json.get('delay', 1.0) if request.json else 1.0
        
        result = wol_service.wake_cluster(cluster_id, retries, delay)
        
        if result.get('success', False):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/wol/status', methods=['GET'])
@login_required
def get_node_wol_status(node_id):
    """Get Wake-on-LAN status for a node."""
    try:
        node = db.session.query(Node).filter(Node.id == node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        status = wol_service.get_wol_status(node)
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/wol/enable', methods=['POST'])
@login_required
def enable_node_wol(node_id):
    """Enable Wake-on-LAN on a node."""
    try:
        node = db.session.query(Node).filter(Node.id == node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        result = wol_service.enable_wol_on_node(node)
        
        if result.get('success', False):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/wol/disable', methods=['POST'])
@login_required
def disable_node_wol(node_id):
    """Disable Wake-on-LAN on a node."""
    try:
        node = db.session.query(Node).filter(Node.id == node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        result = wol_service.disable_wol_on_node(node)
        
        if result.get('success', False):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/wol/collect-mac', methods=['POST'])
@login_required
def collect_mac_addresses():
    """Collect MAC addresses from specified nodes."""
    try:
        data = request.json
        if not data or 'node_ids' not in data:
            return jsonify({'error': 'node_ids required'}), 400
        
        node_ids = data['node_ids']
        nodes = db.session.query(Node).filter(Node.id.in_(node_ids)).all()
        
        if not nodes:
            return jsonify({'error': 'No nodes found'}), 404
        
        result = wol_service.collect_mac_addresses(nodes)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes/<int:node_id>/wol/configure', methods=['PUT'])
@login_required
def configure_node_wol(node_id):
    """Configure Wake-on-LAN settings for a node."""
    try:
        node = db.session.query(Node).filter(Node.id == node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        data = request.json
        if not data:
            return jsonify({'error': 'Configuration data required'}), 400
        
        # Update allowed WoL fields
        if 'wol_enabled' in data:
            node.wol_enabled = bool(data['wol_enabled'])
        
        if 'wol_mac_address' in data:
            node.wol_mac_address = data['wol_mac_address']
        
        if 'wol_method' in data:
            node.wol_method = data['wol_method']
        
        if 'wol_broadcast_address' in data:
            node.wol_broadcast_address = data['wol_broadcast_address']
        
        if 'wol_port' in data:
            node.wol_port = int(data['wol_port'])
        
        if 'is_virtual_node' in data:
            node.is_virtual_node = bool(data['is_virtual_node'])
        
        if 'proxmox_vm_id' in data:
            node.proxmox_vm_id = data['proxmox_vm_id']
        
        if 'proxmox_host_id' in data:
            node.proxmox_host_id = data['proxmox_host_id']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Wake-on-LAN configuration updated for {node.hostname}',
            'node': node.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# System Update endpoints
@bp.route('/system/update/status', methods=['GET'])
@login_required
def get_update_status():
    """Get current git status and available updates."""
    try:
        # Get current commit
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        current_commit = result.stdout.strip() if result.returncode == 0 else None
        
        # Get current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        current_branch = result.stdout.strip() if result.returncode == 0 else None
        
        # Check for local changes
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        has_local_changes = bool(result.stdout.strip())
        local_changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Fetch latest from remote (for current branch)
        subprocess.run(['git', 'fetch', 'origin', current_branch], 
                      capture_output=True, text=True, cwd=os.getcwd())
        
        # Check if there are updates available (compare to origin/current_branch, not origin/main)
        remote_branch = f'origin/{current_branch}'
        result = subprocess.run(['git', 'rev-list', f'HEAD..{remote_branch}', '--count'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        updates_available = int(result.stdout.strip()) if result.returncode == 0 else 0
        
        # Get latest commit info from current branch
        result = subprocess.run(['git', 'log', remote_branch, '-1', '--format=%H|%s|%an|%ad', '--date=iso'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        latest_commit_info = None
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) >= 4:
                latest_commit_info = {
                    'hash': parts[0],
                    'message': parts[1],
                    'author': parts[2],
                    'date': parts[3]
                }
        
        return jsonify({
            'current_commit': current_commit,
            'current_branch': current_branch,
            'has_local_changes': has_local_changes,
            'local_changes': local_changes,
            'updates_available': updates_available,
            'latest_commit': latest_commit_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/update', methods=['POST'])
@login_required
def perform_update():
    """Perform system update."""
    try:
        data = request.get_json() or {}
        strategy = data.get('strategy', 'stash')  # stash, commit, discard
        
        # Run the update script with the specified strategy
        script_path = os.path.join(os.getcwd(), 'scripts', 'update_pi.sh')
        
        # Create a non-interactive version of the update
        if strategy == 'stash':
            commands = [
                'git stash push -m "Web UI update"',
                'git pull origin main',
                'git stash pop || true'  # Don't fail if stash pop has conflicts
            ]
        elif strategy == 'commit':
            commands = [
                'git add .',
                'git commit -m "Local changes before web UI update" || true',
                'git pull origin main'
            ]
        elif strategy == 'discard':
            commands = [
                'git reset --hard HEAD',
                'git pull origin main'
            ]
        else:
            return jsonify({'error': 'Invalid update strategy'}), 400
        
        results = []
        for cmd in commands:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
            results.append({
                'command': cmd,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            if result.returncode != 0 and '|| true' not in cmd:
                break
        
        # Check if update was successful
        success = all(r['returncode'] == 0 for r in results)
        
        return jsonify({
            'success': success,
            'strategy': strategy,
            'results': results,
            'message': 'Update completed successfully' if success else 'Update completed with some issues'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/restart', methods=['POST'])
@login_required
def restart_system():
    """Restart the orchestrator system."""
    try:
        import subprocess
        import sys
        import os
        import signal
        
        # Check if running as systemd service
        systemd_service = os.environ.get('SYSTEMD_SERVICE', '')
        if systemd_service:
            # Restart via systemctl
            try:
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', systemd_service],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return jsonify({
                        'success': True,
                        'message': f'System service {systemd_service} restarted successfully'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to restart service: {result.stderr}'
                    }), 500
            except subprocess.TimeoutExpired:
                return jsonify({
                    'success': False,
                    'error': 'Service restart timed out'
                }), 500
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error restarting service: {str(e)}'
                }), 500
        
        # Check if running via gunicorn/uwsgi
        if 'gunicorn' in sys.argv[0] or 'uwsgi' in sys.argv[0]:
            # Send graceful restart signal
            try:
                os.kill(os.getppid(), signal.SIGHUP)
                return jsonify({
                    'success': True,
                    'message': 'Application server restart signal sent'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Failed to send restart signal: {str(e)}'
                }), 500
        
        # Fallback: Use restart helper script for clean restart
        try:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            restart_script = project_root / 'scripts' / 'restart_server.sh'
            
            # Make sure script is executable
            if restart_script.exists():
                subprocess.run(['chmod', '+x', str(restart_script)], check=True)
                
                # Schedule restart after response is sent
                def delayed_restart():
                    import time
                    time.sleep(2)  # Give time for response to be sent
                    try:
                        # Use restart helper script for clean restart
                        subprocess.Popen([str(restart_script)], 
                                       cwd=str(project_root),
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        # Exit current process after spawning restart
                        time.sleep(1)
                        os._exit(0)
                    except Exception as e:
                        print(f"Failed to restart: {e}")
                
                import threading
                restart_thread = threading.Thread(target=delayed_restart)
                restart_thread.daemon = True
                restart_thread.start()
                
                return jsonify({
                    'success': True,
                    'message': 'Server restart initiated. Please wait 5-10 seconds...'
                })
            else:
                # Fallback to old method if script doesn't exist
                return jsonify({
                    'success': False,
                    'error': 'Restart script not found. Use: make restart'
                }), 500
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to restart application: {str(e)}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'System restart failed: {str(e)}'
        }), 500

@bp.route('/system/timezone', methods=['GET'])
@login_required
def get_timezone_info():
    """Get current timezone information."""
    try:
        import subprocess
        from datetime import datetime
        
        # Get current timezone
        try:
            result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                  capture_output=True, text=True, timeout=10)
            current_timezone = result.stdout.strip() if result.returncode == 0 else 'Unknown'
        except:
            current_timezone = 'Unknown'
        
        # Get system time
        try:
            system_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            system_time = 'Unknown'
        
        # Get UTC offset
        try:
            utc_offset = datetime.now().strftime('%z')
        except:
            utc_offset = 'Unknown'
        
        return jsonify({
            'current_timezone': current_timezone,
            'system_time': system_time,
            'utc_offset': utc_offset
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/timezone/list', methods=['GET'])
@login_required
def get_timezone_list():
    """Get list of available timezones."""
    try:
        import subprocess
        
        # Get list of timezones
        try:
            result = subprocess.run(['timedatectl', 'list-timezones'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                timezones = []
                for tz in result.stdout.strip().split('\n'):
                    if tz.strip():
                        # Format timezone for display
                        display = tz.replace('_', ' ').replace('/', ' - ')
                        timezones.append({
                            'value': tz,
                            'display': display
                        })
                
                # Get current timezone for comparison
                current_result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                              capture_output=True, text=True, timeout=10)
                current_timezone = current_result.stdout.strip() if current_result.returncode == 0 else None
                
                return jsonify({
                    'timezones': timezones,
                    'current_timezone': current_timezone
                })
            else:
                return jsonify({'error': 'Failed to list timezones'}), 500
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Timeout while listing timezones'}), 500
        except Exception as e:
            return jsonify({'error': f'Error listing timezones: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/timezone', methods=['POST'])
@login_required
def set_timezone():
    """Set system timezone."""
    try:
        import subprocess
        from flask import request
        
        data = request.get_json()
        timezone = data.get('timezone')
        
        if not timezone:
            return jsonify({'success': False, 'error': 'Timezone is required'}), 400
        
        # Set timezone using timedatectl
        try:
            result = subprocess.run(['sudo', 'timedatectl', 'set-timezone', timezone], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': f'Timezone set to {timezone}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to set timezone: {result.stderr}'
                }), 500
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Timeout while setting timezone'
            }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error setting timezone: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Timezone setting failed: {str(e)}'
        }), 500

@bp.route('/system/prerequisites', methods=['GET'])
@login_required
def check_prerequisites():
    """Check system prerequisites."""
    try:
        import subprocess
        import shutil
        import os
        
        checks = []
        all_passed = True
        
        # Check Python version
        try:
            import sys
            python_version = sys.version_info
            if python_version >= (3, 8):
                checks.append({
                    'name': 'Python Version',
                    'message': f'Python {python_version.major}.{python_version.minor}.{python_version.micro} is compatible',
                    'passed': True,
                    'details': 'Minimum required: Python 3.8'
                })
            else:
                checks.append({
                    'name': 'Python Version',
                    'message': f'Python {python_version.major}.{python_version.minor}.{python_version.micro} is too old',
                    'passed': False,
                    'details': 'Minimum required: Python 3.8'
                })
                all_passed = False
        except Exception as e:
            checks.append({
                'name': 'Python Version',
                'message': 'Unable to check Python version',
                'passed': False,
                'details': str(e)
            })
            all_passed = False
        
        # Check required commands
        required_commands = ['ansible', 'ssh', 'git', 'systemctl']
        for cmd in required_commands:
            try:
                if shutil.which(cmd):
                    checks.append({
                        'name': f'{cmd.title()} Command',
                        'message': f'{cmd} is available',
                        'passed': True
                    })
                else:
                    checks.append({
                        'name': f'{cmd.title()} Command',
                        'message': f'{cmd} is not installed or not in PATH',
                        'passed': False,
                        'details': f'Install {cmd} to continue'
                    })
                    all_passed = False
            except Exception as e:
                checks.append({
                    'name': f'{cmd.title()} Command',
                    'message': f'Unable to check {cmd}',
                    'passed': False,
                    'details': str(e)
                })
                all_passed = False
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free // (1024**3)
            if free_gb >= 1:
                checks.append({
                    'name': 'Disk Space',
                    'message': f'{free_gb} GB free space available',
                    'passed': True,
                    'details': f'Total: {total // (1024**3)} GB, Used: {used // (1024**3)} GB'
                })
            else:
                checks.append({
                    'name': 'Disk Space',
                    'message': f'Only {free_gb} GB free space available',
                    'passed': False,
                    'details': 'Minimum 1 GB free space recommended'
                })
                all_passed = False
        except Exception as e:
            checks.append({
                'name': 'Disk Space',
                'message': 'Unable to check disk space',
                'passed': False,
                'details': str(e)
            })
            all_passed = False
        
        # Check write permissions
        try:
            test_file = 'test_write_permission.tmp'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            checks.append({
                'name': 'Write Permissions',
                'message': 'Write permissions are available',
                'passed': True
            })
        except Exception as e:
            checks.append({
                'name': 'Write Permissions',
                'message': 'No write permissions in current directory',
                'passed': False,
                'details': str(e)
            })
            all_passed = False
        
        return jsonify({
            'checks': checks,
            'all_passed': all_passed
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/logs/<log_type>', methods=['GET'])
@login_required
def get_system_logs(log_type):
    """Get system logs."""
    try:
        import os
        from pathlib import Path
        
        # Define log file paths
        log_files = {
            'orchestrator': 'logs/orchestrator.log',
            'ansible': 'logs/ansible.log',
            'system': '/var/log/syslog'
        }
        
        if log_type not in log_files:
            return jsonify({'error': 'Invalid log type'}), 400
        
        log_file = log_files[log_type]
        
        # Check if file exists
        if not os.path.exists(log_file):
            return jsonify({
                'logs': [],
                'message': f'Log file {log_file} not found'
            })
        
        # Read last 100 lines of the log file
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last 100 lines
                logs = [line.strip() for line in lines[-100:]]
                
                return jsonify({
                    'logs': logs,
                    'file': log_file,
                    'total_lines': len(lines)
                })
        except PermissionError:
            return jsonify({
                'error': f'Permission denied reading {log_file}'
            }), 403
        except Exception as e:
            return jsonify({
                'error': f'Error reading log file: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/logs/<log_type>', methods=['DELETE'])
@login_required
def clear_system_logs(log_type):
    """Clear system logs."""
    try:
        import os
        
        # Define log file paths
        log_files = {
            'orchestrator': 'logs/orchestrator.log',
            'ansible': 'logs/ansible.log',
            'system': '/var/log/syslog'
        }
        
        if log_type not in log_files:
            return jsonify({'error': 'Invalid log type'}), 400
        
        log_file = log_files[log_type]
        
        # Check if file exists
        if not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'message': f'Log file {log_file} does not exist'
            })
        
        # Clear the log file (truncate to 0 bytes)
        try:
            with open(log_file, 'w') as f:
                pass  # Truncate file
            
            return jsonify({
                'success': True,
                'message': f'Cleared {log_type} logs'
            })
        except PermissionError:
            return jsonify({
                'success': False,
                'error': f'Permission denied clearing {log_file}'
            }), 403
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error clearing log file: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Log clearing failed: {str(e)}'
        }), 500

# Playbook Template endpoints
@bp.route('/playbook-templates', methods=['GET'])
@login_required
def list_playbook_templates():
    """List all playbook templates."""
    try:
        category = request.args.get('category')
        is_public = request.args.get('is_public')
        if is_public is not None:
            is_public = is_public.lower() == 'true'
        
        templates = playbook_service.get_templates(category=category, is_public=is_public)
        return jsonify([template.to_dict() for template in templates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-templates', methods=['POST'])
@login_required
def create_playbook_template():
    """Create a new playbook template."""
    try:
        data = request.get_json()
        template = playbook_service.create_template(
            name=data['name'],
            description=data.get('description', ''),
            category=data['category'],
            yaml_content=data['yaml_content'],
            variables_schema=data.get('variables_schema'),
            tags=data.get('tags'),
            is_public=data.get('is_public', True),
            created_by=current_user.id
        )
        return jsonify(template.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-templates/<int:template_id>', methods=['GET'])
@login_required
def get_playbook_template(template_id):
    """Get a specific playbook template."""
    try:
        template = playbook_service.get_template(template_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        return jsonify(template.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-templates/<int:template_id>', methods=['PUT'])
@login_required
def update_playbook_template(template_id):
    """Update a playbook template."""
    try:
        data = request.get_json()
        template = playbook_service.update_template(template_id, **data)
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        return jsonify(template.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_playbook_template(template_id):
    """Delete a playbook template."""
    try:
        success = playbook_service.delete_template(template_id)
        if not success:
            return jsonify({'error': 'Template not found or cannot be deleted'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Custom Playbook endpoints
@bp.route('/custom-playbooks', methods=['GET'])
@login_required
def list_custom_playbooks():
    """List custom playbooks."""
    try:
        is_public = request.args.get('is_public')
        if is_public is not None:
            is_public = is_public.lower() == 'true'
        
        playbooks = playbook_service.get_custom_playbooks(
            created_by=current_user.id if not is_public else None,
            is_public=is_public
        )
        return jsonify([playbook.to_dict() for playbook in playbooks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/custom-playbooks', methods=['POST'])
@login_required
def create_custom_playbook():
    """Create a new custom playbook."""
    try:
        data = request.get_json()
        playbook = playbook_service.create_custom_playbook(
            name=data['name'],
            description=data.get('description', ''),
            yaml_content=data['yaml_content'],
            visual_config=data.get('visual_config'),
            category=data.get('category', 'custom'),
            tags=data.get('tags'),
            is_public=data.get('is_public', False),
            created_by=current_user.id
        )
        return jsonify(playbook.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/custom-playbooks/<int:playbook_id>', methods=['GET'])
@login_required
def get_custom_playbook(playbook_id):
    """Get a specific custom playbook."""
    try:
        playbook = playbook_service.get_custom_playbook(playbook_id)
        if not playbook:
            return jsonify({'error': 'Playbook not found'}), 404
        return jsonify(playbook.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/custom-playbooks/<int:playbook_id>', methods=['PUT'])
@login_required
def update_custom_playbook(playbook_id):
    """Update a custom playbook."""
    try:
        data = request.get_json()
        playbook = playbook_service.update_custom_playbook(playbook_id, **data)
        if not playbook:
            return jsonify({'error': 'Playbook not found'}), 404
        return jsonify(playbook.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/custom-playbooks/<int:playbook_id>', methods=['DELETE'])
@login_required
def delete_custom_playbook(playbook_id):
    """Delete a custom playbook."""
    try:
        success = playbook_service.delete_custom_playbook(playbook_id)
        if not success:
            return jsonify({'error': 'Playbook not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Node Group endpoints
@bp.route('/node-groups', methods=['GET'])
@login_required
def list_node_groups():
    """List node groups."""
    try:
        groups = playbook_service.get_node_groups(created_by=current_user.id)
        return jsonify([group.to_dict() for group in groups])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/node-groups', methods=['POST'])
@login_required
def create_node_group():
    """Create a new node group."""
    try:
        data = request.get_json()
        group = playbook_service.create_node_group(
            name=data['name'],
            description=data.get('description', ''),
            group_type=data['group_type'],
            criteria=data.get('criteria'),
            tags=data.get('tags'),
            created_by=current_user.id
        )
        return jsonify(group.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/node-groups/<int:group_id>', methods=['GET'])
@login_required
def get_node_group(group_id):
    """Get a specific node group."""
    try:
        group = playbook_service.get_node_group(group_id)
        if not group:
            return jsonify({'error': 'Node group not found'}), 404
        return jsonify(group.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/node-groups/<int:group_id>', methods=['PUT'])
@login_required
def update_node_group(group_id):
    """Update a node group."""
    try:
        data = request.get_json()
        group = playbook_service.update_node_group(group_id, **data)
        if not group:
            return jsonify({'error': 'Node group not found'}), 404
        return jsonify(group.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/node-groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_node_group(group_id):
    """Delete a node group."""
    try:
        success = playbook_service.delete_node_group(group_id)
        if not success:
            return jsonify({'error': 'Node group not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Playbook Execution endpoints
@bp.route('/playbook-executions', methods=['GET'])
@login_required
def list_playbook_executions():
    """List playbook executions."""
    try:
        status = request.args.get('status')
        executions = playbook_service.get_executions(
            created_by=current_user.id,
            status=status
        )
        return jsonify([execution.to_dict() for execution in executions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-executions', methods=['POST'])
@login_required
def execute_playbook():
    """Execute a playbook."""
    try:
        data = request.get_json()
        execution = playbook_service.execute_playbook(
            execution_name=data['execution_name'],
            yaml_content=data['yaml_content'],
            targets=data['targets'],
            extra_vars=data.get('extra_vars'),
            created_by=current_user.id
        )
        return jsonify(execution.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-executions/<int:execution_id>', methods=['GET'])
@login_required
def get_playbook_execution(execution_id):
    """Get a specific playbook execution."""
    try:
        execution = playbook_service.get_execution(execution_id)
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404
        return jsonify(execution.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbook-executions/<int:execution_id>/cancel', methods=['POST'])
@login_required
def cancel_playbook_execution(execution_id):
    """Cancel a running playbook execution."""
    try:
        success = playbook_service.cancel_execution(execution_id)
        if not success:
            return jsonify({'error': 'Execution not found or cannot be cancelled'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Playbook utility endpoints
@bp.route('/playbooks/validate-yaml', methods=['POST'])
@login_required
def validate_yaml():
    """Validate YAML content."""
    try:
        data = request.get_json()
        yaml_content = data.get('yaml_content', '')
        is_valid, message = playbook_service.validate_yaml(yaml_content)
        return jsonify({
            'valid': is_valid,
            'message': message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbooks/resolve-targets', methods=['POST'])
@login_required
def resolve_targets():
    """Resolve target specifications to actual nodes."""
    try:
        data = request.get_json()
        targets = data.get('targets', [])
        nodes = playbook_service.resolve_targets(targets)
        return jsonify([node.to_dict() for node in nodes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbooks/generate-inventory', methods=['POST'])
@login_required
def generate_inventory():
    """Generate Ansible inventory from nodes."""
    try:
        data = request.get_json()
        node_ids = data.get('node_ids', [])
        nodes = Node.query.filter(Node.id.in_(node_ids)).all()
        inventory = playbook_service.generate_inventory(nodes)
        return jsonify({'inventory': inventory})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playbooks/system-templates/init', methods=['POST'])
@login_required
def init_system_templates():
    """Initialize system templates."""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        playbook_service.create_system_templates()
        return jsonify({'success': True, 'message': 'System templates initialized'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Operation endpoints
@bp.route('/operations/<int:operation_id>/execute', methods=['POST'])
@login_required
def execute_operation(operation_id):
    """Execute a pending operation."""
    try:
        result = orchestrator.execute_pending_operation(operation_id)
        
        if result['success']:
            return jsonify({
                'message': 'Operation executed successfully',
                'operation_id': result['operation_id']
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/operations/<int:operation_id>/add-discovered-nodes', methods=['POST'])
@login_required
def add_discovered_nodes(operation_id):
    """
    Add nodes that were discovered during a cluster scan.
    This automatically creates node entries for all nodes found in the Kubernetes cluster
    that aren't yet in the orchestrator.
    """
    try:
        operation = Operation.query.get_or_404(operation_id)
        
        # Verify this is a scan operation
        if operation.operation_type != 'scan':
            return jsonify({
                'success': False,
                'error': 'This operation is not a cluster scan'
            }), 400
        
        # Parse metadata to get discovered nodes
        if not operation.operation_metadata:
            return jsonify({
                'success': False,
                'error': 'No discovered nodes found in this scan'
            }), 404
        
        metadata = json.loads(operation.operation_metadata)
        new_nodes = metadata.get('new_nodes', [])
        
        if not new_nodes:
            return jsonify({
                'success': False,
                'error': 'No new nodes to add'
            }), 404
        
        # Get the cluster from the operation
        if not operation.cluster_id:
            return jsonify({
                'success': False,
                'error': 'Operation is not associated with a cluster'
            }), 400
        
        cluster = Cluster.query.get(operation.cluster_id)
        
        # Add each discovered node
        from ..services.ssh_key_manager import SSHKeyManager
        ssh_manager = SSHKeyManager()
        
        added_nodes = []
        errors = []
        
        for discovered in new_nodes:
            try:
                # Create node entry
                node = Node(
                    hostname=discovered['hostname'],
                    ip_address=discovered['ip_address'],
                    ssh_user='ubuntu',  # Default, user can change later
                    ssh_port=22,
                    cluster_id=cluster.id,
                    status='active',  # Already in cluster, so active
                    microk8s_status='installed',  # Already running MicroK8s
                    is_control_plane='control-plane' in discovered.get('roles', []) or 'master' in discovered.get('roles', []),
                    notes=f"Auto-discovered from cluster scan on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                db.session.add(node)
                db.session.flush()  # Get the node ID
                
                # Generate SSH key
                try:
                    key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
                    
                    node.ssh_key_path = key_info['private_key_path']
                    node.ssh_public_key = key_info['public_key']
                    node.ssh_key_fingerprint = key_info['fingerprint']
                    node.ssh_key_generated = True
                    node.ssh_key_status = 'generated'
                    
                    # Generate setup instructions
                    instructions = ssh_manager.get_setup_instructions(
                        node.hostname,
                        key_info['public_key'],
                        node.ssh_user
                    )
                    node.ssh_setup_instructions = instructions
                    
                    db.session.commit()
                    
                    added_nodes.append({
                        'id': node.id,
                        'hostname': node.hostname,
                        'ip_address': node.ip_address
                    })
                    
                except Exception as key_error:
                    logger.error(f"[NODE-DISCOVERY] Failed to generate SSH key for {node.hostname}: {str(key_error)}")
                    errors.append(f"{node.hostname}: SSH key generation failed - {str(key_error)}")
                    # Still add the node, just without SSH key
                    db.session.commit()
                    added_nodes.append({
                        'id': node.id,
                        'hostname': node.hostname,
                        'ip_address': node.ip_address,
                        'warning': 'SSH key generation failed'
                    })
                    
            except Exception as e:
                logger.error(f"[NODE-DISCOVERY] Failed to add node {discovered.get('hostname')}: {str(e)}")
                errors.append(f"{discovered.get('hostname', 'Unknown')}: {str(e)}")
                db.session.rollback()
        
        return jsonify({
            'success': True,
            'added_count': len(added_nodes),
            'added_nodes': added_nodes,
            'errors': errors,
            'message': f'Successfully added {len(added_nodes)} node(s) to the orchestrator'
        })
        
    except Exception as e:
        logger.error(f"[NODE-DISCOVERY] Error adding discovered nodes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
