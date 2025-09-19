"""Web interface endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models.database import db
from ..models.flask_models import Node, Cluster, Operation, RouterSwitch

bp = Blueprint('web', __name__)

@bp.route('/')
def dashboard():
    """Main dashboard."""
    clusters = Cluster.query.all()
    nodes = Node.query.all()
    router_switches = RouterSwitch.query.all()
    recent_operations = Operation.query.order_by(Operation.created_at.desc()).limit(10).all()
    
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
def nodes():
    """Nodes management page."""
    nodes = Node.query.all()
    return render_template('nodes.html', nodes=nodes)

@bp.route('/nodes/add', methods=['GET', 'POST'])
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
def clusters():
    """Clusters management page."""
    clusters = Cluster.query.all()
    return render_template('clusters.html', clusters=clusters)

@bp.route('/clusters/add', methods=['GET', 'POST'])
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
def operations():
    """Operations history page."""
    operations = Operation.query.order_by(Operation.created_at.desc()).all()
    return render_template('operations.html', operations=operations)

@bp.route('/operations/<int:operation_id>')
def operation_detail(operation_id):
    """Operation detail page."""
    operation = Operation.query.get_or_404(operation_id)
    return render_template('operation_detail.html', operation=operation)

# Router/Switch routes
@bp.route('/router-switches')
def router_switches():
    """Router switches management page."""
    router_switches = RouterSwitch.query.all()
    return render_template('router_switches.html', router_switches=router_switches)

@bp.route('/router-switches/add', methods=['GET', 'POST'])
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
def router_switch_detail(router_switch_id):
    """Router switch detail page."""
    router_switch = RouterSwitch.query.get_or_404(router_switch_id)
    operations = Operation.query.filter_by(router_switch_id=router_switch_id).order_by(Operation.created_at.desc()).limit(10).all()
    return render_template('router_switch_detail.html', router_switch=router_switch, operations=operations)
