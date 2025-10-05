# Wake-on-LAN (WoL) Guide for MicroK8s Cluster Orchestrator

This guide explains how to configure and use Wake-on-LAN functionality with the MicroK8s Cluster Orchestrator for automatic node wake-up after power restoration.

## Overview

Wake-on-LAN (WoL) allows you to remotely power on network-connected computers by sending a "magic packet" over the network. This is particularly useful in UPS management scenarios where:

1. Power failure occurs and UPS gracefully shuts down nodes
2. Power is restored
3. UPS can automatically wake up the cluster nodes using Wake-on-LAN

## Features

- **Physical Node Support**: Full Wake-on-LAN support for physical servers and workstations
- **Virtual Node Support**: Special handling for Proxmox VMs (requires additional configuration)
- **Power Management Integration**: Automatic wake-up triggered by UPS power restoration events
- **Manual Wake Operations**: Manual node and cluster wake-up via web interface, API, or CLI
- **MAC Address Collection**: Automatic discovery of node MAC addresses
- **Network Configuration**: Support for custom broadcast addresses and UDP ports

## Physical Node Configuration

### Hardware Requirements

1. **Network Interface**: The node must have a network interface that supports Wake-on-LAN
2. **BIOS/UEFI Settings**: Wake-on-LAN must be enabled in the system BIOS/UEFI
3. **Network Interface Settings**: Wake-on-LAN must be enabled on the network interface

### BIOS/UEFI Configuration

Enable the following settings in your system BIOS/UEFI:
- **Wake on LAN**: Enable
- **Wake on PCIe**: Enable (if available)
- **Deep Sleep**: Disable (prevents WoL from working)

### Operating System Configuration

The orchestrator can automatically configure Wake-on-LAN on nodes using Ansible:

```bash
# Configure Wake-on-LAN on all nodes
ansible-playbook -i ansible/inventory/dynamic_inventory.ini ansible/playbooks/configure_wake_on_lan.yml

# Collect MAC addresses from all nodes
ansible-playbook -i ansible/inventory/dynamic_inventory.ini ansible/playbooks/collect_network_info.yml
```

### Manual Configuration

If you prefer to configure Wake-on-LAN manually:

```bash
# Install ethtool (if not already installed)
sudo apt install ethtool  # Ubuntu/Debian
sudo yum install ethtool  # CentOS/RHEL

# Enable Wake-on-LAN on the primary network interface
sudo ethtool -s eth0 wol g

# Verify Wake-on-LAN is enabled
sudo ethtool eth0
```

## Virtual Node Configuration (Proxmox VMs)

**Important Note**: Physical Wake-on-LAN magic packets cannot wake up virtual machines directly. Proxmox VMs require different handling:

### Proxmox VM Wake Methods

1. **Proxmox API**: Use the Proxmox API to start VMs
2. **Proxmox CLI**: Use `qm start` command via SSH
3. **Scheduled Tasks**: Use cron jobs or systemd timers

### Configuration for Proxmox VMs

When adding a Proxmox VM as a node, mark it as virtual:

```bash
# Using CLI
python cli.py wol configure <node_id> --virtual --proxmox-vm-id 101 --proxmox-host-id 1

# Using API
PUT /api/nodes/<node_id>/wol/configure
{
    "is_virtual_node": true,
    "proxmox_vm_id": 101,
    "proxmox_host_id": 1
}
```

### Proxmox API Integration (Future Enhancement)

The current implementation includes placeholders for Proxmox VM wake functionality. To fully implement this, you would need to:

1. Install Proxmox API client library
2. Configure Proxmox API credentials
3. Implement VM start/stop operations
4. Handle authentication and error cases

Example implementation structure:
```python
async def _wake_proxmox_vm(self, node: Node) -> bool:
    """Wake up a Proxmox VM using the Proxmox API."""
    try:
        # Connect to Proxmox API
        # Authenticate
        # Start the VM
        # Return success/failure
        pass
    except Exception as e:
        self.logger.error(f"Failed to wake Proxmox VM {node.proxmox_vm_id}: {e}")
        return False
```

## Power Management Integration

### UPS Power Rules

Configure UPS power management rules to automatically wake nodes when power is restored:

1. **Power Event**: `power_restored`
2. **Cluster Action**: `wake_on_lan`

Example configuration:
```bash
# Using CLI
python cli.py ups create-rule \
    --ups-id 1 \
    --cluster-id 1 \
    --power-event power_restored \
    --cluster-action wake_on_lan \
    --name "Wake cluster after power restoration"
```

### Power Management Flow

1. **Power Loss**: UPS detects power loss, triggers graceful shutdown
2. **Graceful Shutdown**: Cluster nodes are shut down gracefully
3. **Power Restoration**: UPS detects power restoration
4. **Wake Trigger**: Power management rule triggers Wake-on-LAN action
5. **Node Wake-up**: Magic packets are sent to wake up nodes
6. **Cluster Recovery**: Nodes start up and rejoin the cluster

## Usage

### Web Interface

1. Navigate to the Nodes page
2. Click on a node to view details
3. Use the Wake-on-LAN section to:
   - View current WoL status
   - Configure WoL settings
   - Send wake packets manually

### API Endpoints

```bash
# Wake a specific node
POST /api/nodes/<node_id>/wol/wake

# Wake all nodes in a cluster
POST /api/clusters/<cluster_id>/wol/wake

# Get WoL status for a node
GET /api/nodes/<node_id>/wol/status

# Enable WoL on a node
POST /api/nodes/<node_id>/wol/enable

# Disable WoL on a node
POST /api/nodes/<node_id>/wol/disable

# Collect MAC addresses
POST /api/nodes/wol/collect-mac
{
    "node_ids": [1, 2, 3]
}

# Configure WoL settings
PUT /api/nodes/<node_id>/wol/configure
{
    "wol_enabled": true,
    "wol_mac_address": "aa:bb:cc:dd:ee:ff",
    "wol_method": "ethernet",
    "wol_port": 9,
    "wol_broadcast_address": "255.255.255.255"
}
```

### CLI Commands

```bash
# Wake a specific node
python cli.py wol wake-node <node_id> [--retries 3] [--delay 1.0]

# Wake all nodes in a cluster
python cli.py wol wake-cluster <cluster_id> [--retries 3] [--delay 1.0]

# Get WoL status for a node
python cli.py wol status <node_id>

# Enable WoL on a node
python cli.py wol enable <node_id>

# Disable WoL on a node
python cli.py wol disable <node_id>

# Collect MAC addresses from nodes
python cli.py wol collect-mac [--node-ids 1,2,3]

# Configure WoL settings for a node
python cli.py wol configure <node_id> \
    --mac-address "aa:bb:cc:dd:ee:ff" \
    --method ethernet \
    --port 9 \
    --broadcast "255.255.255.255" \
    --enable \
    --physical
```

## Troubleshooting

### Common Issues

1. **WoL Not Working on Physical Nodes**
   - Check BIOS/UEFI settings
   - Verify network interface supports WoL
   - Ensure ethtool shows WoL enabled
   - Check network connectivity and firewall rules

2. **MAC Address Collection Fails**
   - Verify SSH connectivity to nodes
   - Check if `ip` command is available on nodes
   - Ensure proper SSH keys are configured

3. **Magic Packets Not Sent**
   - Check broadcast address configuration
   - Verify UDP port 9 is not blocked
   - Ensure the orchestrator has network access

4. **Proxmox VMs Not Waking**
   - Current implementation requires manual Proxmox API integration
   - Use Proxmox web interface or CLI to start VMs manually
   - Consider implementing Proxmox API client

### Network Configuration

Ensure proper network configuration for Wake-on-LAN:

1. **Broadcast Address**: Use appropriate broadcast address for your subnet
2. **UDP Port**: Default port 9, ensure it's not blocked by firewall
3. **Network Segments**: WoL packets are typically limited to the same broadcast domain

### Firewall Configuration

If using a firewall, ensure the following ports are open:
- **UDP Port 9**: For Wake-on-LAN magic packets
- **UDP Port 7**: Alternative Wake-on-LAN port (if configured)

## Security Considerations

1. **Network Security**: Wake-on-LAN packets are unencrypted and can be spoofed
2. **Access Control**: Restrict Wake-on-LAN operations to authorized users
3. **Network Segmentation**: Consider network segmentation to limit WoL packet scope
4. **Monitoring**: Monitor Wake-on-LAN operations for unauthorized activity

## Database Migration

To add Wake-on-LAN fields to existing databases, run the migration script:

```bash
python scripts/migrate_wake_on_lan_fields.py
```

This script will:
1. Create a backup of your database
2. Add Wake-on-LAN fields to the nodes table
3. Set default values for existing nodes
4. Verify the migration was successful

## Future Enhancements

1. **Proxmox API Integration**: Full support for waking Proxmox VMs
2. **IPMI Support**: Alternative wake method using IPMI
3. **Network Discovery**: Automatic discovery of Wake-on-LAN capable nodes
4. **Advanced Scheduling**: Scheduled wake operations
5. **Monitoring Integration**: Integration with monitoring systems for wake status

## Support

For issues or questions regarding Wake-on-LAN functionality:

1. Check the logs in `logs/orchestrator.log`
2. Verify network connectivity and configuration
3. Test Wake-on-LAN manually using tools like `wakeonlan` or `etherwake`
4. Review BIOS/UEFI and network interface settings

