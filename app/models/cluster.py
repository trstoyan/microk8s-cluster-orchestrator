"""Cluster model for representing MicroK8s clusters."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base, db

class Cluster(Base):
    """Represents a MicroK8s cluster."""
    
    __tablename__ = 'clusters'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    
    # Cluster configuration
    ha_enabled = Column(Boolean, default=False)
    addons = Column(Text)  # JSON string of enabled addons
    network_cidr = Column(String(50), default='10.1.0.0/16')
    service_cidr = Column(String(50), default='10.152.183.0/24')
    
    # Status
    status = Column(String(50), default='initializing')  # initializing, active, degraded, offline, error
    health_score = Column(Integer, default=0)  # 0-100
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nodes = relationship("Node", backref="cluster")
    operations = relationship("Operation", back_populates="cluster")
    ups_rules = relationship("UPSClusterRule", back_populates="cluster")
    
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
