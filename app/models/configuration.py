"""Configuration model for storing system and cluster configurations."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from .database import db

class Configuration(db.Model):
    """Represents configuration settings for the orchestrator and clusters."""
    
    __tablename__ = 'configurations'
    
    id = Column(Integer, primary_key=True)
    config_type = Column(String(100), nullable=False)  # system, cluster, node, ansible
    config_name = Column(String(255), nullable=False)
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text)
    
    # Configuration metadata
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)  # For passwords, keys, etc.
    is_active = Column(Boolean, default=True)
    
    # Scope (optional)
    scope_type = Column(String(50))  # global, cluster, node
    scope_id = Column(Integer)  # ID of the scoped entity
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Configuration {self.config_type}:{self.config_name}:{self.config_key}>'
    
    def to_dict(self, include_sensitive=False):
        """Convert configuration to dictionary representation."""
        value = self.config_value
        if self.is_sensitive and not include_sensitive:
            value = '***REDACTED***'
            
        return {
            'id': self.id,
            'config_type': self.config_type,
            'config_name': self.config_name,
            'config_key': self.config_key,
            'config_value': value,
            'description': self.description,
            'is_sensitive': self.is_sensitive,
            'is_active': self.is_active,
            'scope_type': self.scope_type,
            'scope_id': self.scope_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
