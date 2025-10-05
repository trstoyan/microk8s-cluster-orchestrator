# Wake-on-LAN (WoL) Management Guide

This guide covers the Wake-on-LAN functionality integrated into the MicroK8s Cluster Orchestrator, which allows you to remotely power on cluster nodes after they have been gracefully shut down due to power events.

## Overview

Wake-on-LAN (WoL) is a network standard that allows you to remotely wake up computers that are in a low-power state by sending a special network packet called a "magic packet." This functionality is particularly useful in conjunction with the UPS power management system, allowing for automatic cluster startup after power restoration.

## Features

### Core Functionality
- **Individual Node Wake-up**: Wake specific nodes by MAC address
- **Cluster-wide Wake-up**: Wake all nodes in a cluster simultaneously
- **Virtual Node Support**: Special handling for Proxmox VMs and other virtual machines
- **Status Monitoring**: Track WoL configuration and readiness status
- **MAC Address Discovery**: Automatic collection of network interface information

### Integration Features
- **UPS Integration**: Automatic node wake-up after power restoration
- **Web Interface**: User-friendly WoL management through the web UI
- **CLI Commands**: Command-line interface for automation and scripting
- **REST API**: Programmatic access to all WoL functionality
- **Ansible Integration**: Automated WoL configuration on target nodes

## Configuration

### Node WoL Settings

Each node can be configured with the following WoL parameters:

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| `wol_enabled` | Enable Wake-on-LAN for this node | `false` | No |
| `wol_mac_address` | MAC address for WoL packets | `null` | Yes (if enabled) |
| `wol_method` | Wake method (ethernet, wifi, pci, usb) | `ethernet` | No |
| `wol_broadcast_address` | Broadcast address for WoL packet | `null` | No |
| `wol_port` | UDP port for WoL packet | `9` | No |
| `is_virtual_node` | True for Proxmox VMs | `false` | No |
| `proxmox_vm_id` | Proxmox VM ID (if virtual) | `null` | No |
| `proxmox_host_id` | Proxmox host ID (if virtual) | `null` | No |

### WoL Status Levels

The system tracks WoL readiness with the following status levels:

- **Ready** (Green): WoL is fully configured and ready to use
- **Partial** (Yellow): WoL is enabled but missing required configuration
- **Disabled** (Gray): WoL is not configured for this node

## Usage

### Web Interface

#### Configuring WoL for a Node

1. Navigate to the **Nodes** page
2. Click the **Actions** dropdown for the desired node
3. Select **Configure WoL**
4. Fill in the required information:
   - Enable WoL checkbox
   - MAC address (required)
   - Wake method
   - Broadcast address (optional)
   - UDP port (default: 9)
   - Virtual node settings (if applicable)

#### Collecting MAC Addresses

1. Navigate to the **Nodes** page
2. Click the **Actions** dropdown for the desired node
3. Select **Collect MAC**
4. The system will attempt to collect MAC address information from the node

#### Manual Wake-up Operations

**Individual Node:**
1. Navigate to the **Nodes** page
2. Click the **Actions** dropdown for the desired node
3. Select **Wake Node**

**Cluster-wide:**
1. Navigate to the **Clusters** page
2. Click the **Actions** dropdown for the desired cluster
3. Select **Wake Cluster**

### CLI Commands

#### Node Wake-up

```bash
# Wake a specific node
python cli.py wol wake-node <node_id>

# Wake a specific node with custom retry settings
python cli.py wol wake-node <node_id> --retries 5 --delay 2.0
```

#### Cluster Wake-up

```bash
# Wake all nodes in a cluster
python cli.py wol wake-cluster <cluster_id>

# Wake cluster with custom settings
python cli.py wol wake-cluster <cluster_id> --retries 3 --delay 1.5
```

#### Status and Configuration

```bash
# Check WoL status for a node
python cli.py wol status <node_id>

# Enable WoL for a node
python cli.py wol enable <node_id>

# Disable WoL for a node
python cli.py wol disable <node_id>

# Configure WoL settings
python cli.py wol configure <node_id> --mac-address "AA:BB:CC:DD:EE:FF" --method ethernet

# Collect MAC addresses from nodes
python cli.py wol collect-mac <node_id1> <node_id2> <node_id3>
```

### REST API

#### Wake-up Endpoints

```bash
# Wake a specific node
POST /api/nodes/{node_id}/wol/wake
Content-Type: application/json
{
  "retries": 3,
  "delay": 1.0
}

# Wake all nodes in a cluster
POST /api/clusters/{cluster_id}/wol/wake
Content-Type: application/json
{
  "retries": 3,
  "delay": 1.0
}
```

#### Status and Configuration Endpoints

```bash
# Get WoL status for a node
GET /api/nodes/{node_id}/wol/status

# Enable WoL for a node
POST /api/nodes/{node_id}/wol/enable

# Disable WoL for a node
POST /api/nodes/{node_id}/wol/disable

# Configure WoL settings
PUT /api/nodes/{node_id}/wol/configure
Content-Type: application/json
{
  "wol_enabled": true,
  "wol_mac_address": "AA:BB:CC:DD:EE:FF",
  "wol_method": "ethernet",
  "wol_broadcast_address": "255.255.255.255",
  "wol_port": 9,
  "is_virtual_node": false
}

# Collect MAC addresses from multiple nodes
POST /api/nodes/wol/collect-mac
Content-Type: application/json
{
  "node_ids": [1, 2, 3]
}
```

## Ansible Integration

### WoL Configuration Playbook

The system includes an Ansible playbook for configuring WoL on target nodes:

```bash
# Run the WoL configuration playbook
ansible-playbook -i inventory/dynamic_inventory.ini ansible/playbooks/configure_wake_on_lan.yml --limit "node_hostname"
```

### Network Information Collection

Collect network interface information for MAC address discovery:

```bash
# Collect network information
ansible-playbook -i inventory/dynamic_inventory.ini ansible/playbooks/collect_network_info.yml --limit "node_hostname"
```

## Virtual Machine Support

### Proxmox VM Handling

For Proxmox virtual machines, the system provides special handling:

1. **Mark as Virtual**: Set `is_virtual_node = true` in the node configuration
2. **Proxmox VM ID**: Specify the VM ID in Proxmox (`proxmox_vm_id`)
3. **Proxmox Host ID**: Specify the Proxmox host ID (`proxmox_host_id`)

**Note**: Virtual machines require different wake-up methods than physical machines. The system will attempt to use Proxmox API calls or other virtualization-specific wake-up mechanisms.

### Other Virtualization Platforms

The system can be extended to support other virtualization platforms by:
1. Adding platform-specific wake-up logic to the `WakeOnLANService`
2. Extending the node model with platform-specific fields
3. Creating platform-specific Ansible playbooks

## Troubleshooting

### Common Issues

#### WoL Not Working

1. **Check BIOS/UEFI Settings**:
   - Ensure Wake-on-LAN is enabled in BIOS/UEFI
   - Check that the network adapter supports WoL
   - Verify that the correct network adapter is configured

2. **Network Configuration**:
   - Ensure the target node is on the same network segment
   - Check firewall settings (UDP port 9 should be open)
   - Verify that broadcast packets are allowed

3. **MAC Address Issues**:
   - Verify the MAC address is correct
   - Ensure you're using the MAC address of the primary network interface
   - Check that the network interface is the one that supports WoL

#### Virtual Machine Issues

1. **Proxmox Configuration**:
   - Ensure the VM has Wake-on-LAN enabled in Proxmox
   - Check that the Proxmox API is accessible
   - Verify VM and host IDs are correct

2. **Network Interface**:
   - Use the MAC address of the virtual network interface
   - Ensure the virtual network adapter supports WoL

### Debugging Commands

```bash
# Check WoL status with detailed information
python cli.py wol status <node_id> --verbose

# Test WoL packet sending with debug output
python cli.py wol wake-node <node_id> --debug

# Validate network configuration
python cli.py wol collect-mac <node_id> --validate
```

### Log Files

Check the following log files for troubleshooting:

- Application logs: `logs/app.log`
- Ansible logs: `logs/ansible.log`
- System logs: `/var/log/syslog` (for network-related issues)

## Security Considerations

### Network Security

1. **Broadcast Domain**: WoL packets are sent to broadcast addresses, limiting their scope to the local network segment
2. **Firewall Rules**: Consider restricting WoL traffic to trusted networks only
3. **Access Control**: Ensure only authorized users can trigger wake-up operations

### Best Practices

1. **MAC Address Privacy**: MAC addresses are considered semi-identifying information
2. **Network Isolation**: Consider using VLANs to isolate WoL traffic
3. **Monitoring**: Monitor WoL usage for unusual patterns that might indicate security issues

## Integration with UPS Management

### Automatic Startup After Power Restoration

When integrated with the UPS power management system, WoL provides automatic cluster startup after power restoration:

1. **Power Loss Event**: UPS detects power loss and triggers cluster shutdown
2. **Graceful Shutdown**: All nodes are gracefully shut down
3. **Power Restoration**: UPS detects power restoration
4. **Automatic Wake-up**: WoL automatically wakes all cluster nodes
5. **Cluster Recovery**: Nodes start up and rejoin the cluster

### Configuration

To enable automatic wake-up after power restoration:

1. Configure UPS power management rules
2. Set cluster action to "wake_on_lan" for power restoration events
3. Ensure all nodes have WoL properly configured
4. Test the complete power cycle workflow

## Performance Considerations

### Network Impact

- WoL packets are small (102 bytes) and have minimal network impact
- Broadcast packets are limited to the local network segment
- No response packets are generated by WoL

### Timing Considerations

- **Delay Between Packets**: Configure appropriate delays between wake-up attempts
- **Retry Logic**: Use retry mechanisms for reliable wake-up
- **Cluster Startup Time**: Allow sufficient time for all nodes to start up before cluster operations

### Scalability

- WoL works well with clusters of up to 100+ nodes
- Consider network segmentation for very large deployments
- Use batch wake-up operations for efficiency

## Future Enhancements

### Planned Features

1. **Advanced Virtual Machine Support**: Extended support for VMware, Hyper-V, and other platforms
2. **Wake-up Scheduling**: Scheduled wake-up operations for maintenance windows
3. **Wake-up Groups**: Group nodes for staged wake-up sequences
4. **Network Topology Awareness**: Automatic discovery of network topology for optimal WoL routing
5. **Wake-up Analytics**: Tracking and analysis of wake-up success rates and patterns

### Integration Opportunities

1. **Monitoring Systems**: Integration with Prometheus, Grafana, and other monitoring tools
2. **Automation Platforms**: Integration with Ansible Tower, Rundeck, and other automation platforms
3. **Cloud Platforms**: Support for cloud-based virtual machines and containers
4. **Network Management**: Integration with network management systems for topology discovery

## Support and Contributing

### Getting Help

- Check the troubleshooting section above
- Review the application logs for error messages
- Consult the MicroK8s documentation for cluster-specific issues
- Submit issues through the project's issue tracker

### Contributing

Contributions are welcome! Areas where contributions would be particularly valuable:

1. **Additional Virtualization Platform Support**
2. **Enhanced Network Discovery**
3. **Improved Error Handling and Recovery**
4. **Performance Optimizations**
5. **Additional Ansible Playbooks**
6. **Enhanced Security Features**

### Development

To contribute to the WoL functionality:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add appropriate tests
5. Update documentation
6. Submit a pull request

---

For more information about the MicroK8s Cluster Orchestrator, see the main [README.md](../README.md) file.