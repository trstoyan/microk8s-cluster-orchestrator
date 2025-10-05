"""
UPS (Uninterruptible Power Supply) model for local USB power management integration.
Designed for Raspberry Pi 5 with USB-connected UPS devices.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base, db


class UPS(db.Model):
    """UPS model for storing local USB UPS information and configuration."""
    
    __tablename__ = 'ups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # UPS Hardware Information
    model = Column(String(100))
    vendor_id = Column(String(10))
    product_id = Column(String(10))
    driver = Column(String(50))  # e.g., nutdrv_qx, blazer_usb
    port = Column(String(50), default='auto')  # auto for USB detection
    connection_type = Column(String(20), default='usb')  # usb, serial, network
    
    # USB Device Information
    usb_bus = Column(String(10))
    usb_device = Column(String(10))
    usb_vendor_name = Column(String(100))
    usb_product_name = Column(String(100))
    
    # NUT Configuration
    nut_mode = Column(String(20), default='standalone')  # standalone, netserver, netclient
    nut_configured = Column(Boolean, default=False)
    nut_services_running = Column(Boolean, default=False)
    nut_driver_running = Column(Boolean, default=False)
    
    # UPS Status Information (updated via monitoring)
    status = Column(String(20))  # OL, OB, LB, etc.
    battery_charge = Column(Float)
    battery_voltage = Column(Float)
    battery_runtime = Column(Integer)  # seconds
    input_voltage = Column(Float)
    output_voltage = Column(Float)
    load_percentage = Column(Float)
    temperature = Column(Float)
    frequency = Column(Float)
    
    # Power Management Settings
    low_battery_threshold = Column(Integer, default=20)  # percentage
    shutdown_delay = Column(Integer, default=60)  # seconds
    auto_shutdown_enabled = Column(Boolean, default=True)
    graceful_shutdown_enabled = Column(Boolean, default=True)
    
    # System Integration
    is_local = Column(Boolean, default=True)  # True for local USB UPS
    system_protected = Column(Boolean, default=True)  # This system is protected by this UPS
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_status_update = Column(DateTime)
    last_scan = Column(DateTime)  # Last time UPS was scanned/detected
    
    # Relationships
    cluster_rules = relationship("UPSClusterRule", back_populates="ups")
    
    def __repr__(self):
        return f"<UPS(id={self.id}, name='{self.name}', model='{self.model}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert UPS object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model': self.model,
            'vendor_id': self.vendor_id,
            'product_id': self.product_id,
            'driver': self.driver,
            'port': self.port,
            'connection_type': self.connection_type,
            'usb_bus': self.usb_bus,
            'usb_device': self.usb_device,
            'usb_vendor_name': self.usb_vendor_name,
            'usb_product_name': self.usb_product_name,
            'nut_mode': self.nut_mode,
            'nut_configured': self.nut_configured,
            'nut_services_running': self.nut_services_running,
            'nut_driver_running': self.nut_driver_running,
            'status': self.status,
            'battery_charge': self.battery_charge,
            'battery_voltage': self.battery_voltage,
            'battery_runtime': self.battery_runtime,
            'input_voltage': self.input_voltage,
            'output_voltage': self.output_voltage,
            'load_percentage': self.load_percentage,
            'temperature': self.temperature,
            'frequency': self.frequency,
            'low_battery_threshold': self.low_battery_threshold,
            'shutdown_delay': self.shutdown_delay,
            'auto_shutdown_enabled': self.auto_shutdown_enabled,
            'graceful_shutdown_enabled': self.graceful_shutdown_enabled,
            'is_local': self.is_local,
            'system_protected': self.system_protected,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_status_update': self.last_status_update.isoformat() if self.last_status_update else None,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None
        }
    
    @property
    def is_online(self):
        """Check if UPS is online."""
        return self.status == 'OL'
    
    @property
    def is_low_battery(self):
        """Check if UPS battery is low."""
        return self.battery_charge is not None and self.battery_charge <= self.low_battery_threshold
    
    @property
    def battery_runtime_minutes(self):
        """Get battery runtime in minutes."""
        if self.battery_runtime:
            return self.battery_runtime // 60
        return None
    
    @property
    def status_description(self):
        """Get human-readable status description."""
        status_map = {
            'OL': 'Online',
            'OB': 'On Battery',
            'LB': 'Low Battery',
            'HB': 'High Battery',
            'RB': 'Battery Needs Replacing',
            'CHRG': 'Battery Charging',
            'DISCHRG': 'Battery Discharging',
            'BYPASS': 'Bypass Mode',
            'CAL': 'Calibration',
            'OFF': 'Off',
            'OVER': 'Overload',
            'TRIM': 'Voltage Trim',
            'BOOST': 'Voltage Boost',
            'FSD': 'Forced Shutdown'
        }
        return status_map.get(self.status, self.status or 'Unknown')
