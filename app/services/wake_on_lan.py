"""
Wake-on-LAN Service for sending magic packets to wake up nodes.
Provides functionality for both physical and virtual nodes (Proxmox VMs).
"""

import socket
import struct
import logging
import subprocess
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.models.database import db
from app.models.flask_models import Node, Operation


class WakeOnLANService:
    """Service for managing Wake-on-LAN operations."""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.default_port = 9
        self.default_broadcast = "255.255.255.255"
    
    def wake_node(self, node: Node, retries: int = 3, delay: float = 1.0) -> Dict:
        """
        Send Wake-on-LAN packet to a node.
        
        Args:
            node: Node object to wake up
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            Dictionary with success status and details
        """
        try:
            if not node.wol_enabled:
                return {
                    'success': False,
                    'error': 'Wake-on-LAN is not enabled for this node',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            
            if node.is_virtual_node:
                return self._wake_virtual_node(node, retries, delay)
            else:
                return self._wake_physical_node(node, retries, delay)
                
        except Exception as e:
            self.logger.error(f"Error waking node {node.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }
    
    def _wake_physical_node(self, node: Node, retries: int, delay: float) -> Dict:
        """Wake up a physical node using Wake-on-LAN magic packet."""
        try:
            if not node.wol_mac_address:
                return {
                    'success': False,
                    'error': 'No MAC address configured for Wake-on-LAN',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            
            # Format MAC address
            mac_address = node.format_mac_address(separator='')
            if not mac_address:
                return {
                    'success': False,
                    'error': 'Invalid MAC address format',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            
            # Create magic packet
            magic_packet = self._create_magic_packet(mac_address)
            
            # Send packet
            broadcast_address = node.wol_broadcast_address or self.default_broadcast
            port = node.wol_port or self.default_port
            
            success_count = 0
            for attempt in range(retries):
                try:
                    self._send_magic_packet(magic_packet, broadcast_address, port)
                    success_count += 1
                    self.logger.info(f"Sent WoL packet to {node.hostname} (attempt {attempt + 1}/{retries})")
                    
                    if attempt < retries - 1:  # Don't sleep on last attempt
                        import time
                        time.sleep(delay)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to send WoL packet to {node.hostname} (attempt {attempt + 1}): {e}")
            
            # Log the operation
            self._log_wol_operation(node, 'wake', success_count > 0, f"Sent {success_count}/{retries} packets")
            
            return {
                'success': success_count > 0,
                'packets_sent': success_count,
                'total_attempts': retries,
                'broadcast_address': broadcast_address,
                'port': port,
                'node_id': node.id,
                'hostname': node.hostname,
                'mac_address': node.wol_mac_address
            }
            
        except Exception as e:
            self.logger.error(f"Error waking physical node {node.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }
    
    def _wake_virtual_node(self, node: Node, retries: int, delay: float) -> Dict:
        """Wake up a virtual node (Proxmox VM)."""
        try:
            if not node.proxmox_vm_id or not node.proxmox_host_id:
                return {
                    'success': False,
                    'error': 'Proxmox VM ID and host ID required for virtual nodes',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            
            # For Proxmox VMs, we would need to:
            # 1. Connect to the Proxmox host
            # 2. Start the VM using the Proxmox API
            # For now, we'll return a note that this needs to be implemented
            
            self.logger.info(f"Virtual node wake requested for {node.hostname} (Proxmox VM {node.proxmox_vm_id})")
            
            # Log the operation
            self._log_wol_operation(node, 'wake_vm', False, "Proxmox VM wake not yet implemented")
            
            return {
                'success': False,
                'error': 'Proxmox VM wake functionality not yet implemented',
                'node_id': node.id,
                'hostname': node.hostname,
                'proxmox_vm_id': node.proxmox_vm_id,
                'note': 'This feature requires Proxmox API integration'
            }
            
        except Exception as e:
            self.logger.error(f"Error waking virtual node {node.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }
    
    def _create_magic_packet(self, mac_address: str) -> bytes:
        """
        Create a Wake-on-LAN magic packet.
        
        Args:
            mac_address: MAC address in format 'XXXXXXXXXXXX'
            
        Returns:
            Magic packet as bytes
        """
        # Convert MAC address to bytes
        mac_bytes = bytes.fromhex(mac_address)
        
        # Create magic packet: 6 bytes of 0xFF + 16 repetitions of MAC address
        magic_packet = b'\xff' * 6 + mac_bytes * 16
        
        return magic_packet
    
    def _send_magic_packet(self, magic_packet: bytes, broadcast_address: str, port: int):
        """Send magic packet to broadcast address."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast_address, port))
    
    def wake_cluster(self, cluster_id: int, retries: int = 3, delay: float = 1.0) -> Dict:
        """
        Wake up all nodes in a cluster.
        
        Args:
            cluster_id: ID of the cluster to wake up
            retries: Number of retry attempts per node
            delay: Delay between retries in seconds
            
        Returns:
            Dictionary with results for each node
        """
        try:
            nodes = db.session.query(Node).filter(Node.cluster_id == cluster_id).all()
            
            if not nodes:
                return {
                    'success': False,
                    'error': f'No nodes found for cluster {cluster_id}',
                    'cluster_id': cluster_id
                }
            
            results = {}
            successful_nodes = 0
            failed_nodes = 0
            
            for node in nodes:
                result = self.wake_node(node, retries, delay)
                results[node.hostname] = result
                
                if result.get('success', False):
                    successful_nodes += 1
                else:
                    failed_nodes += 1
            
            # Log cluster wake operation
            self._log_cluster_operation(cluster_id, 'wake_cluster', successful_nodes > 0, 
                                      f"Woke {successful_nodes}/{len(nodes)} nodes")
            
            return {
                'success': successful_nodes > 0,
                'cluster_id': cluster_id,
                'total_nodes': len(nodes),
                'successful_nodes': successful_nodes,
                'failed_nodes': failed_nodes,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Error waking cluster {cluster_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'cluster_id': cluster_id
            }
    
    def collect_mac_addresses(self, nodes: List[Node]) -> Dict:
        """
        Collect MAC addresses from nodes using SSH.
        
        Args:
            nodes: List of Node objects to collect MAC addresses from
            
        Returns:
            Dictionary with MAC address collection results
        """
        results = {}
        
        for node in nodes:
            try:
                mac_addresses = self._get_node_mac_addresses(node)
                results[node.hostname] = {
                    'success': True,
                    'mac_addresses': mac_addresses,
                    'node_id': node.id
                }
                
                # Update node with primary MAC address if found
                if mac_addresses and not node.wol_mac_address:
                    primary_mac = self._select_primary_mac(mac_addresses)
                    if primary_mac:
                        node.wol_mac_address = primary_mac
                        db.session.commit()
                        self.logger.info(f"Updated {node.hostname} with MAC address: {primary_mac}")
                
            except Exception as e:
                self.logger.error(f"Error collecting MAC address for {node.hostname}: {e}")
                results[node.hostname] = {
                    'success': False,
                    'error': str(e),
                    'node_id': node.id
                }
        
        return results
    
    def _get_node_mac_addresses(self, node: Node) -> List[Dict]:
        """Get MAC addresses from a node via SSH."""
        try:
            # SSH command to get network interfaces and their MAC addresses
            cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {node.ssh_user}@{node.ip_address} 'ip link show'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"SSH command failed: {result.stderr}")
            
            return self._parse_mac_addresses(result.stdout)
            
        except Exception as e:
            self.logger.error(f"Error getting MAC addresses from {node.hostname}: {e}")
            raise
    
    def _parse_mac_addresses(self, ip_output: str) -> List[Dict]:
        """Parse MAC addresses from ip link show output."""
        mac_addresses = []
        
        lines = ip_output.split('\n')
        current_interface = None
        
        for line in lines:
            line = line.strip()
            
            # Match interface name (e.g., "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>")
            interface_match = re.match(r'^\d+:\s+(\w+):', line)
            if interface_match:
                current_interface = interface_match.group(1)
                continue
            
            # Match MAC address (e.g., "link/ether aa:bb:cc:dd:ee:ff")
            mac_match = re.search(r'link/ether\s+([0-9a-fA-F:]{17})', line)
            if mac_match and current_interface:
                mac_address = mac_match.group(1)
                
                # Skip loopback and virtual interfaces
                if (current_interface.startswith('lo') or 
                    current_interface.startswith('docker') or
                    current_interface.startswith('veth') or
                    current_interface.startswith('br-')):
                    continue
                
                mac_addresses.append({
                    'interface': current_interface,
                    'mac_address': mac_address
                })
        
        return mac_addresses
    
    def _select_primary_mac(self, mac_addresses: List[Dict]) -> Optional[str]:
        """Select the primary MAC address from a list of interfaces."""
        if not mac_addresses:
            return None
        
        # Prefer ethernet interfaces
        for mac_info in mac_addresses:
            if mac_info['interface'].startswith('eth') or mac_info['interface'].startswith('en'):
                return mac_info['mac_address']
        
        # Fall back to first non-loopback interface
        return mac_addresses[0]['mac_address']
    
    def enable_wol_on_node(self, node: Node) -> Dict:
        """
        Enable Wake-on-LAN on a node via SSH.
        
        Args:
            node: Node object to enable WoL on
            
        Returns:
            Dictionary with operation result
        """
        try:
            # SSH command to enable Wake-on-LAN
            cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {node.ssh_user}@{node.ip_address} 'sudo ethtool -s {self._get_primary_interface(node)} wol g'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                node.wol_enabled = True
                db.session.commit()
                
                self.logger.info(f"Enabled Wake-on-LAN on {node.hostname}")
                return {
                    'success': True,
                    'message': f'Enabled Wake-on-LAN on {node.hostname}',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to enable Wake-on-LAN: {result.stderr}',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
                
        except Exception as e:
            self.logger.error(f"Error enabling Wake-on-LAN on {node.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }
    
    def disable_wol_on_node(self, node: Node) -> Dict:
        """
        Disable Wake-on-LAN on a node via SSH.
        
        Args:
            node: Node object to disable WoL on
            
        Returns:
            Dictionary with operation result
        """
        try:
            # SSH command to disable Wake-on-LAN
            cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {node.ssh_user}@{node.ip_address} 'sudo ethtool -s {self._get_primary_interface(node)} wol d'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                node.wol_enabled = False
                db.session.commit()
                
                self.logger.info(f"Disabled Wake-on-LAN on {node.hostname}")
                return {
                    'success': True,
                    'message': f'Disabled Wake-on-LAN on {node.hostname}',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to disable Wake-on-LAN: {result.stderr}',
                    'node_id': node.id,
                    'hostname': node.hostname
                }
                
        except Exception as e:
            self.logger.error(f"Error disabling Wake-on-LAN on {node.hostname}: {e}")
            return {
                'success': False,
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }
    
    def _get_primary_interface(self, node: Node) -> str:
        """Get the primary network interface name for a node."""
        # This is a simplified approach - in practice, you might want to
        # query the node to determine the primary interface
        if node.wol_mac_address:
            # Try to determine interface from MAC address
            mac_addresses = self._get_node_mac_addresses(node)
            for mac_info in mac_addresses:
                if mac_info['mac_address'].replace(':', '').lower() == node.wol_mac_address.replace(':', '').lower():
                    return mac_info['interface']
        
        # Default to eth0 or en0
        return 'eth0'
    
    def _log_wol_operation(self, node: Node, operation: str, success: bool, details: str):
        """Log a Wake-on-LAN operation."""
        try:
            operation_record = Operation(
                operation_type="wol_operation",
                operation_name=f"Wake-on-LAN {operation}",
                description=f"WoL {operation} for {node.hostname}: {details}",
                status="completed" if success else "failed",
                success=success,
                output=details,
                node_id=node.id,
                cluster_id=node.cluster_id,
                created_by="wol_service"
            )
            
            db.session.add(operation_record)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging WoL operation: {e}")
    
    def _log_cluster_operation(self, cluster_id: int, operation: str, success: bool, details: str):
        """Log a cluster Wake-on-LAN operation."""
        try:
            operation_record = Operation(
                operation_type="wol_cluster_operation",
                operation_name=f"Wake-on-LAN {operation}",
                description=f"WoL {operation} for cluster {cluster_id}: {details}",
                status="completed" if success else "failed",
                success=success,
                output=details,
                cluster_id=cluster_id,
                created_by="wol_service"
            )
            
            db.session.add(operation_record)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging WoL cluster operation: {e}")
    
    def get_wol_status(self, node: Node) -> Dict:
        """
        Get Wake-on-LAN status for a node.
        
        Args:
            node: Node object to check
            
        Returns:
            Dictionary with WoL status information
        """
        try:
            status = {
                'node_id': node.id,
                'hostname': node.hostname,
                'wol_enabled': node.wol_enabled,
                'wol_configured': node.wol_configured,
                'wol_description': node.wol_description,
                'mac_address': node.wol_mac_address,
                'method': node.wol_method,
                'port': node.wol_port,
                'broadcast_address': node.wol_broadcast_address,
                'is_virtual_node': node.is_virtual_node
            }
            
            if node.is_virtual_node:
                status.update({
                    'proxmox_vm_id': node.proxmox_vm_id,
                    'proxmox_host_id': node.proxmox_host_id
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting WoL status for {node.hostname}: {e}")
            return {
                'error': str(e),
                'node_id': node.id,
                'hostname': node.hostname
            }

