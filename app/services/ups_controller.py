"""
UPS Controller for power management functions.
Provides high-level interface for UPS operations and cluster management.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.models.database import db
from app.models.ups import UPS
from app.models.flask_models import Cluster
from app.models.ups_cluster_rule import UPSClusterRule, PowerEventType, ClusterActionType
from app.services.ups_scanner import UPSScanner
from app.services.nut_configurator import NUTConfigurator
from app.services.power_management import PowerManagementService


class UPSController:
    """High-level controller for UPS operations and power management."""
    
    def __init__(self, app=None):
        self.app = app
        self.scanner = UPSScanner()
        self.nut_configurator = NUTConfigurator()
        self.power_management = PowerManagementService(app)
        self.logger = logging.getLogger(__name__)
    
    def scan_and_configure_ups(self) -> List[Dict]:
        """
        Scan for UPS devices and automatically configure them.
        
        Returns:
            List of configured UPS devices
        """
        try:
            self.logger.info("Scanning for UPS devices...")
            
            # Scan for UPS devices
            detected_ups = self.scanner.scan_usb_ups()
            
            configured_ups = []
            
            if self.app:
                with self.app.app_context():
                    return self._process_detected_ups(detected_ups)
            else:
                return self._process_detected_ups(detected_ups)
            
        except Exception as e:
            self.logger.error(f"Error scanning and configuring UPS: {e}")
            return []
    
    def _process_detected_ups(self, detected_ups: List[Dict]) -> List[Dict]:
        """Process detected UPS devices and configure them."""
        configured_ups = []
        
        for ups_info in detected_ups:
            # Check if UPS already exists in database
            existing_ups = db.session.query(UPS).filter(
                UPS.vendor_id == ups_info['vendor_id'],
                UPS.product_id == ups_info['product_id']
            ).first()
            
            if existing_ups:
                self.logger.info(f"UPS {existing_ups.name} already exists")
                configured_ups.append(existing_ups.to_dict())
                continue
            
            # Create new UPS record
            ups = UPS(
                name=ups_info['name'],
                model=ups_info['model'],
                vendor_id=ups_info['vendor_id'],
                product_id=ups_info['product_id'],
                driver=ups_info['recommended_driver'],
                port=ups_info['port'],
                connection_type=ups_info['connection_type'],
                usb_bus=ups_info['usb_bus'],
                usb_device=ups_info['usb_device'],
                usb_vendor_name=ups_info['usb_vendor_name'],
                usb_product_name=ups_info['usb_product_name'],
                is_local=ups_info['is_local'],
                system_protected=ups_info['system_protected'],
                last_scan=datetime.utcnow()
            )
            
            db.session.add(ups)
            db.session.commit()
            
            # Check if UPS is already configured in NUT
            if ups_info.get('nut_configured', False):
                # UPS is already configured, just check service status
                service_status = self.nut_configurator.get_nut_service_status()
                ups.nut_services_running = service_status.get('all_running', False)
                ups.nut_driver_running = service_status.get('services', {}).get('nut-driver', False)
                db.session.commit()
                
                self.logger.info(f"UPS {ups.name} already configured in NUT")
                configured_ups.append(ups.to_dict())
            else:
                # Configure NUT for this UPS
                if self.nut_configurator.configure_nut(ups):
                    # Start NUT services
                    if self.nut_configurator.start_nut_services():
                        ups.nut_services_running = True
                        ups.nut_driver_running = True
                        db.session.commit()
                        
                        self.logger.info(f"UPS {ups.name} configured and started successfully")
                        configured_ups.append(ups.to_dict())
                    else:
                        self.logger.error(f"Failed to start NUT services for UPS {ups.name}")
                else:
                    self.logger.error(f"Failed to configure NUT for UPS {ups.name}")
        
        return configured_ups
    
    def get_ups_status(self, ups_id: int) -> Dict:
        """Get current status of a UPS."""
        try:
            ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
            if not ups:
                return {'error': 'UPS not found'}
            
            # Get status from NUT
            status = self.nut_configurator.get_ups_status(ups)
            
            if 'error' in status:
                return status
            
            # Update UPS record with current status
            self._update_ups_status(ups, status)
            
            return {
                'ups': ups.to_dict(),
                'status': status,
                'nut_services': self.nut_configurator.get_nut_service_status()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting UPS status: {e}")
            return {'error': str(e)}
    
    def _update_ups_status(self, ups: UPS, status: Dict):
        """Update UPS status in database."""
        try:
            ups.status = status.get('ups.status', 'Unknown')
            ups.battery_charge = float(status.get('battery.charge', 0)) if status.get('battery.charge') else None
            ups.battery_voltage = float(status.get('battery.voltage', 0)) if status.get('battery.voltage') else None
            ups.battery_runtime = int(status.get('battery.runtime', 0)) if status.get('battery.runtime') else None
            ups.input_voltage = float(status.get('input.voltage', 0)) if status.get('input.voltage') else None
            ups.output_voltage = float(status.get('output.voltage', 0)) if status.get('output.voltage') else None
            ups.load_percentage = float(status.get('ups.load', 0)) if status.get('ups.load') else None
            ups.temperature = float(status.get('ups.temperature', 0)) if status.get('ups.temperature') else None
            ups.frequency = float(status.get('input.frequency', 0)) if status.get('input.frequency') else None
            ups.last_status_update = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating UPS status: {e}")
            db.session.rollback()
    
    def create_power_rule(self, ups_id: int, cluster_id: int, power_event: str, 
                         cluster_action: str, **kwargs) -> Dict:
        """Create a new power management rule."""
        try:
            # Convert string enums to enum objects
            power_event_enum = PowerEventType(power_event)
            cluster_action_enum = ClusterActionType(cluster_action)
            
            # Create the rule
            rule = self.power_management.create_power_rule(
                ups_id=ups_id,
                cluster_id=cluster_id,
                power_event=power_event_enum,
                cluster_action=cluster_action_enum,
                **kwargs
            )
            
            return {
                'success': True,
                'rule': rule.to_dict(),
                'message': f"Power management rule '{rule.name}' created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating power rule: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_power_rules(self, ups_id: Optional[int] = None, cluster_id: Optional[int] = None) -> List[Dict]:
        """Get power management rules."""
        try:
            rules = self.power_management.get_power_rules(ups_id, cluster_id)
            return [rule.to_dict() for rule in rules]
            
        except Exception as e:
            self.logger.error(f"Error getting power rules: {e}")
            return []
    
    def delete_power_rule(self, rule_id: int) -> Dict:
        """Delete a power management rule."""
        try:
            success = self.power_management.delete_power_rule(rule_id)
            
            if success:
                return {
                    'success': True,
                    'message': 'Power management rule deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Rule not found or could not be deleted'
                }
                
        except Exception as e:
            self.logger.error(f"Error deleting power rule: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_power_monitoring(self) -> Dict:
        """Start power event monitoring."""
        try:
            self.power_management.start_monitoring()
            return {
                'success': True,
                'message': 'Power event monitoring started'
            }
            
        except Exception as e:
            self.logger.error(f"Error starting power monitoring: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_power_monitoring(self) -> Dict:
        """Stop power event monitoring."""
        try:
            self.power_management.stop_monitoring()
            return {
                'success': True,
                'message': 'Power event monitoring stopped'
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping power monitoring: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_power_monitoring_status(self) -> Dict:
        """Get power monitoring status."""
        return {
            'monitoring_active': self.power_management.monitoring_active,
            'monitoring_interval': self.power_management.monitoring_interval
        }
    
    def test_ups_connection(self, ups_id: int) -> Dict:
        """Test connection to a UPS."""
        try:
            ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
            if not ups:
                return {'error': 'UPS not found'}
            
            success = self.nut_configurator.test_ups_connection(ups)
            
            return {
                'success': success,
                'message': f"UPS connection test {'passed' if success else 'failed'}"
            }
            
        except Exception as e:
            self.logger.error(f"Error testing UPS connection: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restart_nut_services(self) -> Dict:
        """Restart NUT services."""
        try:
            success = self.nut_configurator.restart_nut_services()
            
            if success:
                return {
                    'success': True,
                    'message': 'NUT services restarted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to restart NUT services'
                }
                
        except Exception as e:
            self.logger.error(f"Error restarting NUT services: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_nut_service_status(self) -> Dict:
        """Get NUT service status."""
        try:
            status = self.nut_configurator.get_nut_service_status()
            return {
                'success': True,
                'services': status
            }
            
        except Exception as e:
            self.logger.error(f"Error getting NUT service status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_ups(self, ups_id: int) -> Dict:
        """Remove UPS configuration and database record."""
        try:
            ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
            if not ups:
                return {'error': 'UPS not found'}
            
            # Remove NUT configuration
            self.nut_configurator.remove_ups_config(ups)
            
            # Delete UPS record
            db.session.delete(ups)
            db.session.commit()
            
            return {
                'success': True,
                'message': f"UPS {ups.name} removed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error removing UPS: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_all_ups(self) -> List[Dict]:
        """Get all UPS devices."""
        try:
            if self.app:
                with self.app.app_context():
                    ups_devices = db.session.query(UPS).all()
                    return [ups.to_dict() for ups in ups_devices]
            else:
                ups_devices = db.session.query(UPS).all()
                return [ups.to_dict() for ups in ups_devices]
            
        except Exception as e:
            self.logger.error(f"Error getting UPS devices: {e}")
            return []
    
    def get_ups_by_id(self, ups_id: int) -> Optional[Dict]:
        """Get UPS by ID."""
        try:
            if self.app:
                with self.app.app_context():
                    ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
                    return ups.to_dict() if ups else None
            else:
                ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
                return ups.to_dict() if ups else None
            
        except Exception as e:
            self.logger.error(f"Error getting UPS by ID: {e}")
            return None
    
    def update_ups_settings(self, ups_id: int, **kwargs) -> Dict:
        """Update UPS settings."""
        try:
            ups = db.session.query(UPS).filter(UPS.id == ups_id).first()
            if not ups:
                return {'error': 'UPS not found'}
            
            # Update allowed fields
            allowed_fields = [
                'low_battery_threshold', 'shutdown_delay', 'auto_shutdown_enabled',
                'graceful_shutdown_enabled', 'description'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(ups, field):
                    setattr(ups, field, value)
            
            ups.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'message': 'UPS settings updated successfully',
                'ups': ups.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error updating UPS settings: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_power_events(self) -> List[str]:
        """Get available power event types."""
        return [event.value for event in PowerEventType]
    
    def get_cluster_actions(self) -> List[str]:
        """Get available cluster action types."""
        return [action.value for action in ClusterActionType]
