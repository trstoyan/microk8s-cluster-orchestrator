"""
NUT (Network UPS Tools) Configuration utility for automatic UPS setup.
Designed for Raspberry Pi 5 with USB-connected UPS devices.
"""

import os
import subprocess
import shutil
import logging
from typing import Dict, List, Optional
from pathlib import Path

from app.models.ups import UPS
from app.models.database import db


class NUTConfigurator:
    """Utility for configuring NUT (Network UPS Tools) for UPS management."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nut_config_dir = Path("/etc/nut")
        self.nut_config_files = {
            'nut_conf': self.nut_config_dir / "nut.conf",
            'ups_conf': self.nut_config_dir / "ups.conf",
            'upsd_users': self.nut_config_dir / "upsd.users",
            'upsmon_conf': self.nut_config_dir / "upsmon.conf"
        }
        
        # NUT service names
        self.nut_services = {
            'server': 'nut-server',
            'client': 'nut-client',
            'driver': 'nut-driver'
        }
    
    def install_nut(self) -> bool:
        """Install NUT packages."""
        try:
            self.logger.info("Installing NUT packages...")
            
            # Update package list
            subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
            
            # Install NUT packages
            packages = ['nut', 'nut-client', 'nut-server', 'nut-driver']
            for package in packages:
                subprocess.run(['sudo', 'apt', 'install', '-y', package], 
                             check=True, capture_output=True)
            
            self.logger.info("NUT packages installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install NUT packages: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing NUT: {e}")
            return False
    
    def configure_nut(self, ups: UPS) -> bool:
        """Configure NUT for a specific UPS."""
        try:
            self.logger.info(f"Configuring NUT for UPS: {ups.name}")
            
            # Create backup of existing config files
            self._backup_config_files()
            
            # Configure nut.conf
            if not self._configure_nut_conf():
                return False
            
            # Configure ups.conf
            if not self._configure_ups_conf(ups):
                return False
            
            # Configure upsd.users
            if not self._configure_upsd_users():
                return False
            
            # Configure upsmon.conf
            if not self._configure_upsmon_conf(ups):
                return False
            
            # Set proper permissions
            self._set_nut_permissions()
            
            # Update UPS record
            ups.nut_configured = True
            db.session.commit()
            
            self.logger.info(f"NUT configured successfully for UPS: {ups.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring NUT: {e}")
            return False
    
    def _backup_config_files(self):
        """Create backup of existing NUT configuration files."""
        backup_dir = self.nut_config_dir / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        for config_name, config_path in self.nut_config_files.items():
            if config_path.exists():
                backup_path = backup_dir / f"{config_name}.backup"
                shutil.copy2(config_path, backup_path)
                self.logger.info(f"Backed up {config_name} to {backup_path}")
    
    def _configure_nut_conf(self) -> bool:
        """Configure nut.conf file."""
        try:
            nut_conf_content = """# NUT configuration file
# Mode: standalone, netserver, netclient
MODE=standalone
"""
            
            with open(self.nut_config_files['nut_conf'], 'w') as f:
                f.write(nut_conf_content)
            
            self.logger.info("Configured nut.conf")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring nut.conf: {e}")
            return False
    
    def _configure_ups_conf(self, ups: UPS) -> bool:
        """Configure ups.conf file."""
        try:
            # Read existing ups.conf or create new one
            ups_conf_path = self.nut_config_files['ups_conf']
            existing_content = ""
            
            if ups_conf_path.exists():
                with open(ups_conf_path, 'r') as f:
                    existing_content = f.read()
            
            # Check if UPS already configured
            if f"[{ups.name}]" in existing_content:
                self.logger.info(f"UPS {ups.name} already configured in ups.conf")
                return True
            
            # Add UPS configuration
            ups_config = f"""
[{ups.name}]
    driver = {ups.driver}
    port = {ups.port}
    vendorid = {ups.vendor_id}
    productid = {ups.product_id}
    desc = "{ups.model}"
"""
            
            # Append to existing content
            with open(ups_conf_path, 'a') as f:
                f.write(ups_config)
            
            self.logger.info(f"Added UPS {ups.name} to ups.conf")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring ups.conf: {e}")
            return False
    
    def _configure_upsd_users(self) -> bool:
        """Configure upsd.users file."""
        try:
            upsd_users_content = """# NUT upsd users file
# Format: username password [upsmon primary|secondary] [actions]

[admin]
    password = adminpass
    actions = SET
    instcmds = ALL

[monuser]
    password = monpass
    upsmon primary
"""
            
            with open(self.nut_config_files['upsd_users'], 'w') as f:
                f.write(upsd_users_content)
            
            self.logger.info("Configured upsd.users")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring upsd.users: {e}")
            return False
    
    def _configure_upsmon_conf(self, ups: UPS) -> bool:
        """Configure upsmon.conf file."""
        try:
            # Read existing upsmon.conf or create new one
            upsmon_conf_path = self.nut_config_files['upsmon_conf']
            existing_content = ""
            
            if upsmon_conf_path.exists():
                with open(upsmon_conf_path, 'r') as f:
                    existing_content = f.read()
            
            # Check if UPS already monitored
            if f"{ups.name}@localhost" in existing_content:
                self.logger.info(f"UPS {ups.name} already monitored in upsmon.conf")
                return True
            
            # Add UPS monitoring
            upsmon_config = f"""
# Monitor UPS
MONITOR {ups.name}@localhost 1 monuser monpass primary
"""
            
            # Append to existing content
            with open(upsmon_conf_path, 'a') as f:
                f.write(upsmon_config)
            
            self.logger.info(f"Added UPS {ups.name} to upsmon.conf")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring upsmon.conf: {e}")
            return False
    
    def _set_nut_permissions(self):
        """Set proper permissions for NUT configuration files."""
        try:
            # Set ownership to nut:nut
            for config_path in self.nut_config_files.values():
                if config_path.exists():
                    subprocess.run(['sudo', 'chown', 'nut:nut', str(config_path)], 
                                 check=True, capture_output=True)
                    subprocess.run(['sudo', 'chmod', '640', str(config_path)], 
                                 check=True, capture_output=True)
            
            self.logger.info("Set NUT configuration file permissions")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set NUT permissions: {e}")
        except Exception as e:
            self.logger.error(f"Error setting NUT permissions: {e}")
    
    def start_nut_services(self) -> bool:
        """Start NUT services."""
        try:
            self.logger.info("Starting NUT services...")
            
            # Start nut-server
            subprocess.run(['sudo', 'systemctl', 'start', self.nut_services['server']], 
                         check=True, capture_output=True)
            
            # Start nut-driver
            subprocess.run(['sudo', 'systemctl', 'start', self.nut_services['driver']], 
                         check=True, capture_output=True)
            
            # Enable services to start on boot
            subprocess.run(['sudo', 'systemctl', 'enable', self.nut_services['server']], 
                         check=True, capture_output=True)
            subprocess.run(['sudo', 'systemctl', 'enable', self.nut_services['driver']], 
                         check=True, capture_output=True)
            
            self.logger.info("NUT services started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start NUT services: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error starting NUT services: {e}")
            return False
    
    def stop_nut_services(self) -> bool:
        """Stop NUT services."""
        try:
            self.logger.info("Stopping NUT services...")
            
            # Stop nut-driver
            subprocess.run(['sudo', 'systemctl', 'stop', self.nut_services['driver']], 
                         check=True, capture_output=True)
            
            # Stop nut-server
            subprocess.run(['sudo', 'systemctl', 'stop', self.nut_services['server']], 
                         check=True, capture_output=True)
            
            self.logger.info("NUT services stopped successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to stop NUT services: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error stopping NUT services: {e}")
            return False
    
    def restart_nut_services(self) -> bool:
        """Restart NUT services."""
        try:
            self.logger.info("Restarting NUT services...")
            
            # Restart nut-server
            subprocess.run(['sudo', 'systemctl', 'restart', self.nut_services['server']], 
                         check=True, capture_output=True)
            
            # Restart nut-driver
            subprocess.run(['sudo', 'systemctl', 'restart', self.nut_services['driver']], 
                         check=True, capture_output=True)
            
            self.logger.info("NUT services restarted successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to restart NUT services: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error restarting NUT services: {e}")
            return False
    
    def get_nut_service_status(self) -> Dict[str, bool]:
        """Get status of NUT services."""
        status = {}
        
        for service_name, service in self.nut_services.items():
            try:
                result = subprocess.run(['sudo', 'systemctl', 'is-active', service], 
                                      capture_output=True, text=True)
                status[service_name] = result.returncode == 0
            except Exception as e:
                self.logger.error(f"Error checking {service} status: {e}")
                status[service_name] = False
        
        return status
    
    def test_ups_connection(self, ups: UPS) -> bool:
        """Test connection to UPS."""
        try:
            self.logger.info(f"Testing connection to UPS: {ups.name}")
            
            # Test with upsc
            result = subprocess.run(['upsc', f'{ups.name}@localhost'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.info(f"UPS {ups.name} connection test successful")
                return True
            else:
                self.logger.error(f"UPS {ups.name} connection test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"UPS {ups.name} connection test timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error testing UPS connection: {e}")
            return False
    
    def get_ups_status(self, ups: UPS) -> Dict:
        """Get current UPS status."""
        try:
            result = subprocess.run(['upsc', f'{ups.name}@localhost'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return {'error': result.stderr}
            
            status = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    status[key.strip()] = value.strip()
            
            return status
            
        except Exception as e:
            return {'error': str(e)}
    
    def remove_ups_config(self, ups: UPS) -> bool:
        """Remove UPS configuration from NUT."""
        try:
            self.logger.info(f"Removing UPS configuration: {ups.name}")
            
            # Remove from ups.conf
            self._remove_from_ups_conf(ups)
            
            # Remove from upsmon.conf
            self._remove_from_upsmon_conf(ups)
            
            # Restart services
            self.restart_nut_services()
            
            # Update UPS record
            ups.nut_configured = False
            ups.nut_services_running = False
            ups.nut_driver_running = False
            db.session.commit()
            
            self.logger.info(f"UPS {ups.name} configuration removed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing UPS configuration: {e}")
            return False
    
    def _remove_from_ups_conf(self, ups: UPS):
        """Remove UPS from ups.conf."""
        try:
            ups_conf_path = self.nut_config_files['ups_conf']
            
            if not ups_conf_path.exists():
                return
            
            with open(ups_conf_path, 'r') as f:
                lines = f.readlines()
            
            # Remove UPS section
            new_lines = []
            skip_section = False
            
            for line in lines:
                if line.strip() == f"[{ups.name}]":
                    skip_section = True
                    continue
                elif line.startswith('[') and line.strip() != f"[{ups.name}]":
                    skip_section = False
                
                if not skip_section:
                    new_lines.append(line)
            
            with open(ups_conf_path, 'w') as f:
                f.writelines(new_lines)
            
            self.logger.info(f"Removed UPS {ups.name} from ups.conf")
            
        except Exception as e:
            self.logger.error(f"Error removing UPS from ups.conf: {e}")
    
    def _remove_from_upsmon_conf(self, ups: UPS):
        """Remove UPS from upsmon.conf."""
        try:
            upsmon_conf_path = self.nut_config_files['upsmon_conf']
            
            if not upsmon_conf_path.exists():
                return
            
            with open(upsmon_conf_path, 'r') as f:
                lines = f.readlines()
            
            # Remove UPS monitoring line
            new_lines = []
            for line in lines:
                if f"{ups.name}@localhost" not in line:
                    new_lines.append(line)
            
            with open(upsmon_conf_path, 'w') as f:
                f.writelines(new_lines)
            
            self.logger.info(f"Removed UPS {ups.name} from upsmon.conf")
            
        except Exception as e:
            self.logger.error(f"Error removing UPS from upsmon.conf: {e}")
