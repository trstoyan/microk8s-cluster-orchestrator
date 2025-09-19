"""Operation model for tracking cluster operations and tasks."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base, db

class Operation(Base if not hasattr(db, 'Model') else db.Model):
    """Represents an operation performed on nodes or clusters."""
    
    __tablename__ = 'operations'
    
    id = Column(Integer, primary_key=True)
    operation_type = Column(String(100), nullable=False)  # install, configure, troubleshoot, update, etc.
    operation_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Operation details
    playbook_path = Column(String(500))
    ansible_extra_vars = Column(Text)  # JSON string
    
    # Status tracking
    status = Column(String(50), default='pending')  # pending, running, completed, failed, cancelled
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    success = Column(Boolean, default=False)
    output = Column(Text)  # Ansible output or logs
    error_message = Column(Text)
    
    # Relationships
    node_id = Column(Integer, ForeignKey('nodes.id'))
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    node = relationship("Node", back_populates="operations")
    cluster = relationship("Cluster", back_populates="operations")
    
    # Metadata
    created_by = Column(String(100), default='system')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        target = f"Node {self.node.hostname}" if self.node else f"Cluster {self.cluster.name}"
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
