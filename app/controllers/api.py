"""API endpoints for the MicroK8s Cluster Orchestrator."""

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from ..models.database import db
from ..models.node import Node
from ..models.cluster import Cluster
from ..models.operation import Operation
from ..services.orchestrator import OrchestrationService

bp = Blueprint('api', __name__)
orchestrator = OrchestrationService()

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'microk8s-orchestrator'})

# Node endpoints
@bp.route('/nodes', methods=['GET'])
def list_nodes():
    """List all nodes."""
    try:
        nodes = Node.query.all()
        return jsonify([node.to_dict() for node in nodes])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/nodes', methods=['POST'])
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
def get_node(node_id):
    """Get a specific node."""
    node = Node.query.get_or_404(node_id)
    return jsonify(node.to_dict())

@bp.route('/nodes/<int:node_id>', methods=['PUT'])
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
def list_clusters():
    """List all clusters."""
    try:
        clusters = Cluster.query.all()
        return jsonify([cluster.to_dict() for cluster in clusters])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/clusters', methods=['POST'])
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
def get_cluster(cluster_id):
    """Get a specific cluster."""
    cluster = Cluster.query.get_or_404(cluster_id)
    return jsonify(cluster.to_dict())

# Operation endpoints
@bp.route('/operations', methods=['GET'])
def list_operations():
    """List all operations."""
    try:
        operations = Operation.query.order_by(Operation.created_at.desc()).all()
        return jsonify([op.to_dict() for op in operations])
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/operations/<int:operation_id>', methods=['GET'])
def get_operation(operation_id):
    """Get a specific operation."""
    operation = Operation.query.get_or_404(operation_id)
    return jsonify(operation.to_dict())

# Orchestration endpoints
@bp.route('/nodes/<int:node_id>/install-microk8s', methods=['POST'])
def install_microk8s(node_id):
    """Install MicroK8s on a node."""
    try:
        node = Node.query.get_or_404(node_id)
        operation = orchestrator.install_microk8s(node)
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
def setup_cluster(cluster_id):
    """Set up a cluster."""
    try:
        cluster = Cluster.query.get_or_404(cluster_id)
        operation = orchestrator.setup_cluster(cluster)
        return jsonify(operation.to_dict()), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500
