"""Node model for representing cluster nodes."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base, db

try:
    # Check if we're in a Flask context
    from flask import has_app_context
    use_flask = has_app_context()
except:
    use_flask = False

class Node(Base):
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
    
    # Detailed hardware information (JSON strings)
    hardware_info = Column(Text)  # Comprehensive hardware details
    cpu_info = Column(Text)       # CPU model, architecture, features
    memory_info = Column(Text)    # Memory details, speed, type
    disk_info = Column(Text)      # Disk details, types, speeds
    disk_partitions_info = Column(Text)  # Detailed disk partitions, LVM, RAID info
    storage_volumes_info = Column(Text)  # PVCs, PVs, Docker volumes info
    network_info = Column(Text)   # Network interfaces
    gpu_info = Column(Text)       # GPU information if available
    thermal_info = Column(Text)   # Temperature sensors
    
    # Wake-on-LAN (WoL) Configuration
    wol_enabled = Column(Boolean, default=False)  # Whether WoL is enabled on this node
    wol_mac_address = Column(String(17))  # MAC address for WoL (format: XX:XX:XX:XX:XX:XX)
    wol_method = Column(String(20), default='ethernet')  # ethernet, wifi, pci, usb
    wol_broadcast_address = Column(String(45))  # Broadcast address for WoL packet (optional)
    wol_port = Column(Integer, default=9)  # UDP port for WoL packet (default: 9)
    is_virtual_node = Column(Boolean, default=False)  # True for Proxmox VMs, requires different handling
    proxmox_vm_id = Column(Integer)  # Proxmox VM ID if this is a virtual node
    proxmox_host_id = Column(Integer)  # ID of the Proxmox host running this VM
    
    # Resource usage (updated regularly)
    cpu_usage_percent = Column(Integer)
    memory_usage_percent = Column(Integer)
    disk_usage_percent = Column(Integer)
    load_average = Column(String(50))
    uptime_seconds = Column(Integer)
    
    # Metadata
    tags = Column(Text)  # JSON string for flexible tagging
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    operations = relationship("Operation", back_populates="node")
    lease_info = relationship("NetworkLease", back_populates="node", uselist=False)
    
    def __repr__(self):
        return f'<Node {self.hostname} ({self.ip_address})>'
    
    @property
    def wol_configured(self):
        """Check if Wake-on-LAN is properly configured for this node."""
        return (self.wol_enabled and 
                self.wol_mac_address and 
                self.wol_mac_address != '' and
                self._is_valid_mac_address(self.wol_mac_address))
    
    @property
    def wol_description(self):
        """Get human-readable WoL configuration description."""
        if not self.wol_enabled:
            return "Wake-on-LAN disabled"
        
        if not self.wol_mac_address:
            return "Wake-on-LAN enabled (no MAC address configured)"
        
        if self.is_virtual_node:
            return f"Virtual node (Proxmox VM {self.proxmox_vm_id}) - requires VM wake method"
        
        return f"Wake-on-LAN enabled ({self.wol_method}) - MAC: {self.wol_mac_address}"
    
    @staticmethod
    def _is_valid_mac_address(mac_address):
        """Validate MAC address format."""
        import re
        if not mac_address:
            return False
        # Accept formats like XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac_address))
    
    def format_mac_address(self, separator=':'):
        """Format MAC address with specified separator."""
        if not self.wol_mac_address:
            return None
        
        # Remove any existing separators
        clean_mac = re.sub(r'[:-]', '', self.wol_mac_address)
        
        # Add new separator every 2 characters
        if separator == ':':
            return ':'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
        elif separator == '-':
            return '-'.join([clean_mac[i:i+2] for i in range(0, 12, 2)])
        else:
            return clean_mac
    
    def to_dict(self):
        """Convert Node object to dictionary."""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'ssh_user': self.ssh_user,
            'ssh_port': self.ssh_port,
            'ssh_key_path': self.ssh_key_path,
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
            'hardware_info': self.hardware_info,
            'cpu_info': self.cpu_info,
            'memory_info': self.memory_info,
            'disk_info': self.disk_info,
            'disk_partitions_info': self.disk_partitions_info,
            'storage_volumes_info': self.storage_volumes_info,
            'network_info': self.network_info,
            'gpu_info': self.gpu_info,
            'thermal_info': self.thermal_info,
            'wol_enabled': self.wol_enabled,
            'wol_mac_address': self.wol_mac_address,
            'wol_method': self.wol_method,
            'wol_broadcast_address': self.wol_broadcast_address,
            'wol_port': self.wol_port,
            'is_virtual_node': self.is_virtual_node,
            'proxmox_vm_id': self.proxmox_vm_id,
            'proxmox_host_id': self.proxmox_host_id,
            'wol_configured': self.wol_configured,
            'wol_description': self.wol_description,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_percent': self.memory_usage_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'load_average': self.load_average,
            'uptime_seconds': self.uptime_seconds,
            'tags': self.tags,
            'notes': self.notes,
            'cluster_id': self.cluster_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
