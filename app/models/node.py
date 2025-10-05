"""Node model for representing cluster nodes."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, inspect
from sqlalchemy.orm import relationship
from .database import db
import logging

logger = logging.getLogger(__name__)

try:
    # Check if we're in a Flask context
    from flask import has_app_context
    use_flask = has_app_context()
except:
    use_flask = False

class Node(db.Model):
    """Represents a single node in the cluster."""
    
    __tablename__ = 'nodes'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    ssh_user = Column(String(100), default='ubuntu')
    ssh_port = Column(Integer, default=22)
    ssh_key_path = Column(String(500))
    
    # SSH Key Management
    ssh_key_generated = Column(Boolean, default=False)  # Whether SSH key pair has been generated
    ssh_public_key = Column(Text)  # Public key content
    ssh_key_fingerprint = Column(String(100))  # Key fingerprint for identification
    ssh_key_status = Column(String(50), default='not_generated')  # not_generated, generated, deployed, tested, failed
    ssh_connection_tested = Column(Boolean, default=False)  # Whether SSH connection has been tested
    ssh_connection_test_result = Column(Text)  # Last SSH connection test result (JSON)
    ssh_setup_instructions = Column(Text)  # Setup instructions for the user
    
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
    
    # Resource usage (updated regularly)
    cpu_usage_percent = Column(Integer)
    memory_usage_percent = Column(Integer)
    disk_usage_percent = Column(Integer)
    load_average = Column(String(50))
    uptime_seconds = Column(Integer)
    
    # Wake-on-LAN (WoL) Configuration
    wol_enabled = Column(Boolean, default=False)  # Whether WoL is enabled on this node
    wol_mac_address = Column(String(17))  # MAC address for WoL (format: XX:XX:XX:XX:XX:XX)
    wol_method = Column(String(20), default='ethernet')  # ethernet, wifi, pci, usb
    wol_broadcast_address = Column(String(45))  # Broadcast address for WoL packet (optional)
    wol_port = Column(Integer, default=9)  # UDP port for WoL packet (default: 9)
    is_virtual_node = Column(Boolean, default=False)  # True for Proxmox VMs, requires different handling
    proxmox_vm_id = Column(Integer)  # Proxmox VM ID if this is a virtual node
    proxmox_host_id = Column(Integer)  # ID of the Proxmox host running this VM
    
    # Metadata
    tags = Column(Text)  # JSON string for flexible tagging
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cluster_id = Column(Integer, ForeignKey('clusters.id'))
    operations = relationship("Operation", back_populates="node")
    lease_info = relationship("NetworkLease", back_populates="node", uselist=False, lazy="select")
    
    def __repr__(self):
        return f'<Node {self.hostname} ({self.ip_address})>'
    
    @classmethod
    def validate_schema_consistency(cls):
        """
        Validate that the model schema matches the database schema.
        
        Returns:
            Dict with validation results
        """
        try:
            if not use_flask:
                return {
                    'valid': False,
                    'error': 'No Flask application context available',
                    'details': {}
                }
            
            # Get database schema
            inspector = inspect(db.engine)
            db_columns = {col['name']: col for col in inspector.get_columns('nodes')}
            
            # Get model schema
            model_columns = {}
            for column in cls.__table__.columns:
                model_columns[column.name] = {
                    'type': str(column.type),
                    'nullable': column.nullable,
                    'default': column.default.arg if column.default else None
                }
            
            # Compare schemas
            missing_in_db = set(model_columns.keys()) - set(db_columns.keys())
            missing_in_model = set(db_columns.keys()) - set(model_columns.keys())
            
            # Check for type mismatches
            type_mismatches = []
            for col_name in set(model_columns.keys()) & set(db_columns.keys()):
                model_type = str(model_columns[col_name]['type']).lower()
                db_type = str(db_columns[col_name]['type']).lower()
                
                # Normalize types for comparison
                if 'boolean' in model_type and 'boolean' in db_type:
                    continue
                elif 'integer' in model_type and 'integer' in db_type:
                    continue
                elif 'varchar' in model_type and 'varchar' in db_type:
                    continue
                elif 'text' in model_type and 'text' in db_type:
                    continue
                elif 'datetime' in model_type and 'datetime' in db_type:
                    continue
                else:
                    type_mismatches.append({
                        'column': col_name,
                        'model_type': model_type,
                        'db_type': db_type
                    })
            
            is_valid = len(missing_in_db) == 0 and len(missing_in_model) == 0 and len(type_mismatches) == 0
            
            return {
                'valid': is_valid,
                'missing_in_db': list(missing_in_db),
                'missing_in_model': list(missing_in_model),
                'type_mismatches': type_mismatches,
                'details': {
                    'model_columns': len(model_columns),
                    'db_columns': len(db_columns),
                    'common_columns': len(set(model_columns.keys()) & set(db_columns.keys()))
                }
            }
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'details': {}
            }
    
    @classmethod
    def sync_with_database(cls):
        """
        Synchronize model attributes with database schema.
        This ensures that all database columns are accessible as model attributes.
        """
        try:
            if not use_flask:
                logger.warning("No Flask application context available for schema sync")
                return False
            
            inspector = inspect(db.engine)
            db_columns = {col['name'] for col in inspector.get_columns('nodes')}
            
            # Add missing attributes dynamically
            for col_name in db_columns:
                if not hasattr(cls, col_name):
                    # Create a property that accesses the column
                    def make_property(column_name):
                        def getter(self):
                            return getattr(self, f'_{column_name}', None)
                        def setter(self, value):
                            setattr(self, f'_{column_name}', value)
                        return property(getter, setter)
                    
                    setattr(cls, col_name, make_property(col_name))
                    logger.info(f"Added dynamic property for column: {col_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync model with database: {e}")
            return False
    
    def get_ssh_key_status(self):
        """
        Get comprehensive SSH key status information.
        
        Returns:
            Dict with SSH key status details
        """
        try:
            # Use getattr with defaults to handle missing attributes gracefully
            ssh_key_generated = getattr(self, 'ssh_key_generated', False)
            ssh_key_status = getattr(self, 'ssh_key_status', 'not_generated')
            ssh_public_key = getattr(self, 'ssh_public_key', None)
            ssh_key_fingerprint = getattr(self, 'ssh_key_fingerprint', None)
            ssh_key_path = getattr(self, 'ssh_key_path', None)
            ssh_connection_tested = getattr(self, 'ssh_connection_tested', False)
            ssh_connection_test_result = getattr(self, 'ssh_connection_test_result', None)
            ssh_setup_instructions = getattr(self, 'ssh_setup_instructions', None)
            
            # Check if key files exist
            key_files_exist = False
            if ssh_key_path:
                from pathlib import Path
                key_path = Path(ssh_key_path)
                public_key_path = key_path.with_suffix('.pub')
                key_files_exist = key_path.exists() and public_key_path.exists()
            
            # Determine overall status
            if ssh_key_generated and ssh_public_key and key_files_exist:
                if ssh_connection_tested and ssh_connection_test_result and 'success' in str(ssh_connection_test_result).lower():
                    overall_status = 'ready'
                    status_description = 'SSH connection ready'
                elif ssh_key_status in ['generated', 'deployed']:
                    overall_status = 'setup_required'
                    status_description = 'SSH key generated - setup required'
                else:
                    overall_status = 'generated'
                    status_description = 'SSH key generated'
            elif key_files_exist and not ssh_key_generated:
                overall_status = 'sync_needed'
                status_description = 'Key files exist but database not synchronized'
            else:
                overall_status = 'not_generated'
                status_description = 'SSH key not generated'
            
            return {
                'overall_status': overall_status,
                'status_description': status_description,
                'ssh_key_generated': ssh_key_generated,
                'ssh_key_status': ssh_key_status,
                'ssh_public_key': ssh_public_key,
                'ssh_key_fingerprint': ssh_key_fingerprint,
                'ssh_key_path': ssh_key_path,
                'ssh_connection_tested': ssh_connection_tested,
                'ssh_connection_test_result': ssh_connection_test_result,
                'ssh_setup_instructions': ssh_setup_instructions,
                'key_files_exist': key_files_exist,
                'sync_needed': key_files_exist and not ssh_key_generated
            }
            
        except Exception as e:
            logger.error(f"Failed to get SSH key status: {e}")
            return {
                'overall_status': 'error',
                'status_description': f'Error getting SSH key status: {str(e)}',
                'ssh_key_generated': False,
                'ssh_key_status': 'error',
                'ssh_public_key': None,
                'ssh_key_fingerprint': None,
                'ssh_key_path': None,
                'ssh_connection_tested': False,
                'ssh_connection_test_result': None,
                'ssh_setup_instructions': None,
                'key_files_exist': False,
                'sync_needed': False
            }
    
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
    
    @property
    def ssh_key_ready(self):
        """Check if SSH key is ready for use."""
        status = self.get_ssh_key_status()
        return status['overall_status'] in ['generated', 'setup_required', 'ready']
    
    @property
    def ssh_connection_ready(self):
        """Check if SSH connection is ready."""
        status = self.get_ssh_key_status()
        return status['overall_status'] == 'ready'
    
    def get_ssh_status_description(self):
        """Get human-readable SSH key status description."""
        status = self.get_ssh_key_status()
        return status['status_description']
    
    def to_dict(self):
        """Convert Node object to dictionary."""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'ssh_user': self.ssh_user,
            'ssh_port': self.ssh_port,
            'ssh_key_path': self.ssh_key_path,
            'ssh_key_generated': getattr(self, 'ssh_key_generated', False),
            'ssh_public_key': getattr(self, 'ssh_public_key', None),
            'ssh_key_fingerprint': getattr(self, 'ssh_key_fingerprint', None),
            'ssh_key_status': getattr(self, 'ssh_key_status', 'not_generated'),
            'ssh_connection_tested': getattr(self, 'ssh_connection_tested', False),
            'ssh_connection_test_result': getattr(self, 'ssh_connection_test_result', None),
            'ssh_setup_instructions': getattr(self, 'ssh_setup_instructions', None),
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
            'ssh_key_ready': self.ssh_key_ready,
            'ssh_connection_ready': self.ssh_connection_ready,
            'ssh_status_description': self.get_ssh_status_description(),
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
