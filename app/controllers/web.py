"""Web interface endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch, NetworkLease, NetworkInterface

bp = Blueprint('web', __name__)

@bp.route('/')
@login_required
def dashboard():
    """Main dashboard."""
    clusters = Cluster.query.all()
    nodes = Node.query.all()
    router_switches = RouterSwitch.query.all()
    recent_operations = Operation.query.filter_by(user_id=current_user.id).order_by(Operation.created_at.desc()).limit(10).all() if not current_user.is_admin else Operation.query.order_by(Operation.created_at.desc()).limit(10).all()
    
    stats = {
        'total_clusters': len(clusters),
        'total_nodes': len(nodes),
        'online_nodes': len([n for n in nodes if n.status == 'online']),
        'total_router_switches': len(router_switches),
        'online_router_switches': len([rs for rs in router_switches if rs.status == 'online']),
        'recent_operations': len(recent_operations)
    }
    
    return render_template('dashboard.html', 
                         clusters=clusters, 
                         nodes=nodes, 
                         router_switches=router_switches,
                         recent_operations=recent_operations,
                         stats=stats)

@bp.route('/nodes')
@login_required
def nodes():
    """Nodes management page."""
    nodes = Node.query.all()
    return render_template('nodes.html', nodes=nodes)

@bp.route('/nodes/add', methods=['GET', 'POST'])
@login_required
def add_node():
    """Add a new node."""
    if request.method == 'POST':
        try:
            node = Node(
                hostname=request.form['hostname'],
                ip_address=request.form['ip_address'],
                ssh_user=request.form.get('ssh_user', 'ubuntu'),
                ssh_port=int(request.form.get('ssh_port', 22)),
                ssh_key_path=request.form.get('ssh_key_path'),
                cluster_id=request.form.get('cluster_id') or None,
                notes=request.form.get('notes')
            )
            db.session.add(node)
            db.session.commit()
            flash('Node added successfully!', 'success')
            return redirect(url_for('web.nodes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding node: {str(e)}', 'error')
    
    clusters = Cluster.query.all()
    return render_template('add_node.html', clusters=clusters)

@bp.route('/clusters')
@login_required
def clusters():
    """Clusters management page."""
    clusters = Cluster.query.all()
    return render_template('clusters.html', clusters=clusters)

@bp.route('/clusters/add', methods=['GET', 'POST'])
@login_required
def add_cluster():
    """Add a new cluster."""
    if request.method == 'POST':
        try:
            cluster = Cluster(
                name=request.form['name'],
                description=request.form.get('description'),
                ha_enabled='ha_enabled' in request.form,
                network_cidr=request.form.get('network_cidr', '10.1.0.0/16'),
                service_cidr=request.form.get('service_cidr', '10.152.183.0/24')
            )
            db.session.add(cluster)
            db.session.commit()
            flash('Cluster added successfully!', 'success')
            return redirect(url_for('web.clusters'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding cluster: {str(e)}', 'error')
    
    return render_template('add_cluster.html')

@bp.route('/operations')
@login_required
def operations():
    """Operations history page."""
    if current_user.is_admin:
        operations = Operation.query.order_by(Operation.created_at.desc()).all()
    else:
        operations = Operation.query.filter_by(user_id=current_user.id).order_by(Operation.created_at.desc()).all()
    return render_template('operations.html', operations=operations)

@bp.route('/operations/<int:operation_id>')
@login_required
def operation_detail(operation_id):
    """Operation detail page."""
    operation = Operation.query.get_or_404(operation_id)
    
    # Check if user has permission to view this operation
    if not current_user.is_admin and operation.user_id != current_user.id:
        flash('Access denied. You can only view your own operations.', 'error')
        return redirect(url_for('web.operations'))
    
    return render_template('operation_detail.html', operation=operation)

# Router/Switch routes
@bp.route('/router-switches')
@login_required
def router_switches():
    """Router switches management page."""
    router_switches = RouterSwitch.query.all()
    return render_template('router_switches.html', router_switches=router_switches)

@bp.route('/router-switches/add', methods=['GET', 'POST'])
@login_required
def add_router_switch():
    """Add a new router switch."""
    if request.method == 'POST':
        try:
            router_switch = RouterSwitch(
                hostname=request.form['hostname'],
                ip_address=request.form['ip_address'],
                device_type=request.form.get('device_type', 'mikrotik'),
                model=request.form.get('model'),
                serial_number=request.form.get('serial_number'),
                mac_address=request.form.get('mac_address'),
                management_port=int(request.form.get('management_port', 22)),
                cluster_id=request.form.get('cluster_id') or None,
                location=request.form.get('location'),
                contact_person=request.form.get('contact_person'),
                notes=request.form.get('notes'),
                tags=request.form.get('tags')
            )
            db.session.add(router_switch)
            db.session.commit()
            flash('Router switch added successfully!', 'success')
            return redirect(url_for('web.router_switches'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding router switch: {str(e)}', 'error')
    
    clusters = Cluster.query.all()
    return render_template('add_router_switch.html', clusters=clusters)

@bp.route('/router-switches/<int:router_switch_id>')
@login_required
def router_switch_detail(router_switch_id):
    """Router switch detail page."""
    router_switch = RouterSwitch.query.get_or_404(router_switch_id)
    operations = Operation.query.filter_by(router_switch_id=router_switch_id).order_by(Operation.created_at.desc()).limit(10).all()
    return render_template('router_switch_detail.html', router_switch=router_switch, operations=operations)

@bp.route('/router-switches/<int:router_switch_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_router_switch(router_switch_id):
    """Edit a router switch."""
    router_switch = RouterSwitch.query.get_or_404(router_switch_id)
    
    if request.method == 'POST':
        try:
            router_switch.hostname = request.form['hostname']
            router_switch.ip_address = request.form['ip_address']
            router_switch.device_type = request.form.get('device_type', 'mikrotik')
            router_switch.model = request.form.get('model')
            router_switch.serial_number = request.form.get('serial_number')
            router_switch.mac_address = request.form.get('mac_address')
            router_switch.management_port = int(request.form.get('management_port', 22))
            router_switch.cluster_id = request.form.get('cluster_id') or None
            router_switch.location = request.form.get('location')
            router_switch.contact_person = request.form.get('contact_person')
            router_switch.notes = request.form.get('notes')
            router_switch.tags = request.form.get('tags')
            
            # Update firmware information if provided
            if request.form.get('firmware_version'):
                router_switch.firmware_version = request.form.get('firmware_version')
            if request.form.get('routeros_version'):
                router_switch.routeros_version = request.form.get('routeros_version')
            if request.form.get('bootloader_version'):
                router_switch.bootloader_version = request.form.get('bootloader_version')
            if request.form.get('architecture'):
                router_switch.architecture = request.form.get('architecture')
            
            # Update hardware information if provided
            if request.form.get('cpu_model'):
                router_switch.cpu_model = request.form.get('cpu_model')
            if request.form.get('cpu_frequency_mhz'):
                router_switch.cpu_frequency_mhz = int(request.form.get('cpu_frequency_mhz'))
            if request.form.get('total_memory_mb'):
                router_switch.total_memory_mb = int(request.form.get('total_memory_mb'))
            if request.form.get('total_disk_mb'):
                router_switch.total_disk_mb = int(request.form.get('total_disk_mb'))
            if request.form.get('port_count'):
                router_switch.port_count = int(request.form.get('port_count'))
            
            # Update network configuration if provided
            if request.form.get('management_vlan'):
                router_switch.management_vlan = int(request.form.get('management_vlan'))
            if request.form.get('default_gateway'):
                router_switch.default_gateway = request.form.get('default_gateway')
            if request.form.get('dns_servers'):
                router_switch.dns_servers = request.form.get('dns_servers')
            
            # Update configuration settings
            router_switch.config_backup_enabled = 'config_backup_enabled' in request.form
            router_switch.auto_update_enabled = 'auto_update_enabled' in request.form
            router_switch.stp_enabled = 'stp_enabled' in request.form
            router_switch.lldp_enabled = 'lldp_enabled' in request.form
            router_switch.wireless_enabled = 'wireless_enabled' in request.form
            
            if request.form.get('wireless_standard'):
                router_switch.wireless_standard = request.form.get('wireless_standard')
            if request.form.get('wireless_channels'):
                router_switch.wireless_channels = request.form.get('wireless_channels')
            
            db.session.commit()
            flash('Router switch updated successfully!', 'success')
            return redirect(url_for('web.router_switch_detail', router_switch_id=router_switch.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating router switch: {str(e)}', 'error')
    
    clusters = Cluster.query.all()
    return render_template('edit_router_switch.html', router_switch=router_switch, clusters=clusters)

@bp.route('/router-switches/<int:router_switch_id>/delete', methods=['POST'])
@login_required
def delete_router_switch(router_switch_id):
    """Delete a router switch."""
    router_switch = RouterSwitch.query.get_or_404(router_switch_id)
    
    try:
        # Delete associated operations first
        Operation.query.filter_by(router_switch_id=router_switch_id).delete()
        
        # Delete the router switch
        db.session.delete(router_switch)
        db.session.commit()
        flash(f'Router switch "{router_switch.hostname}" deleted successfully!', 'success')
        return redirect(url_for('web.router_switches'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting router switch: {str(e)}', 'error')
        return redirect(url_for('web.router_switch_detail', router_switch_id=router_switch.id))

# Network Lease routes
@bp.route('/network-leases')
@login_required
def network_leases():
    """Network leases management page."""
    # Get filter parameters
    router_switch_id = request.args.get('router_switch_id', type=int)
    status = request.args.get('status')
    is_cluster_node = request.args.get('is_cluster_node')
    
    query = NetworkLease.query
    
    # Apply filters
    if router_switch_id:
        query = query.filter(NetworkLease.router_switch_id == router_switch_id)
    if status:
        query = query.filter(NetworkLease.status == status)
    if is_cluster_node:
        if is_cluster_node.lower() in ('true', '1', 'yes'):
            query = query.filter(NetworkLease.node_id.isnot(None))
        else:
            query = query.filter(NetworkLease.node_id.is_(None))
    
    leases = query.order_by(NetworkLease.last_activity.desc()).all()
    router_switches = RouterSwitch.query.all()
    
    # Get statistics
    stats = {
        'total_leases': len(leases),
        'active_leases': len([l for l in leases if l.is_active]),
        'cluster_node_leases': len([l for l in leases if l.is_cluster_node]),
        'expired_leases': len([l for l in leases if l.is_expired])
    }
    
    return render_template('network_leases.html', 
                         leases=leases, 
                         router_switches=router_switches,
                         stats=stats,
                         current_filters={
                             'router_switch_id': router_switch_id,
                             'status': status,
                             'is_cluster_node': is_cluster_node
                         })

@bp.route('/network-leases/<int:lease_id>')
@login_required
def network_lease_detail(lease_id):
    """Network lease detail page."""
    lease = NetworkLease.query.get_or_404(lease_id)
    return render_template('network_lease_detail.html', lease=lease)

@bp.route('/network-interfaces')
@login_required
def network_interfaces():
    """Network interfaces management page."""
    router_switch_id = request.args.get('router_switch_id', type=int)
    interface_type = request.args.get('interface_type')
    
    query = NetworkInterface.query
    
    if router_switch_id:
        query = query.filter(NetworkInterface.router_switch_id == router_switch_id)
    if interface_type:
        query = query.filter(NetworkInterface.interface_type == interface_type)
    
    interfaces = query.order_by(NetworkInterface.name).all()
    router_switches = RouterSwitch.query.all()
    
    # Get statistics
    stats = {
        'total_interfaces': len(interfaces),
        'up_interfaces': len([i for i in interfaces if i.status == 'up']),
        'down_interfaces': len([i for i in interfaces if i.status == 'down']),
        'dhcp_enabled_interfaces': len([i for i in interfaces if i.dhcp_server_enabled])
    }
    
    return render_template('network_interfaces.html', 
                         interfaces=interfaces, 
                         router_switches=router_switches,
                         stats=stats,
                         current_filters={
                             'router_switch_id': router_switch_id,
                             'interface_type': interface_type
                         })

@bp.route('/network-interfaces/<int:interface_id>')
@login_required
def network_interface_detail(interface_id):
    """Network interface detail page."""
    interface = NetworkInterface.query.get_or_404(interface_id)
    return render_template('network_interface_detail.html', interface=interface)

@bp.route('/network/topology')
@login_required
def network_topology():
    """Network topology visualization page."""
    # Get all active leases with relationships
    leases = NetworkLease.query.filter(NetworkLease.is_active == True).all()
    
    # Get all router switches
    router_switches = RouterSwitch.query.all()
    
    # Get all cluster nodes
    nodes = Node.query.all()
    
    # Get all clusters
    clusters = Cluster.query.all()
    
    # Build topology data for visualization
    topology_data = {
        'nodes': [],
        'edges': []
    }
    
    # Add router switches as nodes
    for rs in router_switches:
        topology_data['nodes'].append({
            'id': f'router_{rs.id}',
            'label': rs.hostname,
            'type': 'router',
            'group': 'routers',
            'data': {
                'ip_address': rs.ip_address,
                'device_type': rs.device_type,
                'model': rs.model,
                'status': rs.status,
                'health_score': rs.health_score
            }
        })
    
    # Add cluster nodes
    for node in nodes:
        topology_data['nodes'].append({
            'id': f'node_{node.id}',
            'label': node.hostname,
            'type': 'cluster_node',
            'group': f'cluster_{node.cluster_id}' if node.cluster_id else 'unassigned',
            'data': {
                'ip_address': node.ip_address,
                'status': node.status,
                'microk8s_status': node.microk8s_status,
                'is_control_plane': node.is_control_plane
            }
        })
    
    # Add connections based on leases
    for lease in leases:
        if lease.node_id:
            topology_data['edges'].append({
                'from': f'router_{lease.router_switch_id}',
                'to': f'node_{lease.node_id}',
                'label': lease.ip_address,
                'data': {
                    'mac_address': lease.mac_address,
                    'hostname': lease.hostname,
                    'lease_remaining': lease.time_remaining,
                    'connection_type': 'dhcp_lease'
                }
            })
    
    return render_template('network_topology.html', 
                         topology_data=topology_data,
                         leases=leases,
                         router_switches=router_switches,
                         nodes=nodes,
                         clusters=clusters)

@bp.route('/hardware-report')
@login_required
def hardware_report():
    """Hardware report for all nodes."""
    nodes = Node.query.all()
    clusters = Cluster.query.all()
    
    # Calculate summary statistics
    total_cpu_cores = sum(node.cpu_cores or 0 for node in nodes)
    total_memory_gb = sum(node.memory_gb or 0 for node in nodes)
    total_disk_gb = sum(node.disk_gb or 0 for node in nodes)
    
    # Calculate averages for nodes with data (with defensive programming for missing attributes)
    nodes_with_cpu_usage = [n for n in nodes if hasattr(n, 'cpu_usage_percent') and n.cpu_usage_percent is not None]
    nodes_with_memory_usage = [n for n in nodes if hasattr(n, 'memory_usage_percent') and n.memory_usage_percent is not None]
    nodes_with_disk_usage = [n for n in nodes if hasattr(n, 'disk_usage_percent') and n.disk_usage_percent is not None]
    
    avg_cpu_usage = sum(n.cpu_usage_percent for n in nodes_with_cpu_usage) / len(nodes_with_cpu_usage) if nodes_with_cpu_usage else 0
    avg_memory_usage = sum(n.memory_usage_percent for n in nodes_with_memory_usage) / len(nodes_with_memory_usage) if nodes_with_memory_usage else 0
    avg_disk_usage = sum(n.disk_usage_percent for n in nodes_with_disk_usage) / len(nodes_with_disk_usage) if nodes_with_disk_usage else 0
    
    # Count nodes with GPU
    nodes_with_gpu = len([n for n in nodes if hasattr(n, 'gpu_info') and n.gpu_info and 'present": true' in n.gpu_info.lower()])
    
    # Count nodes with thermal sensors
    nodes_with_thermal = len([n for n in nodes if hasattr(n, 'thermal_info') and n.thermal_info and 'sensors_available": true' in n.thermal_info.lower()])
    
    summary = {
        'total_nodes': len(nodes),
        'total_cpu_cores': total_cpu_cores,
        'total_memory_gb': total_memory_gb,
        'total_disk_gb': total_disk_gb,
        'avg_cpu_usage': round(avg_cpu_usage, 1),
        'avg_memory_usage': round(avg_memory_usage, 1),
        'avg_disk_usage': round(avg_disk_usage, 1),
        'nodes_with_gpu': nodes_with_gpu,
        'nodes_with_thermal': nodes_with_thermal,
        'nodes_with_usage_data': len(nodes_with_cpu_usage)
    }
    
    return render_template('hardware_report.html', 
                         nodes=nodes, 
                         clusters=clusters,
                         summary=summary)

@bp.route('/hardware-report/cluster/<int:cluster_id>')
@login_required
def cluster_hardware_report(cluster_id):
    """Hardware report for a specific cluster."""
    cluster = Cluster.query.get_or_404(cluster_id)
    nodes = cluster.nodes
    
    # Calculate summary statistics for this cluster
    total_cpu_cores = sum(node.cpu_cores or 0 for node in nodes)
    total_memory_gb = sum(node.memory_gb or 0 for node in nodes)
    total_disk_gb = sum(node.disk_gb or 0 for node in nodes)
    
    # Calculate averages for nodes with data (with defensive programming for missing attributes)
    nodes_with_cpu_usage = [n for n in nodes if hasattr(n, 'cpu_usage_percent') and n.cpu_usage_percent is not None]
    nodes_with_memory_usage = [n for n in nodes if hasattr(n, 'memory_usage_percent') and n.memory_usage_percent is not None]
    nodes_with_disk_usage = [n for n in nodes if hasattr(n, 'disk_usage_percent') and n.disk_usage_percent is not None]
    
    avg_cpu_usage = sum(n.cpu_usage_percent for n in nodes_with_cpu_usage) / len(nodes_with_cpu_usage) if nodes_with_cpu_usage else 0
    avg_memory_usage = sum(n.memory_usage_percent for n in nodes_with_memory_usage) / len(nodes_with_memory_usage) if nodes_with_memory_usage else 0
    avg_disk_usage = sum(n.disk_usage_percent for n in nodes_with_disk_usage) / len(nodes_with_disk_usage) if nodes_with_disk_usage else 0
    
    # Count nodes with GPU
    nodes_with_gpu = len([n for n in nodes if hasattr(n, 'gpu_info') and n.gpu_info and 'present": true' in n.gpu_info.lower()])
    
    # Count nodes with thermal sensors
    nodes_with_thermal = len([n for n in nodes if hasattr(n, 'thermal_info') and n.thermal_info and 'sensors_available": true' in n.thermal_info.lower()])
    
    summary = {
        'total_nodes': len(nodes),
        'total_cpu_cores': total_cpu_cores,
        'total_memory_gb': total_memory_gb,
        'total_disk_gb': total_disk_gb,
        'avg_cpu_usage': round(avg_cpu_usage, 1),
        'avg_memory_usage': round(avg_memory_usage, 1),
        'avg_disk_usage': round(avg_disk_usage, 1),
        'nodes_with_gpu': nodes_with_gpu,
        'nodes_with_thermal': nodes_with_thermal,
        'nodes_with_usage_data': len(nodes_with_cpu_usage)
    }
    
    return render_template('cluster_hardware_report.html', 
                         cluster=cluster,
                         nodes=nodes,
                         summary=summary)

@bp.route('/hardware-report/node/<int:node_id>')
@login_required
def node_hardware_report(node_id):
    """Detailed hardware report for a specific node."""
    node = Node.query.get_or_404(node_id)
    
    # Parse JSON fields for display
    import json
    parsed_info = {}
    
    try:
        if hasattr(node, 'cpu_info') and node.cpu_info:
            parsed_info['cpu'] = json.loads(node.cpu_info)
        else:
            parsed_info['cpu'] = None
    except json.JSONDecodeError:
        parsed_info['cpu'] = None
        
    try:
        if hasattr(node, 'memory_info') and node.memory_info:
            parsed_info['memory'] = json.loads(node.memory_info)
        else:
            parsed_info['memory'] = None
    except json.JSONDecodeError:
        parsed_info['memory'] = None
        
    try:
        if hasattr(node, 'disk_info') and node.disk_info:
            parsed_info['disk'] = json.loads(node.disk_info)
        else:
            parsed_info['disk'] = None
    except json.JSONDecodeError:
        parsed_info['disk'] = None
        
    try:
        if hasattr(node, 'network_info') and node.network_info:
            parsed_info['network'] = json.loads(node.network_info)
        else:
            parsed_info['network'] = None
    except json.JSONDecodeError:
        parsed_info['network'] = None
        
    try:
        if hasattr(node, 'gpu_info') and node.gpu_info:
            parsed_info['gpu'] = json.loads(node.gpu_info)
        else:
            parsed_info['gpu'] = None
    except json.JSONDecodeError:
        parsed_info['gpu'] = None
        
    try:
        if hasattr(node, 'thermal_info') and node.thermal_info:
            parsed_info['thermal'] = json.loads(node.thermal_info)
        else:
            parsed_info['thermal'] = None
    except json.JSONDecodeError:
        parsed_info['thermal'] = None
        
    try:
        if hasattr(node, 'hardware_info') and node.hardware_info:
            parsed_info['hardware'] = json.loads(node.hardware_info)
        else:
            parsed_info['hardware'] = None
    except json.JSONDecodeError:
        parsed_info['hardware'] = None
    
    return render_template('node_hardware_report.html', 
                         node=node,
                         parsed_info=parsed_info)
