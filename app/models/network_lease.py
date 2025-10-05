"""Network lease model for tracking DHCP leases and node connections."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import db

class NetworkLease(db.Model):
    """Represents a DHCP lease from router/switch devices."""
    
    __tablename__ = 'network_leases'
    
    id = Column(Integer, primary_key=True)
    
    # Lease identification
    mac_address = Column(String(17), nullable=False)  # MAC address of client
    ip_address = Column(String(45), nullable=False)   # IPv4 or IPv6 assigned
    hostname = Column(String(255))                    # Client hostname if available
    
    # Lease details
    lease_start = Column(DateTime, nullable=False)
    lease_end = Column(DateTime, nullable=False)
    lease_duration_seconds = Column(Integer, default=86400)  # 24 hours default
    is_active = Column(Boolean, default=True)
    is_static = Column(Boolean, default=False)  # Static vs dynamic lease
    
    # Network information
    vlan_id = Column(Integer)
    subnet = Column(String(50))  # e.g., "192.168.1.0/24"
    gateway = Column(String(45))
    dns_servers = Column(Text)  # JSON string of DNS servers
    
    # Client information
    vendor_class = Column(String(255))  # DHCP vendor class identifier
    client_id = Column(String(255))     # DHCP client identifier
    user_class = Column(String(255))    # DHCP user class
    
    # Connection tracking
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    connection_count = Column(Integer, default=1)
    
    # Device fingerprinting
    device_type = Column(String(100))   # e.g., "linux", "windows", "android"
    os_version = Column(String(100))
    device_model = Column(String(100))
    
    # Status and monitoring
    status = Column(String(50), default='active')  # active, expired, reserved, conflict
    last_activity = Column(DateTime, default=datetime.utcnow)
    bytes_sent = Column(Integer, default=0)
    bytes_received = Column(Integer, default=0)
    
    # Relationships
    router_switch_id = Column(Integer, ForeignKey('router_switches.id'), nullable=False)
    router_switch = relationship("RouterSwitch", back_populates="leases", lazy="select")
    node_id = Column(Integer, ForeignKey('nodes.id'), nullable=True)  # If this lease corresponds to a cluster node
    node = relationship("Node", back_populates="lease_info", lazy="select")
    
    # Metadata
    discovered_by = Column(String(100), default='dhcp_scan')  # dhcp_scan, arp_scan, manual
    tags = Column(Text)  # JSON string for flexible tagging
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NetworkLease {self.mac_address} -> {self.ip_address} ({self.hostname})>'
    
    @property
    def is_expired(self):
        """Check if the lease has expired."""
        return datetime.utcnow() > self.lease_end
    
    @property
    def time_remaining(self):
        """Get remaining lease time in seconds."""
        if self.is_expired:
            return 0
        return int((self.lease_end - datetime.utcnow()).total_seconds())
    
    @property
    def uptime_hours(self):
        """Calculate uptime since first seen."""
        if self.first_seen:
            return int((datetime.utcnow() - self.first_seen).total_seconds() / 3600)
        return 0
    
    @property
    def is_cluster_node(self):
        """Check if this lease belongs to a cluster node."""
        return self.node_id is not None
    
    def to_dict(self):
        """Convert network lease to dictionary representation."""
        return {
            'id': self.id,
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'hostname': self.hostname,
            'lease_start': self.lease_start.isoformat() if self.lease_start else None,
            'lease_end': self.lease_end.isoformat() if self.lease_end else None,
            'lease_duration_seconds': self.lease_duration_seconds,
            'time_remaining': self.time_remaining,
            'is_active': self.is_active,
            'is_static': self.is_static,
            'is_expired': self.is_expired,
            'vlan_id': self.vlan_id,
            'subnet': self.subnet,
            'gateway': self.gateway,
            'dns_servers': self.dns_servers,
            'vendor_class': self.vendor_class,
            'client_id': self.client_id,
            'user_class': self.user_class,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'connection_count': self.connection_count,
            'uptime_hours': self.uptime_hours,
            'device_type': self.device_type,
            'os_version': self.os_version,
            'device_model': self.device_model,
            'status': self.status,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'router_switch_id': self.router_switch_id,
            'router_switch': self.router_switch.to_dict() if self.router_switch else None,
            'node_id': self.node_id,
            'is_cluster_node': self.is_cluster_node,
            'discovered_by': self.discovered_by,
            'tags': self.tags,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class NetworkInterface(db.Model):
    """Represents network interfaces on router/switch devices."""
    
    __tablename__ = 'network_interfaces'
    
    id = Column(Integer, primary_key=True)
    
    # Interface identification
    name = Column(String(100), nullable=False)  # e.g., "ether1", "wlan1", "bridge1"
    interface_type = Column(String(50), nullable=False)  # ethernet, wireless, bridge, vlan, etc.
    mac_address = Column(String(17))
    
    # Interface configuration
    enabled = Column(Boolean, default=True)
    mtu = Column(Integer, default=1500)
    speed_mbps = Column(Integer)  # Link speed in Mbps
    duplex = Column(String(20))  # full, half, auto
    
    # IP configuration
    ip_addresses = Column(Text)  # JSON array of IP addresses
    dhcp_server_enabled = Column(Boolean, default=False)
    dhcp_pool_start = Column(String(45))
    dhcp_pool_end = Column(String(45))
    dhcp_lease_time = Column(Integer, default=86400)  # seconds
    
    # VLAN configuration
    vlan_id = Column(Integer)
    vlan_mode = Column(String(20))  # access, trunk, hybrid
    allowed_vlans = Column(Text)  # JSON array of allowed VLAN IDs
    
    # Status and statistics
    status = Column(String(50), default='unknown')  # up, down, disabled, error
    rx_bytes = Column(Integer, default=0)
    tx_bytes = Column(Integer, default=0)
    rx_packets = Column(Integer, default=0)
    tx_packets = Column(Integer, default=0)
    rx_errors = Column(Integer, default=0)
    tx_errors = Column(Integer, default=0)
    
    # Relationships
    router_switch_id = Column(Integer, ForeignKey('router_switches.id'), nullable=False)
    router_switch = relationship("RouterSwitch", back_populates="interfaces", lazy="select")
    
    # Metadata
    description = Column(Text)
    tags = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NetworkInterface {self.name} on {self.router_switch.hostname if self.router_switch else "Unknown"}>'
    
    @property
    def utilization_percent(self):
        """Calculate interface utilization percentage."""
        if not self.speed_mbps:
            return 0
        
        # This is a simplified calculation - in reality you'd need recent traffic data
        max_bps = self.speed_mbps * 1000000  # Convert Mbps to bps
        current_bps = max(self.rx_bytes, self.tx_bytes)  # Simplified
        
        return min(100, (current_bps / max_bps) * 100) if max_bps > 0 else 0
    
    def to_dict(self):
        """Convert network interface to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'interface_type': self.interface_type,
            'mac_address': self.mac_address,
            'enabled': self.enabled,
            'mtu': self.mtu,
            'speed_mbps': self.speed_mbps,
            'duplex': self.duplex,
            'ip_addresses': self.ip_addresses,
            'dhcp_server_enabled': self.dhcp_server_enabled,
            'dhcp_pool_start': self.dhcp_pool_start,
            'dhcp_pool_end': self.dhcp_pool_end,
            'dhcp_lease_time': self.dhcp_lease_time,
            'vlan_id': self.vlan_id,
            'vlan_mode': self.vlan_mode,
            'allowed_vlans': self.allowed_vlans,
            'status': self.status,
            'rx_bytes': self.rx_bytes,
            'tx_bytes': self.tx_bytes,
            'rx_packets': self.rx_packets,
            'tx_packets': self.tx_packets,
            'rx_errors': self.rx_errors,
            'tx_errors': self.tx_errors,
            'utilization_percent': self.utilization_percent,
            'router_switch_id': self.router_switch_id,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
