"""Web interface endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch, User
from ..models.network_lease import NetworkLease, NetworkInterface

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
            # Create the node first
            node = Node(
                hostname=request.form['hostname'],
                ip_address=request.form['ip_address'],
                ssh_user=request.form.get('ssh_user', 'ubuntu'),
                ssh_port=int(request.form.get('ssh_port', 22)),
                cluster_id=request.form.get('cluster_id') or None,
                notes=request.form.get('notes')
            )
            db.session.add(node)
            db.session.flush()  # Get the node ID
            
            # Generate SSH key pair
            from ..services.ssh_key_manager import SSHKeyManager
            ssh_manager = SSHKeyManager()
            
            try:
                key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
                
                # Update node with SSH key information
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
                
                flash(f'Node "{node.hostname}" added successfully! SSH key generated. Please follow the setup instructions.', 'success')
                return redirect(url_for('web.node_ssh_setup', node_id=node.id))
                
            except Exception as key_error:
                db.session.rollback()
                flash(f'Error generating SSH key: {str(key_error)}', 'error')
                return redirect(url_for('web.add_node'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding node: {str(e)}', 'error')
    
    clusters = Cluster.query.all()
    return render_template('add_node.html', clusters=clusters)

@bp.route('/nodes/<int:node_id>/ssh-setup')
@login_required
def node_ssh_setup(node_id):
    """SSH key setup page for a node."""
    node = Node.query.get_or_404(node_id)
    
    # Handle cases where SSH key fields might not exist (backward compatibility)
    ssh_key_generated = getattr(node, 'ssh_key_generated', False)
    
    if not ssh_key_generated:
        flash('SSH key not generated for this node.', 'error')
        return redirect(url_for('web.nodes'))
    
    return render_template('node_ssh_setup.html', node=node)

@bp.route('/nodes/<int:node_id>/test-ssh', methods=['POST'])
@login_required
def test_ssh_connection(node_id):
    """Test SSH connection to a node."""
    node = Node.query.get_or_404(node_id)
    
    if not node.ssh_key_ready:
        flash('SSH key not ready for testing.', 'error')
        return redirect(url_for('web.node_ssh_setup', node_id=node.id))
    
    try:
        from ..services.ssh_key_manager import SSHKeyManager
        import json
        
        ssh_manager = SSHKeyManager()
        test_result = ssh_manager.validate_ssh_connection(
            node.hostname,
            node.ip_address,
            node.ssh_user,
            node.ssh_port,
            node.ssh_key_path
        )
        
        # Update node with test results
        node.ssh_connection_tested = True
        node.ssh_connection_test_result = json.dumps(test_result)
        
        if test_result['success']:
            node.ssh_key_status = 'tested'
            flash('SSH connection test successful! Node is ready for cluster operations.', 'success')
        else:
            node.ssh_key_status = 'failed'
            flash(f'SSH connection test failed: {test_result.get("message", "Unknown error")}', 'error')
        
        db.session.commit()
        
    except Exception as e:
        flash(f'Error testing SSH connection: {str(e)}', 'error')
    
    return redirect(url_for('web.node_ssh_setup', node_id=node.id))

@bp.route('/nodes/<int:node_id>/regenerate-ssh-key', methods=['POST'])
@login_required
def regenerate_ssh_key(node_id):
    """Regenerate SSH key for a node."""
    node = Node.query.get_or_404(node_id)
    
    try:
        from ..services.ssh_key_manager import SSHKeyManager
        
        # Clean up existing key if it exists
        if node.ssh_key_path:
            ssh_manager = SSHKeyManager()
            ssh_manager.cleanup_key_pair(node.ssh_key_path)
        
        # Generate new key pair
        ssh_manager = SSHKeyManager()
        key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
        
        # Update node with new SSH key information
        node.ssh_key_path = key_info['private_key_path']
        node.ssh_public_key = key_info['public_key']
        node.ssh_key_fingerprint = key_info['fingerprint']
        node.ssh_key_generated = True
        node.ssh_key_status = 'generated'
        node.ssh_connection_tested = False
        node.ssh_connection_test_result = None
        
        # Generate new setup instructions
        instructions = ssh_manager.get_setup_instructions(
            node.hostname, 
            key_info['public_key'],
            node.ssh_user
        )
        node.ssh_setup_instructions = instructions
        
        db.session.commit()
        
        flash('SSH key regenerated successfully! Please follow the new setup instructions.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error regenerating SSH key: {str(e)}', 'error')
    
    return redirect(url_for('web.node_ssh_setup', node_id=node.id))

@bp.route('/api/nodes/<int:node_id>/check-ssh-keys', methods=['POST'])
@login_required
def api_check_ssh_keys(node_id):
    """API endpoint to check SSH key status and file existence."""
    from flask import jsonify
    node = Node.query.get_or_404(node_id)
    
    try:
        from ..services.ssh_key_manager import SSHKeyManager
        from pathlib import Path
        
        ssh_manager = SSHKeyManager()
        
        # Check if key files exist
        key_files_exist = False
        key_path = None
        fingerprint = None
        sync_needed = False
        available_keys = []
        
        # First, scan for all available SSH keys
        ssh_keys_dir = Path('ssh_keys')
        if ssh_keys_dir.exists():
            for key_file in ssh_keys_dir.glob('*'):
                if not key_file.name.endswith('.pub') and not key_file.name.startswith('.'):
                    pub_key_file = key_file.with_suffix('.pub')
                    if pub_key_file.exists():
                        try:
                            with open(pub_key_file, 'r') as f:
                                public_key = f.read().strip()
                            
                            # Get key info
                            key_info = ssh_manager.get_key_info(str(key_file))
                            if key_info:
                                available_keys.append({
                                    'name': key_file.name,
                                    'path': str(key_file.absolute()),
                                    'public_key': public_key,
                                    'fingerprint': key_info['fingerprint'],
                                    'size': key_file.stat().st_size,
                                    'is_current': str(key_file.absolute()) == node.ssh_key_path
                                })
                        except Exception as e:
                            print(f"Error reading key {key_file}: {e}")
        
        # Check current key path
        if node.ssh_key_path:
            key_path = Path(node.ssh_key_path)
            public_key_path = key_path.with_suffix('.pub')
            
            if key_path.exists() and public_key_path.exists():
                key_files_exist = True
                
                # Get key info if files exist
                key_info = ssh_manager.get_key_info(str(key_path))
                if key_info:
                    fingerprint = key_info['fingerprint']
                    
                    # Check if database is in sync with files
                    db_has_key = getattr(node, 'ssh_key_generated', False)
                    if not db_has_key:
                        sync_needed = True
                        
                        # Auto-sync if needed
                        try:
                            node.ssh_key_generated = True
                            node.ssh_key_status = 'generated'
                            node.ssh_public_key = key_info['public_key']
                            node.ssh_key_fingerprint = key_info['fingerprint']
                            
                            # Generate setup instructions
                            instructions = ssh_manager.get_setup_instructions(
                                node.hostname, 
                                key_info['public_key'],
                                node.ssh_user
                            )
                            node.ssh_setup_instructions = instructions
                            
                            db.session.commit()
                            
                        except Exception as sync_error:
                            db.session.rollback()
                            return jsonify({
                                'success': False,
                                'error': f'Failed to sync database: {str(sync_error)}'
                            })
        
        # Get database status
        db_status = getattr(node, 'ssh_key_status', 'not_generated')
        if getattr(node, 'ssh_key_generated', False):
            db_status = f"Generated ({db_status})"
        else:
            db_status = "Not Generated"
        
        return jsonify({
            'success': True,
            'key_files_exist': key_files_exist,
            'database_status': db_status,
            'fingerprint': fingerprint,
            'key_path': str(key_path) if key_path else None,
            'sync_needed': sync_needed,
            'sync_performed': sync_needed,
            'available_keys': available_keys
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/api/nodes/<int:node_id>/select-ssh-key', methods=['POST'])
@login_required
def api_select_ssh_key(node_id):
    """API endpoint to select a different SSH key for a node."""
    from flask import jsonify
    node = Node.query.get_or_404(node_id)
    
    try:
        data = request.get_json()
        key_path = data.get('key_path')
        
        if not key_path:
            return jsonify({
                'success': False,
                'error': 'Key path is required'
            })
        
        from ..services.ssh_key_manager import SSHKeyManager
        from pathlib import Path
        
        ssh_manager = SSHKeyManager()
        key_file = Path(key_path)
        
        if not key_file.exists():
            return jsonify({
                'success': False,
                'error': 'Key file does not exist'
            })
        
        # Get key info
        key_info = ssh_manager.get_key_info(str(key_file))
        if not key_info:
            return jsonify({
                'success': False,
                'error': 'Failed to read key information'
            })
        
        # Update node with new key
        node.ssh_key_path = str(key_file.absolute())
        node.ssh_key_generated = True
        node.ssh_key_status = 'generated'
        node.ssh_public_key = key_info['public_key']
        node.ssh_key_fingerprint = key_info['fingerprint']
        
        # Generate setup instructions
        instructions = ssh_manager.get_setup_instructions(
            node.hostname, 
            key_info['public_key'],
            node.ssh_user
        )
        node.ssh_setup_instructions = instructions
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'SSH key updated to {key_file.name}',
            'key_info': {
                'name': key_file.name,
                'fingerprint': key_info['fingerprint'],
                'public_key': key_info['public_key']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/api/nodes/<int:node_id>/regenerate-ssh-key', methods=['POST'])
@login_required
def api_regenerate_ssh_key(node_id):
    """API endpoint to regenerate SSH key for a node."""
    from flask import jsonify
    node = Node.query.get_or_404(node_id)
    
    try:
        from ..services.ssh_key_manager import SSHKeyManager
        
        # Clean up existing key if it exists
        if node.ssh_key_path:
            ssh_manager = SSHKeyManager()
            ssh_manager.cleanup_key_pair(node.ssh_key_path)
        
        # Generate new key pair
        ssh_manager = SSHKeyManager()
        key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
        
        # Update node with new SSH key information
        node.ssh_key_path = key_info['private_key_path']
        node.ssh_public_key = key_info['public_key']
        node.ssh_key_fingerprint = key_info['fingerprint']
        node.ssh_key_generated = True
        node.ssh_key_status = 'generated'
        node.ssh_connection_tested = False
        node.ssh_connection_test_result = None
        
        # Generate new setup instructions
        instructions = ssh_manager.get_setup_instructions(
            node.hostname, 
            key_info['public_key'],
            node.ssh_user
        )
        node.ssh_setup_instructions = instructions
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'SSH key regenerated successfully',
            'fingerprint': key_info['fingerprint']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/api/system/health', methods=['GET'])
@login_required
def api_system_health():
    """API endpoint to check system health."""
    from flask import jsonify
    
    try:
        from ..utils.migration_manager import MigrationManager
        
        migration_manager = MigrationManager()
        health_check = migration_manager.run_comprehensive_check()
        
        return jsonify({
            'overall_healthy': health_check['overall_healthy'],
            'migration_status': health_check['migration_status'],
            'model_validation': health_check['model_validation'],
            'recommendations': health_check['recommendations']
        })
        
    except Exception as e:
        return jsonify({
            'overall_healthy': False,
            'error': str(e)
        })

@bp.route('/nodes/<int:node_id>')
@login_required
def node_detail(node_id):
    """Node detail page."""
    node = Node.query.get_or_404(node_id)
    
    # Get recent operations for this node
    recent_operations = Operation.query.filter_by(node_id=node_id).order_by(Operation.created_at.desc()).limit(10).all()
    
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
        if hasattr(node, 'hardware_info') and node.hardware_info:
            parsed_info['hardware'] = json.loads(node.hardware_info)
        else:
            parsed_info['hardware'] = None
    except json.JSONDecodeError:
        parsed_info['hardware'] = None
    
    # Calculate node statistics
    stats = {
        'total_operations': len(recent_operations),
        'successful_operations': len([op for op in recent_operations if op.success]),
        'failed_operations': len([op for op in recent_operations if not op.success]),
        'wol_configured': node.wol_configured,
        'ssh_ready': node.ssh_connection_ready,
        'microk8s_ready': node.microk8s_status == 'running'
    }
    
    return render_template('node_detail.html', 
                         node=node, 
                         recent_operations=recent_operations,
                         parsed_info=parsed_info,
                         stats=stats)

@bp.route('/clusters')
@login_required
def clusters():
    """Clusters management page."""
    clusters = Cluster.query.all()
    return render_template('clusters.html', clusters=clusters)

@bp.route('/clusters/<int:cluster_id>')
@login_required
def cluster_detail(cluster_id):
    """Cluster detail page."""
    cluster = Cluster.query.get_or_404(cluster_id)
    
    # Get cluster nodes
    nodes = Node.query.filter_by(cluster_id=cluster_id).all()
    
    # Get recent operations for this cluster
    recent_operations = Operation.query.filter_by(cluster_id=cluster_id).order_by(Operation.created_at.desc()).limit(10).all()
    
    # Get UPS rules for this cluster
    from ..models.ups_cluster_rule import UPSClusterRule
    ups_rules = UPSClusterRule.query.filter_by(cluster_id=cluster_id).all()
    
    # Calculate cluster statistics
    stats = {
        'total_nodes': len(nodes),
        'online_nodes': len([n for n in nodes if n.status == 'online']),
        'offline_nodes': len([n for n in nodes if n.status == 'offline']),
        'control_plane_nodes': len([n for n in nodes if n.is_control_plane]),
        'worker_nodes': len([n for n in nodes if not n.is_control_plane]),
        'wol_configured_nodes': len([n for n in nodes if n.wol_configured]),
        'virtual_nodes': len([n for n in nodes if n.is_virtual_node]),
        'recent_operations': len(recent_operations),
        'ups_rules': len(ups_rules)
    }
    
    return render_template('cluster_detail.html', 
                         cluster=cluster, 
                         nodes=nodes, 
                         recent_operations=recent_operations,
                         ups_rules=ups_rules,
                         stats=stats)

@bp.route('/clusters/<int:cluster_id>/configure-hosts', methods=['POST'])
@login_required
def configure_cluster_hosts(cluster_id):
    """Configure /etc/hosts file for cluster nodes."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        
        if not cluster.nodes:
            flash('Cluster has no nodes assigned.', 'error')
            return redirect(url_for('web.cluster_detail', cluster_id=cluster_id))
        
        from ..services.orchestrator import OrchestrationService
        orchestrator = OrchestrationService()
        
        operation = orchestrator.configure_hosts_file(cluster)
        # Set the user who initiated the operation
        operation.user_id = current_user.id
        operation.created_by = current_user.full_name
        db.session.commit()
        
        flash(f'Hosts file configuration started for cluster "{cluster.name}". Operation ID: {operation.id}', 'success')
        return redirect(url_for('web.cluster_detail', cluster_id=cluster_id))
        
    except Exception as e:
        flash(f'Error configuring hosts file: {str(e)}', 'error')
        return redirect(url_for('web.cluster_detail', cluster_id=cluster_id))

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
    
    avg_cpu_usage = sum(int(n.cpu_usage_percent) for n in nodes_with_cpu_usage if str(n.cpu_usage_percent).isdigit()) / len(nodes_with_cpu_usage) if nodes_with_cpu_usage else 0
    avg_memory_usage = sum(int(n.memory_usage_percent) for n in nodes_with_memory_usage if str(n.memory_usage_percent).isdigit()) / len(nodes_with_memory_usage) if nodes_with_memory_usage else 0
    avg_disk_usage = sum(int(n.disk_usage_percent) for n in nodes_with_disk_usage if str(n.disk_usage_percent).isdigit()) / len(nodes_with_disk_usage) if nodes_with_disk_usage else 0
    
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
    
    avg_cpu_usage = sum(int(n.cpu_usage_percent) for n in nodes_with_cpu_usage if str(n.cpu_usage_percent).isdigit()) / len(nodes_with_cpu_usage) if nodes_with_cpu_usage else 0
    avg_memory_usage = sum(int(n.memory_usage_percent) for n in nodes_with_memory_usage if str(n.memory_usage_percent).isdigit()) / len(nodes_with_memory_usage) if nodes_with_memory_usage else 0
    avg_disk_usage = sum(int(n.disk_usage_percent) for n in nodes_with_disk_usage if str(n.disk_usage_percent).isdigit()) / len(nodes_with_disk_usage) if nodes_with_disk_usage else 0
    
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
        # Direct database query to get the new fields
        from app.models.database import db
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT disk_partitions_info, storage_volumes_info FROM nodes WHERE id = :node_id"),
            {'node_id': node.id}
        ).fetchone()
        
        if result and result[0]:  # disk_partitions_info
            parsed_info['disk_partitions'] = json.loads(result[0])
        else:
            parsed_info['disk_partitions'] = None
            
        if result and result[1]:  # storage_volumes_info
            parsed_info['storage_volumes'] = json.loads(result[1])
        else:
            parsed_info['storage_volumes'] = None
            
    except json.JSONDecodeError as e:
        parsed_info['disk_partitions'] = None
        parsed_info['storage_volumes'] = None
        print(f"DEBUG: JSON decode error: {e}")
    except Exception as e:
        parsed_info['disk_partitions'] = None
        parsed_info['storage_volumes'] = None
    
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

# =============================================================================
# UPS Management Web Routes
# =============================================================================

@bp.route('/ups')
@login_required
def ups_list():
    """UPS management page."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    ups_devices = controller.get_all_ups()
    return render_template('ups_list.html', ups_devices=ups_devices)

@bp.route('/ups/<int:ups_id>')
@login_required
def ups_detail(ups_id):
    """UPS detail page."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    ups_device = controller.get_ups_by_id(ups_id)
    if not ups_device:
        flash('UPS not found', 'error')
        return redirect(url_for('web.ups_list'))
    
    status_info = controller.get_ups_status(ups_id)
    rules = controller.get_power_rules(ups_id=ups_id)
    
    return render_template('ups_detail.html', 
                         ups=ups_device,
                         status_info=status_info,
                         rules=rules)

@bp.route('/ups/scan', methods=['POST'])
@login_required
def ups_scan():
    """Scan for UPS devices."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        ups_devices = controller.scan_and_configure_ups()
        if ups_devices:
            flash(f'Found and configured {len(ups_devices)} UPS device(s)', 'success')
        else:
            flash('No UPS devices found', 'warning')
    except Exception as e:
        flash(f'Error scanning for UPS devices: {e}', 'error')
    
    return redirect(url_for('web.ups_list'))

@bp.route('/ups/<int:ups_id>/test', methods=['POST'])
@login_required
def ups_test(ups_id):
    """Test UPS connection."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.test_ups_connection(ups_id)
        if result['success']:
            flash('UPS connection test passed', 'success')
        else:
            flash(f'UPS connection test failed: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error testing UPS connection: {e}', 'error')
    
    return redirect(url_for('web.ups_detail', ups_id=ups_id))

@bp.route('/ups/<int:ups_id>/remove', methods=['POST'])
@login_required
def ups_remove(ups_id):
    """Remove UPS configuration."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.remove_ups(ups_id)
        if result['success']:
            flash('UPS configuration removed successfully', 'success')
        else:
            flash(f'Failed to remove UPS: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error removing UPS: {e}', 'error')
    
    return redirect(url_for('web.ups_list'))

@bp.route('/ups/rules')
@login_required
def ups_rules():
    """Power management rules page."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    rules = controller.get_power_rules()
    clusters = Cluster.query.all()
    ups_devices = controller.get_all_ups()
    
    return render_template('ups_rules.html', 
                         rules=rules,
                         clusters=clusters,
                         ups_devices=ups_devices)

@bp.route('/ups/rules/create', methods=['GET', 'POST'])
@login_required
def ups_rule_create():
    """Create power management rule."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    if request.method == 'POST':
        try:
            result = controller.create_power_rule(
                ups_id=int(request.form['ups_id']),
                cluster_id=int(request.form['cluster_id']),
                power_event=request.form['power_event'],
                cluster_action=request.form['cluster_action'],
                name=request.form.get('name'),
                description=request.form.get('description'),
                battery_threshold=float(request.form['battery_threshold']) if request.form.get('battery_threshold') else None,
                action_delay=int(request.form.get('action_delay', 0)),
                priority=int(request.form.get('priority', 100)),
                enabled=request.form.get('enabled') == 'on'
            )
            
            if result['success']:
                flash('Power management rule created successfully', 'success')
                return redirect(url_for('web.ups_rules'))
            else:
                flash(f'Failed to create rule: {result.get("error", "Unknown error")}', 'error')
        except Exception as e:
            flash(f'Error creating rule: {e}', 'error')
    
    clusters = Cluster.query.all()
    ups_devices = controller.get_all_ups()
    power_events = controller.get_power_events()
    cluster_actions = controller.get_cluster_actions()
    
    return render_template('ups_rule_create.html',
                         clusters=clusters,
                         ups_devices=ups_devices,
                         power_events=power_events,
                         cluster_actions=cluster_actions)

@bp.route('/ups/rules/<int:rule_id>/delete', methods=['POST'])
@login_required
def ups_rule_delete(rule_id):
    """Delete power management rule."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.delete_power_rule(rule_id)
        if result['success']:
            flash('Power management rule deleted successfully', 'success')
        else:
            flash(f'Failed to delete rule: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error deleting rule: {e}', 'error')
    
    return redirect(url_for('web.ups_rules'))

@bp.route('/ups/monitor')
@login_required
def ups_monitor():
    """Power monitoring page."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    monitoring_status = controller.get_power_monitoring_status()
    nut_services = controller.get_nut_service_status()
    
    return render_template('ups_monitor.html',
                         monitoring_status=monitoring_status,
                         nut_services=nut_services)

@bp.route('/ups/monitor/start', methods=['POST'])
@login_required
def ups_monitor_start():
    """Start power monitoring."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.start_power_monitoring()
        if result['success']:
            flash('Power monitoring started', 'success')
        else:
            flash(f'Failed to start monitoring: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error starting monitoring: {e}', 'error')
    
    return redirect(url_for('web.ups_monitor'))

@bp.route('/ups/monitor/stop', methods=['POST'])
@login_required
def ups_monitor_stop():
    """Stop power monitoring."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.stop_power_monitoring()
        if result['success']:
            flash('Power monitoring stopped', 'success')
        else:
            flash(f'Failed to stop monitoring: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error stopping monitoring: {e}', 'error')
    
    return redirect(url_for('web.ups_monitor'))

@bp.route('/ups/services/restart', methods=['POST'])
@login_required
def ups_services_restart():
    """Restart NUT services."""
    from ..services.ups_controller import UPSController
    controller = UPSController(app=current_app._get_current_object())
    
    try:
        result = controller.restart_nut_services()
        if result['success']:
            flash('NUT services restarted successfully', 'success')
        else:
            flash(f'Failed to restart services: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error restarting services: {e}', 'error')
    
    return redirect(url_for('web.ups_monitor'))

@bp.route('/system')
@login_required
def system_management():
    """System management page."""
    return render_template('system_management.html')

@bp.route('/assistant')
@login_required
def assistant():
    """AI Assistant chat interface."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Check if AI assistant is enabled
    if not ai_config.is_web_interface_enabled():
        flash('AI Assistant is disabled in system configuration', 'warning')
        return redirect(url_for('web.dashboard'))
    
    return render_template('assistant.html')

@bp.route('/api/assistant/chat', methods=['POST'])
@login_required
def assistant_chat():
    """Chat endpoint for AI assistant."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Check if AI assistant is enabled
    if not ai_config.is_ai_assistant_enabled():
        return jsonify({'error': 'AI Assistant is disabled'}), 403
    
    if not ai_config.is_rag_system_enabled():
        return jsonify({'error': 'RAG System is disabled'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Import the local RAG system
        from ..services.local_rag_system import get_local_rag_system
        rag_system = get_local_rag_system()
        
        # Generate response using RAG system
        response = rag_system.generate_response(message)
        
        # Format response for chat interface
        chat_response = {
            'message': message,
            'response': response['response'],
            'confidence': response['confidence'],
            'method': response['method'],
            'context_used': response['context_used'],
            'timestamp': response.get('timestamp', None)
        }
        
        # Store the interaction in the knowledge base if enabled
        if ai_config.should_store_chat_history():
            interaction_metadata = {
                'type': 'chat_interaction',
                'user_id': current_user.id,
                'username': current_user.username,
                'timestamp': response.get('timestamp', None),
                'confidence': response['confidence']
            }
            
            # Anonymize data if configured
            content_to_store = f"User question: {message}\nAssistant response: {response['response'].get('solution', 'N/A')}"
            if ai_config.should_anonymize_data():
                content_to_store = content_to_store.replace(current_user.username, 'user')
            
            rag_system.add_document(content_to_store, interaction_metadata)
        
        return jsonify(chat_response)
        
    except Exception as e:
        current_app.logger.error(f"Assistant chat error: {e}")
        return jsonify({
            'error': 'Failed to process request',
            'message': message,
            'response': {
                'diagnosis': 'System error occurred',
                'solution': 'Please try again or contact support',
                'confidence': 1
            },
            'confidence': 0.1,
            'method': 'error'
        }), 500

@bp.route('/api/assistant/analyze-ansible', methods=['POST'])
@login_required
def analyze_ansible():
    """Analyze Ansible output using AI assistant."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Check if AI assistant and Ansible analysis are enabled
    if not ai_config.is_ai_assistant_enabled():
        return jsonify({'error': 'AI Assistant is disabled'}), 403
    
    if not ai_config.is_ansible_analysis_enabled():
        return jsonify({'error': 'Ansible analysis is disabled'}), 403
    
    try:
        data = request.get_json()
        ansible_output = data.get('output', '').strip()
        playbook_name = data.get('playbook', 'unknown_playbook')
        affected_hosts = data.get('hosts', [])
        
        if not ansible_output:
            return jsonify({'error': 'Ansible output is required'}), 400
        
        # Import the local RAG system
        from ..services.local_rag_system import get_local_rag_system
        rag_system = get_local_rag_system()
        
        # Analyze the Ansible output
        analysis = rag_system.analyze_ansible_output(
            ansible_output,
            playbook_name,
            affected_hosts
        )
        
        return jsonify(analysis)
        
    except Exception as e:
        current_app.logger.error(f"Ansible analysis error: {e}")
        return jsonify({
            'error': 'Failed to analyze Ansible output',
            'success': False,
            'recommendations': ['Check system logs for detailed error information']
        }), 500

@bp.route('/api/assistant/health-insights')
@login_required
def health_insights():
    """Get health insights from AI assistant."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Check if AI assistant and health insights are enabled
    if not ai_config.is_ai_assistant_enabled():
        return jsonify({'error': 'AI Assistant is disabled'}), 403
    
    if not ai_config.is_health_insights_enabled():
        return jsonify({'error': 'Health insights are disabled'}), 403
    
    try:
        # Import the local RAG system
        from ..services.local_rag_system import get_local_rag_system
        rag_system = get_local_rag_system()
        
        # Get health insights
        insights = rag_system.get_health_insights()
        
        return jsonify(insights)
        
    except Exception as e:
        current_app.logger.error(f"Health insights error: {e}")
        return jsonify({
            'error': 'Failed to get health insights',
            'insights': ['Unable to generate insights - check system logs'],
            'confidence': 0.0
        }), 500

@bp.route('/api/assistant/statistics')
@login_required
def assistant_statistics():
    """Get AI assistant statistics."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Check if AI assistant is enabled
    if not ai_config.is_ai_assistant_enabled():
        return jsonify({'error': 'AI Assistant is disabled'}), 403
    
    try:
        # Import the local RAG system
        from ..services.local_rag_system import get_local_rag_system
        rag_system = get_local_rag_system()
        
        # Get statistics
        stats = rag_system.get_statistics()
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Assistant statistics error: {e}")
        return jsonify({
            'error': 'Failed to get statistics',
            'total_documents': 0
        }), 500

@bp.route('/ai-config')
@login_required
def ai_config_management():
    """AI Assistant configuration management page."""
    from ..utils.ai_config import get_ai_config
    ai_config = get_ai_config()
    
    # Get current configuration
    current_config = ai_config.get_full_config()
    
    return render_template('ai_config_management.html', ai_config=current_config)
