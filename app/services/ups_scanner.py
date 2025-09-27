"""
UPS USB Scanner utility for detecting connected UPS devices.
Designed for Raspberry Pi 5 with USB-connected UPS devices.
"""

import subprocess
import re
import json
from typing import List, Dict, Optional
from datetime import datetime


class UPSScanner:
    """Scanner for detecting USB-connected UPS devices."""
    
    def __init__(self):
        self.supported_drivers = {
            'nutdrv_qx': ['0665', '0519', '0001', '0002'],  # Generic Q* driver
            'blazer_usb': ['0665', '0519'],  # Blazer USB driver
            'usbhid-ups': ['0665', '0519'],  # USB HID driver
            'apcsmart': ['051d', '0002'],  # APC Smart UPS
            'apcupsd-ups': ['051d', '0002'],  # APC UPS daemon
            'bcmxcp_usb': ['0665', '5161'],  # BCM XCP USB
            'cyberpower': ['0764', '0501'],  # CyberPower
            'dummy-ups': []  # Dummy driver for testing
        }
    
    def scan_usb_ups(self) -> List[Dict]:
        """
        Scan for USB-connected UPS devices using nut-scanner and upsc.
        
        Returns:
            List of detected UPS devices with their information.
        """
        ups_devices = []
        
        # First, try to get already configured UPS devices
        try:
            configured_ups = self._get_configured_ups_devices()
            ups_devices.extend(configured_ups)
        except Exception as e:
            print(f"Error getting configured UPS devices: {e}")
        
        # Then, try nut-scanner for new devices
        try:
            result = subprocess.run(
                ['nut-scanner', '-U'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                new_devices = self._parse_nut_scanner_output(result.stdout)
                # Filter out devices that are already configured
                for new_device in new_devices:
                    if not any(dev.get('name') == new_device.get('name') for dev in ups_devices):
                        ups_devices.append(new_device)
            else:
                print(f"nut-scanner failed: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            print("nut-scanner timed out")
        except FileNotFoundError:
            print("nut-scanner not found. Please install NUT tools.")
        except Exception as e:
            print(f"Error scanning for UPS devices: {e}")
        
        return ups_devices
    
    def _get_configured_ups_devices(self) -> List[Dict]:
        """Get already configured UPS devices using upsc -l and upsc."""
        ups_devices = []
        
        try:
            # Get list of configured UPS devices
            result = subprocess.run(
                ['upsc', '-l'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            # Parse UPS names from output
            ups_names = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    ups_names.append(line)
            
            # Get detailed information for each UPS
            for ups_name in ups_names:
                try:
                    ups_info = self._get_ups_info(ups_name)
                    if ups_info:
                        ups_devices.append(ups_info)
                except Exception as e:
                    print(f"Error getting info for UPS {ups_name}: {e}")
                    continue
                    
        except subprocess.TimeoutExpired:
            print("upsc -l timed out")
        except FileNotFoundError:
            print("upsc not found. Please install NUT tools.")
        except Exception as e:
            print(f"Error getting configured UPS devices: {e}")
        
        return ups_devices
    
    def _get_ups_info(self, ups_name: str) -> Optional[Dict]:
        """Get detailed information for a specific UPS."""
        try:
            result = subprocess.run(
                ['upsc', ups_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return None
            
            # Parse UPS information
            ups_info = {
                'name': ups_name,
                'connection_type': 'usb',
                'port': 'auto',
                'nut_configured': True,
                'is_local': True,
                'system_protected': True,
                'last_scan': datetime.utcnow()
            }
            
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'driver.name':
                        ups_info['driver'] = value
                    elif key == 'ups.vendorid':
                        ups_info['vendor_id'] = value
                    elif key == 'ups.productid':
                        ups_info['product_id'] = value
                    elif key == 'device.model':
                        ups_info['model'] = value
                    elif key == 'ups.status':
                        ups_info['status'] = value
                    elif key == 'battery.charge':
                        try:
                            ups_info['battery_charge'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'battery.voltage':
                        try:
                            ups_info['battery_voltage'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'battery.runtime':
                        try:
                            ups_info['battery_runtime'] = int(float(value))
                        except ValueError:
                            pass
                    elif key == 'input.voltage':
                        try:
                            ups_info['input_voltage'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'output.voltage':
                        try:
                            ups_info['output_voltage'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'ups.load':
                        try:
                            ups_info['load_percentage'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'ups.temperature':
                        try:
                            ups_info['temperature'] = float(value)
                        except ValueError:
                            pass
            
            # Set description if model is available
            if 'model' in ups_info:
                ups_info['description'] = f"{ups_info['model']} UPS"
            
            # Set recommended driver (use the current driver)
            if 'driver' in ups_info:
                ups_info['recommended_driver'] = ups_info['driver']
            else:
                ups_info['recommended_driver'] = 'nutdrv_qx'  # Default driver
            
            # Set default values for missing fields
            if 'usb_bus' not in ups_info:
                ups_info['usb_bus'] = None
            if 'usb_device' not in ups_info:
                ups_info['usb_device'] = None
            if 'usb_vendor_name' not in ups_info:
                ups_info['usb_vendor_name'] = None
            if 'usb_product_name' not in ups_info:
                ups_info['usb_product_name'] = None
            
            return ups_info
            
        except subprocess.TimeoutExpired:
            print(f"upsc {ups_name} timed out")
            return None
        except Exception as e:
            print(f"Error getting info for UPS {ups_name}: {e}")
            return None
    
    def _parse_nut_scanner_output(self, output: str) -> List[Dict]:
        """Parse nut-scanner output to extract UPS information."""
        ups_devices = []
        
        # Split output by sections
        sections = re.split(r'\[nutdev-usb\d+\]', output)
        
        for section in sections[1:]:  # Skip first empty section
            ups_info = self._parse_ups_section(section)
            if ups_info:
                ups_devices.append(ups_info)
        
        return ups_devices
    
    def _parse_ups_section(self, section: str) -> Optional[Dict]:
        """Parse a single UPS section from nut-scanner output."""
        lines = section.strip().split('\n')
        ups_info = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                
                if key == 'driver':
                    ups_info['driver'] = value
                elif key == 'port':
                    ups_info['port'] = value
                elif key == 'vendorid':
                    ups_info['vendor_id'] = value
                elif key == 'productid':
                    ups_info['product_id'] = value
                elif key == 'bus':
                    ups_info['usb_bus'] = value
                elif key == 'device':
                    ups_info['usb_device'] = value
                elif key == 'busport':
                    ups_info['usb_busport'] = value
        
        # Only return if we have essential information
        if 'driver' in ups_info and 'vendor_id' in ups_info and 'product_id' in ups_info:
            return ups_info
        
        return None
    
    def get_usb_device_info(self, vendor_id: str, product_id: str) -> Dict:
        """
        Get detailed USB device information using lsusb.
        
        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID
            
        Returns:
            Dictionary with USB device information
        """
        try:
            result = subprocess.run(
                ['lsusb', '-v', '-d', f'{vendor_id}:{product_id}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {}
            
            return self._parse_lsusb_output(result.stdout)
            
        except Exception as e:
            print(f"Error getting USB device info: {e}")
            return {}
    
    def _parse_lsusb_output(self, output: str) -> Dict:
        """Parse lsusb output to extract device information."""
        info = {}
        
        # Extract vendor and product names
        vendor_match = re.search(r'idVendor\s+0x\w+\s+([^\n]+)', output)
        if vendor_match:
            info['vendor_name'] = vendor_match.group(1).strip()
        
        product_match = re.search(r'idProduct\s+0x\w+\s+([^\n]+)', output)
        if product_match:
            info['product_name'] = product_match.group(1).strip()
        
        # Extract bus and device numbers
        bus_match = re.search(r'Bus\s+(\d+)', output)
        if bus_match:
            info['bus'] = bus_match.group(1)
        
        device_match = re.search(r'Device\s+(\d+)', output)
        if device_match:
            info['device'] = device_match.group(1)
        
        return info
    
    def detect_ups_model(self, vendor_id: str, product_id: str) -> str:
        """
        Detect UPS model based on vendor and product IDs.
        
        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID
            
        Returns:
            UPS model name
        """
        # Common UPS models
        ups_models = {
            ('0665', '5161'): 'ATEN 3000 Pro NJOY',
            ('0665', '0519'): 'Generic Q* UPS',
            ('051d', '0002'): 'APC Smart UPS',
            ('0764', '0501'): 'CyberPower UPS',
            ('0001', '0000'): 'Generic USB UPS',
            ('0002', '0000'): 'Generic USB UPS'
        }
        
        return ups_models.get((vendor_id, product_id), f'Unknown UPS ({vendor_id}:{product_id})')
    
    def get_recommended_driver(self, vendor_id: str, product_id: str) -> str:
        """
        Get recommended NUT driver for the UPS.
        
        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID
            
        Returns:
            Recommended NUT driver name
        """
        # Driver recommendations based on vendor/product IDs
        driver_map = {
            ('0665', '5161'): 'nutdrv_qx',  # ATEN 3000 Pro NJOY
            ('0665', '0519'): 'nutdrv_qx',  # Generic Q*
            ('051d', '0002'): 'apcsmart',   # APC Smart UPS
            ('0764', '0501'): 'cyberpower', # CyberPower
        }
        
        return driver_map.get((vendor_id, product_id), 'nutdrv_qx')
    
    def scan_all_ups(self) -> List[Dict]:
        """
        Comprehensive UPS scan including USB detection and device information.
        
        Returns:
            List of complete UPS device information
        """
        ups_devices = self.scan_usb_ups()
        complete_devices = []
        
        for device in ups_devices:
            # Get additional USB device information
            usb_info = self.get_usb_device_info(
                device.get('vendor_id', ''),
                device.get('product_id', '')
            )
            
            # Combine information
            complete_device = {
                'name': f"ups_{device.get('vendor_id', 'unknown')}_{device.get('product_id', 'unknown')}",
                'model': self.detect_ups_model(
                    device.get('vendor_id', ''),
                    device.get('product_id', '')
                ),
                'vendor_id': device.get('vendor_id', ''),
                'product_id': device.get('product_id', ''),
                'driver': device.get('driver', ''),
                'port': device.get('port', 'auto'),
                'connection_type': 'usb',
                'usb_bus': device.get('usb_bus', usb_info.get('bus', '')),
                'usb_device': device.get('usb_device', usb_info.get('device', '')),
                'usb_vendor_name': usb_info.get('vendor_name', ''),
                'usb_product_name': usb_info.get('product_name', ''),
                'recommended_driver': self.get_recommended_driver(
                    device.get('vendor_id', ''),
                    device.get('product_id', '')
                ),
                'is_local': True,
                'system_protected': True,
                'detected_at': datetime.utcnow().isoformat()
            }
            
            complete_devices.append(complete_device)
        
        return complete_devices
    
    def test_ups_connection(self, ups_name: str) -> Dict:
        """
        Test connection to a specific UPS using upsc.
        
        Args:
            ups_name: Name of the UPS to test
            
        Returns:
            Dictionary with connection test results
        """
        try:
            result = subprocess.run(
                ['upsc', f'{ups_name}@localhost'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'connected': True,
                    'status': 'OK',
                    'data': result.stdout,
                    'error': None
                }
            else:
                return {
                    'connected': False,
                    'status': 'ERROR',
                    'data': None,
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'connected': False,
                'status': 'ERROR',
                'data': None,
                'error': str(e)
            }
    
    def get_ups_status(self, ups_name: str) -> Dict:
        """
        Get current status of a UPS.
        
        Args:
            ups_name: Name of the UPS
            
        Returns:
            Dictionary with UPS status information
        """
        try:
            result = subprocess.run(
                ['upsc', f'{ups_name}@localhost'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
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
