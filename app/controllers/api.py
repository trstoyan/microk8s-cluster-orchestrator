"""API endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch, NetworkLease, NetworkInterface
from ..services.orchestrator import OrchestrationService
from ..services.wake_on_lan import WakeOnLANService

bp = Blueprint('api', __name__)
orchestrator = OrchestrationService()
wol_service = WakeOnLANService()

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
        
        for key, value in data.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        db.session.commit()
        return jsonify(node.to_dict())
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
        operation = orchestrator.check_node_status(node)
        return jsonify(operation.to_dict()), 202
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

@bp.route('/clusters/<int:cluster_id>/scan', methods=['POST'])
def scan_cluster_state(cluster_id):
    """Scan cluster to validate configuration and detect drift."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        operation = orchestrator.scan_cluster_state(cluster)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
