"""Web interface endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models.database import db
from ..models.node import Node
from ..models.cluster import Cluster
from ..models.operation import Operation

bp = Blueprint('web', __name__)

@bp.route('/')
def dashboard():
    """Main dashboard."""
    clusters = Cluster.query.all()
    nodes = Node.query.all()
    recent_operations = Operation.query.order_by(Operation.created_at.desc()).limit(10).all()
    
    stats = {
        'total_clusters': len(clusters),
        'total_nodes': len(nodes),
        'online_nodes': len([n for n in nodes if n.status == 'online']),
        'recent_operations': len(recent_operations)
    }
    
    return render_template('dashboard.html', 
                         clusters=clusters, 
                         nodes=nodes, 
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
