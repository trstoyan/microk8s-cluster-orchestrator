"""
UPS-Cluster Rules model for power management policies.
Links UPS devices to clusters and defines power management rules.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.database import Base, db


class PowerEventType(enum.Enum):
    """Types of power events that can trigger cluster actions."""
    POWER_LOSS = "power_loss"  # UPS goes on battery
    LOW_BATTERY = "low_battery"  # Battery charge below threshold
    CRITICAL_BATTERY = "critical_battery"  # Battery critically low
    POWER_RESTORED = "power_restored"  # Power restored, UPS back online
    UPS_SHUTDOWN = "ups_shutdown"  # UPS is shutting down
    UPS_STARTUP = "ups_startup"  # UPS started up


class ClusterActionType(enum.Enum):
    """Types of actions that can be performed on clusters."""
    GRACEFUL_SHUTDOWN = "graceful_shutdown"  # Graceful cluster shutdown
    FORCE_SHUTDOWN = "force_shutdown"  # Force cluster shutdown
    STARTUP = "startup"  # Start cluster
    SCALE_DOWN = "scale_down"  # Scale down cluster resources
    SCALE_UP = "scale_up"  # Scale up cluster resources
    PAUSE = "pause"  # Pause cluster operations
    RESUME = "resume"  # Resume cluster operations
    WAKE_ON_LAN = "wake_on_lan"  # Wake cluster nodes using Wake-on-LAN


class UPSClusterRule(db.Model):
    """Rules linking UPS devices to clusters for power management."""
    
    __tablename__ = 'ups_cluster_rules'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # UPS and Cluster References
    ups_id = Column(Integer, ForeignKey('ups.id'), nullable=False)
    cluster_id = Column(Integer, ForeignKey('clusters.id'), nullable=False)
    
    # Power Event Configuration
    power_event = Column(Enum(PowerEventType), nullable=False)
    battery_threshold = Column(Float)  # Battery percentage threshold for low_battery events
    
    # Cluster Action Configuration
    cluster_action = Column(Enum(ClusterActionType), nullable=False)
    action_delay = Column(Integer, default=0)  # Delay in seconds before executing action
    action_timeout = Column(Integer, default=300)  # Timeout for action execution
    
    # Rule Configuration
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)  # Lower number = higher priority
    auto_reverse = Column(Boolean, default=False)  # Automatically reverse action when condition changes
    
    # Notification Settings
    notify_on_trigger = Column(Boolean, default=True)
    notify_on_completion = Column(Boolean, default=True)
    notify_on_failure = Column(Boolean, default=True)
    
    # Execution History
    last_triggered = Column(DateTime)
    last_successful = Column(DateTime)
    last_failed = Column(DateTime)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ups = relationship("UPS", back_populates="cluster_rules")
    cluster = relationship("Cluster", back_populates="ups_rules")
    
    def __repr__(self):
        return f"<UPSClusterRule(id={self.id}, name='{self.name}', event='{self.power_event.value}', action='{self.cluster_action.value}')>"
    
    def to_dict(self):
        """Convert UPSClusterRule object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'ups_id': self.ups_id,
            'cluster_id': self.cluster_id,
            'power_event': self.power_event.value if self.power_event else None,
            'battery_threshold': self.battery_threshold,
            'cluster_action': self.cluster_action.value if self.cluster_action else None,
            'action_delay': self.action_delay,
            'action_timeout': self.action_timeout,
            'enabled': self.enabled,
            'priority': self.priority,
            'auto_reverse': self.auto_reverse,
            'notify_on_trigger': self.notify_on_trigger,
            'notify_on_completion': self.notify_on_completion,
            'notify_on_failure': self.notify_on_failure,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'last_successful': self.last_successful.isoformat() if self.last_successful else None,
            'last_failed': self.last_failed.isoformat() if self.last_failed else None,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    @property
    def is_active(self):
        """Check if rule is active and ready to execute."""
        return self.enabled and self.ups_id and self.cluster_id
    
    def should_trigger(self, ups_status: dict) -> bool:
        """
        Check if rule should trigger based on current UPS status.
        
        Args:
            ups_status: Dictionary with current UPS status
            
        Returns:
            True if rule should trigger
        """
        if not self.is_active:
            return False
        
        # Check power event conditions
        if self.power_event == PowerEventType.POWER_LOSS:
            return ups_status.get('status') == 'OB'  # On Battery
        
        elif self.power_event == PowerEventType.LOW_BATTERY:
            battery_charge = ups_status.get('battery_charge')
            if battery_charge is not None and self.battery_threshold is not None:
                return battery_charge <= self.battery_threshold
        
        elif self.power_event == PowerEventType.CRITICAL_BATTERY:
            battery_charge = ups_status.get('battery_charge')
            if battery_charge is not None:
                return battery_charge <= 10  # Critical threshold
        
        elif self.power_event == PowerEventType.POWER_RESTORED:
            return ups_status.get('status') == 'OL'  # Online
        
        elif self.power_event == PowerEventType.UPS_SHUTDOWN:
            return ups_status.get('status') == 'FSD'  # Forced Shutdown
        
        elif self.power_event == PowerEventType.UPS_STARTUP:
            return ups_status.get('status') == 'OL'  # Online
        
        return False
    
    def get_action_description(self) -> str:
        """Get human-readable description of the cluster action."""
        action_descriptions = {
            ClusterActionType.GRACEFUL_SHUTDOWN: "Gracefully shutdown cluster",
            ClusterActionType.FORCE_SHUTDOWN: "Force shutdown cluster",
            ClusterActionType.STARTUP: "Start cluster",
            ClusterActionType.SCALE_DOWN: "Scale down cluster resources",
            ClusterActionType.SCALE_UP: "Scale up cluster resources",
            ClusterActionType.PAUSE: "Pause cluster operations",
            ClusterActionType.RESUME: "Resume cluster operations",
            ClusterActionType.WAKE_ON_LAN: "Wake cluster nodes using Wake-on-LAN"
        }
        return action_descriptions.get(self.cluster_action, str(self.cluster_action.value))
    
    def get_event_description(self) -> str:
        """Get human-readable description of the power event."""
        event_descriptions = {
            PowerEventType.POWER_LOSS: "Power loss detected (UPS on battery)",
            PowerEventType.LOW_BATTERY: f"Low battery ({self.battery_threshold}% threshold)",
            PowerEventType.CRITICAL_BATTERY: "Critical battery level (10% or less)",
            PowerEventType.POWER_RESTORED: "Power restored (UPS back online)",
            PowerEventType.UPS_SHUTDOWN: "UPS shutting down",
            PowerEventType.UPS_STARTUP: "UPS started up"
        }
        return event_descriptions.get(self.power_event, str(self.power_event.value))
