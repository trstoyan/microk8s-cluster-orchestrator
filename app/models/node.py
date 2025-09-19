"""Node model for representing cluster nodes."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base, db

class Node(Base if not hasattr(db, 'Model') else db.Model):
    """Represents a single node in the cluster."""
    
    __tablename__ = 'nodes'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    ssh_user = Column(String(100), default='ubuntu')
    ssh_port = Column(Integer, default=22)
    ssh_key_path = Column(String(500))
    
    # Node status
    status = Column(String(50), default='unknown')  # unknown, online, offline, provisioning, error
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # MicroK8s specific
    microk8s_version = Column(String(50))
    microk8s_status = Column(String(50), default='not_installed')  # not_installed, installed, running, stopped, error
    is_control_plane = Column(Boolean, default=False)
    
    # System information
    os_version = Column(String(100))
    kernel_version = Column(String(100))
    cpu_cores = Column(Integer)
    memory_gb = Column(Integer)
    disk_gb = Column(Integer)
    
    # Metadata
    tags = Column(Text)  # JSON string for flexible tagging
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    operations = relationship("Operation", back_populates="node")
    
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
