# Longhorn Setup Guide for MicroK8s Cluster Orchestrator

This guide explains how to set up Longhorn storage for your MicroK8s cluster using the Cluster Orchestrator.

## Overview

Longhorn is a distributed block storage system for Kubernetes that provides persistent storage for your applications. This orchestrator includes automated setup and management of Longhorn prerequisites across your cluster nodes.

## Prerequisites

Longhorn requires specific packages and services to be installed on each node:

### Required Packages
- `lvm2` - Logical Volume Manager
- `liblvm2cmd2.03` - LVM2 command library
- `nfs-common` - NFS support files
- `open-iscsi` - iSCSI initiator tools
- `util-linux` - System utilities

### Required Services
- `iscsid` - iSCSI daemon
- `multipathd` - Multipath daemon

### Required Commands
- `lvm`, `pvcreate`, `vgcreate`, `lvcreate` - LVM tools
- `iscsiadm` - iSCSI administration
- `multipath` - Multipath management
- `mount.nfs4`, `umount.nfs4` - NFS mounting

## Automated Setup

### Using the Web Interface

1. **Navigate to Node Details**
   - Go to the Nodes page
   - Click on a node hostname to view details

2. **Check Prerequisites**
   - Click "Check Prerequisites" to verify current status
   - Review the results in the Longhorn Prerequisites section

3. **Install Prerequisites**
   - Click "Install Prerequisites" to install missing packages
   - Monitor progress in the Operations page

4. **Complete Node Setup**
   - For new nodes, use "Complete Setup" to install everything at once
   - This includes all prerequisites, MicroK8s, and Longhorn support

### Using the CLI

#### Check Prerequisites
```bash
# Check prerequisites for a specific node
python cli.py check-longhorn-prerequisites --node-id 1

# Check prerequisites for all nodes
python cli.py check-longhorn-prerequisites --all

# Check prerequisites by hostname
python cli.py check-longhorn-prerequisites --hostname node-01
```

#### Install Prerequisites
```bash
# Install prerequisites for a specific node
python cli.py install-longhorn-prerequisites --node-id 1

# Install prerequisites for all nodes
python cli.py install-longhorn-prerequisites --all

# Install prerequisites by hostname
python cli.py install-longhorn-prerequisites --hostname node-01
```

#### Complete Node Setup
```bash
# Setup a new node with all prerequisites and MicroK8s
python cli.py setup-new-node --node-id 1
```

## Manual Verification

After installation, you can manually verify the prerequisites on each node:

### Check Packages
```bash
# Check if required packages are installed
dpkg -l | grep -E "(lvm2|nfs-common|open-iscsi|util-linux)"

# Expected output should show all packages as "ii" (installed)
```

### Check Services
```bash
# Check iSCSI service
systemctl status iscsid

# Check multipath service
systemctl status multipathd

# Both services should be active and enabled
```

### Check Commands
```bash
# Test LVM functionality
lvm version

# Test iSCSI functionality
iscsiadm --version

# Test multipath functionality
multipath -v0
```

## Ansible Playbooks

The orchestrator includes several Ansible playbooks for Longhorn setup:

### `install_longhorn_prerequisites.yml`
- Installs all required packages
- Configures and starts required services
- Sets up iSCSI initiator configuration
- Configures multipath settings
- Verifies installation

### `check_longhorn_prerequisites.yml`
- Checks if all packages are installed
- Verifies service status
- Tests command availability
- Provides detailed status report

### `setup_new_node.yml`
- Complete node setup including:
  - Basic system prerequisites
  - Longhorn prerequisites
  - MicroK8s installation
  - Service configuration
  - Verification

## Troubleshooting

### Common Issues

#### Package Installation Fails
```bash
# Update package cache
sudo apt update

# Install packages manually
sudo apt install lvm2 liblvm2cmd2.03 nfs-common open-iscsi util-linux
```

#### Services Not Starting
```bash
# Check service status
systemctl status iscsid multipathd

# Start services manually
sudo systemctl start iscsid multipathd
sudo systemctl enable iscsid multipathd
```

#### iSCSI Configuration Issues
```bash
# Check iSCSI initiator configuration
cat /etc/iscsi/initiatorname.iscsi

# Regenerate initiator name if needed
sudo iscsiadm -m discovery -t st -p <target_ip>
```

#### Multipath Configuration Issues
```bash
# Check multipath configuration
cat /etc/multipath.conf

# Test multipath functionality
sudo multipath -v0
```

### Log Files

Check these log files for troubleshooting:
- `/var/log/ansible.log` - Ansible operation logs
- `/var/log/syslog` - System logs
- `/tmp/longhorn_prerequisites_report_*.json` - Prerequisites check reports
- `/tmp/node_setup_report_*.json` - Node setup reports

## Integration with MicroK8s

Once prerequisites are installed, you can enable Longhorn in your MicroK8s cluster:

```bash
# Enable Longhorn addon
microk8s enable longhorn

# Check Longhorn status
microk8s kubectl get pods -n longhorn-system

# Access Longhorn UI
microk8s kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80
```

## Best Practices

1. **Pre-install Prerequisites**: Install Longhorn prerequisites before joining nodes to the cluster
2. **Verify Before Joining**: Always check prerequisites before adding nodes to the cluster
3. **Monitor Operations**: Use the Operations page to monitor installation progress
4. **Regular Checks**: Periodically check prerequisites status across all nodes
5. **Backup Configuration**: Keep backups of iSCSI and multipath configurations

## API Endpoints

The orchestrator provides REST API endpoints for programmatic access:

- `POST /api/nodes/{node_id}/check-longhorn-prerequisites` - Check prerequisites
- `POST /api/nodes/{node_id}/install-longhorn-prerequisites` - Install prerequisites
- `POST /api/nodes/{node_id}/setup-new-node` - Complete node setup

## Support

For issues or questions:
1. Check the Operations page for detailed error messages
2. Review the log files mentioned above
3. Use the CLI commands for detailed status information
4. Check the Ansible playbook outputs for specific error details

## Related Documentation

- [MicroK8s Documentation](https://microk8s.io/docs)
- [Longhorn Documentation](https://longhorn.io/docs/)
- [Ansible Documentation](https://docs.ansible.com/)
