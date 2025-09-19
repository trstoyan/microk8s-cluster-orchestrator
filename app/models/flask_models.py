"""Flask-SQLAlchemy models for web interface."""

from datetime import datetime
from .database import db

class Node(db.Model):
    """Flask-SQLAlchemy Node model."""
    
    __tablename__ = 'nodes'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    ssh_user = db.Column(db.String(100), default='ubuntu')
    ssh_port = db.Column(db.Integer, default=22)
    ssh_key_path = db.Column(db.String(500))
    
    # Node status
    status = db.Column(db.String(50), default='unknown')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # MicroK8s specific
    microk8s_version = db.Column(db.String(50))
    microk8s_status = db.Column(db.String(50), default='not_installed')
    is_control_plane = db.Column(db.Boolean, default=False)
    
    # System information
    os_version = db.Column(db.String(100))
    kernel_version = db.Column(db.String(100))
    cpu_cores = db.Column(db.Integer)
    memory_gb = db.Column(db.Integer)
    disk_gb = db.Column(db.Integer)
    
    # Metadata
    tags = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'))
    
    def __repr__(self):
        return f'<Node {self.hostname} ({self.ip_address})>'
    
    def to_dict(self):
        """Convert node to dictionary representation."""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'ssh_user': self.ssh_user,
            'ssh_port': self.ssh_port,
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'microk8s_version': self.microk8s_version,
            'microk8s_status': self.microk8s_status,
            'is_control_plane': self.is_control_plane,
            'os_version': self.os_version,
            'kernel_version': self.kernel_version,
            'cpu_cores': self.cpu_cores,
            'memory_gb': self.memory_gb,
            'disk_gb': self.disk_gb,
            'tags': self.tags,
            'notes': self.notes,
            'cluster_id': self.cluster_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Cluster(db.Model):
    """Flask-SQLAlchemy Cluster model."""
    
    __tablename__ = 'clusters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Cluster configuration
    ha_enabled = db.Column(db.Boolean, default=False)
    addons = db.Column(db.Text)
    network_cidr = db.Column(db.String(50), default='10.1.0.0/16')
    service_cidr = db.Column(db.String(50), default='10.152.183.0/24')
    
    # Status
    status = db.Column(db.String(50), default='initializing')
    health_score = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nodes = db.relationship("Node", backref="cluster")
    
    def __repr__(self):
        return f'<Cluster {self.name}>'
    
    @property
    def node_count(self):
        """Get the number of nodes in this cluster."""
        return len(self.nodes)
    
    @property
    def control_plane_count(self):
        """Get the number of control plane nodes."""
        return len([n for n in self.nodes if n.is_control_plane])
    
    @property
    def worker_count(self):
        """Get the number of worker nodes."""
        return len([n for n in self.nodes if not n.is_control_plane])
    
    def to_dict(self):
        """Convert cluster to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'ha_enabled': self.ha_enabled,
            'addons': self.addons,
            'network_cidr': self.network_cidr,
            'service_cidr': self.service_cidr,
            'status': self.status,
            'health_score': self.health_score,
            'node_count': self.node_count,
            'control_plane_count': self.control_plane_count,
            'worker_count': self.worker_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Operation(db.Model):
    """Flask-SQLAlchemy Operation model."""
    
    __tablename__ = 'operations'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(100), nullable=False)
    operation_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Operation details
    playbook_path = db.Column(db.String(500))
    ansible_extra_vars = db.Column(db.Text)
    
    # Status tracking
    status = db.Column(db.String(50), default='pending')
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Results
    success = db.Column(db.Boolean, default=False)
    output = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    # Relationships
    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'))
    
    # Metadata
    created_by = db.Column(db.String(100), default='system')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        target = f"Node {self.node.hostname}" if self.node else f"Cluster {self.cluster.name}" if self.cluster else "System"
        return f'<Operation {self.operation_name} on {target}>'
    
    @property
    def duration(self):
        """Calculate operation duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self):
        """Convert operation to dictionary representation."""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'operation_name': self.operation_name,
            'description': self.description,
            'playbook_path': self.playbook_path,
            'ansible_extra_vars': self.ansible_extra_vars,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'success': self.success,
            'output': self.output,
            'error_message': self.error_message,
            'node_id': self.node_id,
            'cluster_id': self.cluster_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Configuration(db.Model):
    """Flask-SQLAlchemy Configuration model."""
    
    __tablename__ = 'configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    config_type = db.Column(db.String(100), nullable=False)
    config_name = db.Column(db.String(255), nullable=False)
    config_key = db.Column(db.String(255), nullable=False)
    config_value = db.Column(db.Text)
    
    # Metadata
    is_encrypted = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Configuration {self.config_type}.{self.config_name}.{self.config_key}>'
