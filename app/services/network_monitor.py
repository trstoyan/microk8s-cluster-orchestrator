"""Network monitoring service for collecting lease and interface data from routers."""

import json
import logging
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import paramiko
import re
from ..models.database import db
from ..models.network_lease import NetworkLease, NetworkInterface
from ..models.flask_models import Node, RouterSwitch

logger = logging.getLogger(__name__)

class NetworkMonitorService:
    """Service for monitoring network devices and collecting lease information."""
    
    def __init__(self):
        self.ssh_timeout = 30
        self.command_timeout = 60
    
    def scan_dhcp_leases(self, router_switch: RouterSwitch) -> Dict[str, Any]:
        """Scan router for DHCP leases and update database."""
        try:
            if router_switch.is_mikrotik:
                leases_data = self._scan_mikrotik_dhcp_leases(router_switch)
            else:
                raise NotImplementedError(f"DHCP scanning not implemented for {router_switch.device_type}")
            
            # Process and store leases
            processed_count = self._process_dhcp_leases(router_switch, leases_data)
            
            return {
                'success': True,
                'router_switch_id': router_switch.id,
                'leases_found': len(leases_data),
                'leases_processed': processed_count,
                'scan_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to scan DHCP leases for {router_switch.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'router_switch_id': router_switch.id,
                'scan_time': datetime.utcnow().isoformat()
            }
    
    def scan_network_interfaces(self, router_switch: RouterSwitch) -> Dict[str, Any]:
        """Scan router for network interfaces and update database."""
        try:
            if router_switch.is_mikrotik:
                interfaces_data = self._scan_mikrotik_interfaces(router_switch)
            else:
                raise NotImplementedError(f"Interface scanning not implemented for {router_switch.device_type}")
            
            # Process and store interfaces
            processed_count = self._process_network_interfaces(router_switch, interfaces_data)
            
            return {
                'success': True,
                'router_switch_id': router_switch.id,
                'interfaces_found': len(interfaces_data),
                'interfaces_processed': processed_count,
                'scan_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to scan network interfaces for {router_switch.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'router_switch_id': router_switch.id,
                'scan_time': datetime.utcnow().isoformat()
            }
    
    def _scan_mikrotik_dhcp_leases(self, router_switch: RouterSwitch) -> List[Dict[str, Any]]:
        """Scan MikroTik router for DHCP leases using SSH."""
        leases = []
        
        try:
            # Connect via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=router_switch.ip_address,
                port=router_switch.management_port,
                username='admin',  # This should be configurable
                timeout=self.ssh_timeout
            )
            
            # Get DHCP leases
            stdin, stdout, stderr = ssh.exec_command('/ip dhcp-server lease print detail without-paging')
            lease_output = stdout.read().decode('utf-8')
            
            # Parse lease information
            leases = self._parse_mikrotik_dhcp_output(lease_output)
            
            # Get ARP table for additional device information
            stdin, stdout, stderr = ssh.exec_command('/ip arp print without-paging')
            arp_output = stdout.read().decode('utf-8')
            arp_entries = self._parse_mikrotik_arp_output(arp_output)
            
            # Enhance lease data with ARP information
            for lease in leases:
                mac_address = lease.get('mac_address', '').lower()
                if mac_address in arp_entries:
                    lease.update(arp_entries[mac_address])
            
            ssh.close()
            
        except Exception as e:
            logger.error(f"Failed to connect to MikroTik router {router_switch.hostname}: {e}")
            raise
        
        return leases
    
    def _scan_mikrotik_interfaces(self, router_switch: RouterSwitch) -> List[Dict[str, Any]]:
        """Scan MikroTik router for network interfaces using SSH."""
        interfaces = []
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=router_switch.ip_address,
                port=router_switch.management_port,
                username='admin',  # This should be configurable
                timeout=self.ssh_timeout
            )
            
            # Get interface information
            stdin, stdout, stderr = ssh.exec_command('/interface print detail without-paging')
            interface_output = stdout.read().decode('utf-8')
            
            interfaces = self._parse_mikrotik_interface_output(interface_output)
            
            # Get interface statistics
            stdin, stdout, stderr = ssh.exec_command('/interface print stats without-paging')
            stats_output = stdout.read().decode('utf-8')
            stats_data = self._parse_mikrotik_interface_stats(stats_output)
            
            # Enhance interface data with statistics
            for interface in interfaces:
                name = interface.get('name')
                if name in stats_data:
                    interface.update(stats_data[name])
            
            ssh.close()
            
        except Exception as e:
            logger.error(f"Failed to get interfaces from MikroTik router {router_switch.hostname}: {e}")
            raise
        
        return interfaces
    
    def _parse_mikrotik_dhcp_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse MikroTik DHCP lease output."""
        leases = []
        current_lease = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if not line:
                if current_lease:
                    leases.append(current_lease)
                    current_lease = {}
                continue
            
            # Parse key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'address':
                    current_lease['ip_address'] = value
                elif key == 'mac-address':
                    current_lease['mac_address'] = value
                elif key == 'client-id':
                    current_lease['client_id'] = value
                elif key == 'server':
                    current_lease['dhcp_server'] = value
                elif key == 'dhcp-option':
                    current_lease['dhcp_options'] = value
                elif key == 'status':
                    current_lease['status'] = value
                elif key == 'expires-after':
                    current_lease['expires_after'] = value
                elif key == 'last-seen':
                    current_lease['last_seen'] = value
                elif key == 'host-name':
                    current_lease['hostname'] = value
        
        # Add the last lease if exists
        if current_lease:
            leases.append(current_lease)
        
        return leases
    
    def _parse_mikrotik_arp_output(self, output: str) -> Dict[str, Dict[str, Any]]:
        """Parse MikroTik ARP table output."""
        arp_entries = {}
        
        for line in output.split('\n')[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue
            
            # Parse ARP table format: flags address mac-address interface
            parts = line.split()
            if len(parts) >= 4:
                flags = parts[0]
                ip_address = parts[1]
                mac_address = parts[2].lower()
                interface = parts[3]
                
                arp_entries[mac_address] = {
                    'arp_flags': flags,
                    'interface': interface,
                    'verified_ip': ip_address
                }
        
        return arp_entries
    
    def _parse_mikrotik_interface_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse MikroTik interface output."""
        interfaces = []
        current_interface = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if not line:
                if current_interface:
                    interfaces.append(current_interface)
                    current_interface = {}
                continue
            
            # Parse key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'name':
                    current_interface['name'] = value
                elif key == 'type':
                    current_interface['interface_type'] = value
                elif key == 'mac-address':
                    current_interface['mac_address'] = value
                elif key == 'mtu':
                    try:
                        current_interface['mtu'] = int(value)
                    except ValueError:
                        pass
                elif key == 'running':
                    current_interface['enabled'] = value.lower() == 'true'
                elif key == 'disabled':
                    current_interface['disabled'] = value.lower() == 'true'
        
        # Add the last interface if exists
        if current_interface:
            interfaces.append(current_interface)
        
        return interfaces
    
    def _parse_mikrotik_interface_stats(self, output: str) -> Dict[str, Dict[str, Any]]:
        """Parse MikroTik interface statistics output."""
        stats = {}
        
        for line in output.split('\n')[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue
            
            # Parse stats format: name rx-byte tx-byte rx-packet tx-packet
            parts = line.split()
            if len(parts) >= 5:
                name = parts[0]
                try:
                    stats[name] = {
                        'rx_bytes': int(parts[1]),
                        'tx_bytes': int(parts[2]),
                        'rx_packets': int(parts[3]),
                        'tx_packets': int(parts[4])
                    }
                except ValueError:
                    continue
        
        return stats
    
    def _process_dhcp_leases(self, router_switch: RouterSwitch, leases_data: List[Dict[str, Any]]) -> int:
        """Process and store DHCP leases in database."""
        processed_count = 0
        
        for lease_data in leases_data:
            try:
                mac_address = lease_data.get('mac_address')
                ip_address = lease_data.get('ip_address')
                
                if not mac_address or not ip_address:
                    continue
                
                # Check if lease already exists
                existing_lease = NetworkLease.query.filter_by(
                    mac_address=mac_address,
                    router_switch_id=router_switch.id
                ).first()
                
                # Calculate lease times
                now = datetime.utcnow()
                lease_duration = 86400  # Default 24 hours
                
                if 'expires_after' in lease_data:
                    # Parse expires_after format (e.g., "23h59m59s")
                    expires_after = lease_data['expires_after']
                    lease_duration = self._parse_time_duration(expires_after)
                
                lease_end = now + timedelta(seconds=lease_duration)
                
                # Try to match with existing cluster nodes
                node = Node.query.filter_by(ip_address=ip_address).first()
                
                if existing_lease:
                    # Update existing lease
                    existing_lease.ip_address = ip_address
                    existing_lease.hostname = lease_data.get('hostname') or existing_lease.hostname
                    existing_lease.lease_end = lease_end
                    existing_lease.lease_duration_seconds = lease_duration
                    existing_lease.status = self._map_lease_status(lease_data.get('status', 'bound'))
                    existing_lease.last_seen = now
                    existing_lease.last_activity = now
                    existing_lease.is_active = True
                    existing_lease.node_id = node.id if node else None
                    
                    # Update connection count
                    existing_lease.connection_count += 1
                    
                else:
                    # Create new lease
                    new_lease = NetworkLease(
                        mac_address=mac_address,
                        ip_address=ip_address,
                        hostname=lease_data.get('hostname'),
                        lease_start=now,
                        lease_end=lease_end,
                        lease_duration_seconds=lease_duration,
                        is_active=True,
                        is_static=lease_data.get('status') == 'static',
                        client_id=lease_data.get('client_id'),
                        status=self._map_lease_status(lease_data.get('status', 'bound')),
                        router_switch_id=router_switch.id,
                        node_id=node.id if node else None,
                        discovered_by='dhcp_scan',
                        first_seen=now,
                        last_seen=now,
                        last_activity=now
                    )
                    db.session.add(new_lease)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process lease {lease_data}: {e}")
                continue
        
        # Mark old leases as inactive
        old_threshold = datetime.utcnow() - timedelta(hours=1)
        old_leases = NetworkLease.query.filter(
            NetworkLease.router_switch_id == router_switch.id,
            NetworkLease.last_activity < old_threshold,
            NetworkLease.is_active == True
        ).all()
        
        for old_lease in old_leases:
            old_lease.is_active = False
            old_lease.status = 'expired'
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit lease changes: {e}")
            raise
        
        return processed_count
    
    def _process_network_interfaces(self, router_switch: RouterSwitch, interfaces_data: List[Dict[str, Any]]) -> int:
        """Process and store network interfaces in database."""
        processed_count = 0
        
        for interface_data in interfaces_data:
            try:
                name = interface_data.get('name')
                if not name:
                    continue
                
                # Check if interface already exists
                existing_interface = NetworkInterface.query.filter_by(
                    name=name,
                    router_switch_id=router_switch.id
                ).first()
                
                # Determine interface status
                disabled = interface_data.get('disabled', False)
                enabled = interface_data.get('enabled', True)
                status = 'up' if enabled and not disabled else 'down'
                
                if existing_interface:
                    # Update existing interface
                    existing_interface.interface_type = interface_data.get('interface_type', existing_interface.interface_type)
                    existing_interface.mac_address = interface_data.get('mac_address') or existing_interface.mac_address
                    existing_interface.enabled = enabled
                    existing_interface.mtu = interface_data.get('mtu', existing_interface.mtu)
                    existing_interface.status = status
                    existing_interface.rx_bytes = interface_data.get('rx_bytes', existing_interface.rx_bytes)
                    existing_interface.tx_bytes = interface_data.get('tx_bytes', existing_interface.tx_bytes)
                    existing_interface.rx_packets = interface_data.get('rx_packets', existing_interface.rx_packets)
                    existing_interface.tx_packets = interface_data.get('tx_packets', existing_interface.tx_packets)
                    
                else:
                    # Create new interface
                    new_interface = NetworkInterface(
                        name=name,
                        interface_type=interface_data.get('interface_type', 'ethernet'),
                        mac_address=interface_data.get('mac_address'),
                        enabled=enabled,
                        mtu=interface_data.get('mtu', 1500),
                        status=status,
                        rx_bytes=interface_data.get('rx_bytes', 0),
                        tx_bytes=interface_data.get('tx_bytes', 0),
                        rx_packets=interface_data.get('rx_packets', 0),
                        tx_packets=interface_data.get('tx_packets', 0),
                        router_switch_id=router_switch.id
                    )
                    db.session.add(new_interface)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process interface {interface_data}: {e}")
                continue
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit interface changes: {e}")
            raise
        
        return processed_count
    
    def _parse_time_duration(self, duration_str: str) -> int:
        """Parse MikroTik time duration string to seconds."""
        if not duration_str:
            return 86400  # Default 24 hours
        
        total_seconds = 0
        
        # Parse format like "23h59m59s" or "1d2h3m4s"
        pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
        match = re.match(pattern, duration_str)
        
        if match:
            days, hours, minutes, seconds = match.groups()
            
            if days:
                total_seconds += int(days) * 86400
            if hours:
                total_seconds += int(hours) * 3600
            if minutes:
                total_seconds += int(minutes) * 60
            if seconds:
                total_seconds += int(seconds)
        
        return total_seconds if total_seconds > 0 else 86400
    
    def _map_lease_status(self, mikrotik_status: str) -> str:
        """Map MikroTik lease status to our status."""
        status_map = {
            'bound': 'active',
            'waiting': 'pending',
            'static': 'active',
            'offered': 'pending',
            'expired': 'expired'
        }
        
        return status_map.get(mikrotik_status.lower(), 'unknown')
    
    def match_leases_to_nodes(self) -> int:
        """Match network leases to cluster nodes based on IP addresses."""
        matched_count = 0
        
        # Get all active leases without node associations
        unmatched_leases = NetworkLease.query.filter(
            NetworkLease.is_active == True,
            NetworkLease.node_id.is_(None)
        ).all()
        
        for lease in unmatched_leases:
            # Try to find a node with matching IP
            node = Node.query.filter_by(ip_address=lease.ip_address).first()
            
            if node:
                lease.node_id = node.id
                matched_count += 1
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit lease-node matches: {e}")
            raise
        
        return matched_count
