"""Router/Switch model for representing network infrastructure devices like MikroTik."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base, db

class RouterSwitch(Base):
    """Represents a router or switch device (e.g., MikroTik RouterBoard)."""
    
    __tablename__ = 'router_switches'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    management_port = Column(Integer, default=22)  # SSH/Telnet port
    
    # Device identification
    device_type = Column(String(100), default='mikrotik')  # mikrotik, cisco, ubiquiti, etc.
    model = Column(String(100))  # e.g., "RB4011iGS+RM", "CCR1009-8G-1S-1S+"
    serial_number = Column(String(100), unique=True)
    mac_address = Column(String(17))  # Primary MAC address
    
    # Firmware and software
    firmware_version = Column(String(50))
    routeros_version = Column(String(50))  # For MikroTik devices
    bootloader_version = Column(String(50))
    architecture = Column(String(50))  # e.g., "mipsbe", "x86", "arm"
    
    # Hardware specifications
    cpu_model = Column(String(100))
    cpu_frequency_mhz = Column(Integer)
    total_memory_mb = Column(Integer)
    total_disk_mb = Column(Integer)
    port_count = Column(Integer, default=0)
    
    # Network configuration
    management_vlan = Column(Integer)
    default_gateway = Column(String(45))
    dns_servers = Column(Text)  # JSON string of DNS servers
    
    # Device status
    status = Column(String(50), default='unknown')  # unknown, online, offline, error, maintenance
    uptime_seconds = Column(Integer, default=0)
    last_seen = Column(DateTime, default=datetime.utcnow)
    cpu_load_percent = Column(Float, default=0.0)
    memory_usage_percent = Column(Float, default=0.0)
    temperature_celsius = Column(Float)
    
    # Configuration management
    config_backup_enabled = Column(Boolean, default=True)
    last_config_backup = Column(DateTime)
    config_backup_path = Column(String(500))
    auto_update_enabled = Column(Boolean, default=False)
    
    # VLAN and switching
    vlan_count = Column(Integer, default=0)
    stp_enabled = Column(Boolean, default=False)
    lldp_enabled = Column(Boolean, default=True)
    
    # Wireless (if applicable)
    wireless_enabled = Column(Boolean, default=False)
    wireless_standard = Column(String(20))  # 802.11n, 802.11ac, etc.
    wireless_channels = Column(Text)  # JSON string of configured channels
    
    # Relationships
    cluster_id = Column(Integer, ForeignKey('clusters.id'), nullable=True)
    operations = relationship("Operation", back_populates="router_switch")
    leases = relationship("NetworkLease", back_populates="router_switch", cascade="all, delete-orphan")
    interfaces = relationship("NetworkInterface", back_populates="router_switch", cascade="all, delete-orphan")
    
    # Metadata
    tags = Column(Text)  # JSON string for flexible tagging
    notes = Column(Text)
    location = Column(String(255))  # Physical location
    contact_person = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
