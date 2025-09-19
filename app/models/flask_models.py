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
    router_switch_id = db.Column(db.Integer, db.ForeignKey('router_switches.id'))
    
    # Metadata
    created_by = db.Column(db.String(100), default='system')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        if self.node:
            target = f"Node {self.node.hostname}"
        elif self.cluster:
            target = f"Cluster {self.cluster.name}"
        elif self.router_switch:
            target = f"RouterSwitch {self.router_switch.hostname}"
        else:
            target = "System"
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
            'router_switch_id': self.router_switch_id,
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

class RouterSwitch(db.Model):
    """Flask-SQLAlchemy RouterSwitch model."""
    
    __tablename__ = 'router_switches'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    management_port = db.Column(db.Integer, default=22)
    
    # Device identification
    device_type = db.Column(db.String(100), default='mikrotik')
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100), unique=True)
    mac_address = db.Column(db.String(17))
    
    # Firmware and software
    firmware_version = db.Column(db.String(50))
    routeros_version = db.Column(db.String(50))
    bootloader_version = db.Column(db.String(50))
    architecture = db.Column(db.String(50))
    
    # Hardware specifications
    cpu_model = db.Column(db.String(100))
    cpu_frequency_mhz = db.Column(db.Integer)
    total_memory_mb = db.Column(db.Integer)
    total_disk_mb = db.Column(db.Integer)
    port_count = db.Column(db.Integer, default=0)
    
    # Network configuration
    management_vlan = db.Column(db.Integer)
    default_gateway = db.Column(db.String(45))
    dns_servers = db.Column(db.Text)
    
    # Device status
    status = db.Column(db.String(50), default='unknown')
    uptime_seconds = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_load_percent = db.Column(db.Float, default=0.0)
    memory_usage_percent = db.Column(db.Float, default=0.0)
    temperature_celsius = db.Column(db.Float)
    
    # Configuration management
    config_backup_enabled = db.Column(db.Boolean, default=True)
    last_config_backup = db.Column(db.DateTime)
    config_backup_path = db.Column(db.String(500))
    auto_update_enabled = db.Column(db.Boolean, default=False)
    
    # VLAN and switching
    vlan_count = db.Column(db.Integer, default=0)
    stp_enabled = db.Column(db.Boolean, default=False)
    lldp_enabled = db.Column(db.Boolean, default=True)
    
    # Wireless (if applicable)
    wireless_enabled = db.Column(db.Boolean, default=False)
    wireless_standard = db.Column(db.String(20))
    wireless_channels = db.Column(db.Text)
    
    # Relationships
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'), nullable=True)
    
    # Metadata
    tags = db.Column(db.Text)
    notes = db.Column(db.Text)
    location = db.Column(db.String(255))
    contact_person = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RouterSwitch {self.hostname} ({self.device_type}:{self.model})>'
    
    @property
    def is_mikrotik(self):
        """Check if this is a MikroTik device."""
        return self.device_type.lower() == 'mikrotik'
    
    @property
    def uptime_days(self):
        """Get uptime in days."""
        return self.uptime_seconds // 86400 if self.uptime_seconds else 0
    
    @property
    def uptime_hours(self):
        """Get uptime in hours."""
        return (self.uptime_seconds % 86400) // 3600 if self.uptime_seconds else 0
    
    @property
    def health_score(self):
        """Calculate device health score based on various factors."""
        score = 100
        
        # Deduct points for high resource usage
        if self.cpu_load_percent > 80:
            score -= 20
        elif self.cpu_load_percent > 60:
            score -= 10
            
        if self.memory_usage_percent > 90:
            score -= 20
        elif self.memory_usage_percent > 75:
            score -= 10
            
        # Deduct points for high temperature
        if self.temperature_celsius and self.temperature_celsius > 70:
            score -= 15
        elif self.temperature_celsius and self.temperature_celsius > 60:
            score -= 5
            
        # Deduct points for offline status
        if self.status == 'offline':
            score -= 50
        elif self.status == 'error':
            score -= 30
        elif self.status == 'maintenance':
            score -= 10
            
        return max(0, score)
    
    def to_dict(self):
        """Convert router switch to dictionary representation."""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'management_port': self.management_port,
            'device_type': self.device_type,
            'model': self.model,
            'serial_number': self.serial_number,
            'mac_address': self.mac_address,
            'firmware_version': self.firmware_version,
            'routeros_version': self.routeros_version,
            'bootloader_version': self.bootloader_version,
            'architecture': self.architecture,
            'cpu_model': self.cpu_model,
            'cpu_frequency_mhz': self.cpu_frequency_mhz,
            'total_memory_mb': self.total_memory_mb,
            'total_disk_mb': self.total_disk_mb,
            'port_count': self.port_count,
            'management_vlan': self.management_vlan,
            'default_gateway': self.default_gateway,
            'dns_servers': self.dns_servers,
            'status': self.status,
            'uptime_seconds': self.uptime_seconds,
            'uptime_days': self.uptime_days,
            'uptime_hours': self.uptime_hours,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'cpu_load_percent': self.cpu_load_percent,
            'memory_usage_percent': self.memory_usage_percent,
            'temperature_celsius': self.temperature_celsius,
            'health_score': self.health_score,
            'config_backup_enabled': self.config_backup_enabled,
            'last_config_backup': self.last_config_backup.isoformat() if self.last_config_backup else None,
            'config_backup_path': self.config_backup_path,
            'auto_update_enabled': self.auto_update_enabled,
            'vlan_count': self.vlan_count,
            'stp_enabled': self.stp_enabled,
            'lldp_enabled': self.lldp_enabled,
            'wireless_enabled': self.wireless_enabled,
            'wireless_standard': self.wireless_standard,
            'wireless_channels': self.wireless_channels,
            'cluster_id': self.cluster_id,
            'tags': self.tags,
            'notes': self.notes,
            'location': self.location,
            'contact_person': self.contact_person,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
