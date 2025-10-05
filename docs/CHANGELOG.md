# Changelog

All notable changes to the MicroK8s Cluster Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SSH Key Management System**: Comprehensive SSH key management with automatic generation
  - Automatic generation of unique RSA 2048-bit SSH key pairs for each node
  - Secure storage of private keys with proper file permissions (600)
  - Step-by-step setup instructions for adding public keys to target nodes
  - SSH connection testing with sudo access validation
  - Key regeneration capabilities for compromised or lost keys
  - Visual SSH key status indicators in the web interface
  - Integration with Ansible inventory generation
  - CLI commands for SSH key management (`test-ssh`, `ssh-status`, `regenerate-ssh-key`)

### Enhanced
- **Node Addition Workflow**: Streamlined node addition with automatic SSH key generation
  - Removed manual SSH key path requirement
  - Automatic redirect to SSH setup page after node creation
  - Clear setup instructions provided to users
  - Integration with existing node management workflow

- **Web Interface**: Enhanced with SSH key management features
  - New SSH setup page for each node with detailed instructions
  - SSH key status column in the nodes list
  - Copy-to-clipboard functionality for public keys
  - Connection testing with real-time feedback
  - Key regeneration with confirmation dialogs

- **CLI Interface**: Extended with SSH key management commands
  - `node test-ssh <node_id>` - Test SSH connection to a node
  - `node ssh-status <node_id>` - Show detailed SSH key status
  - `node regenerate-ssh-key <node_id>` - Regenerate SSH key for a node
  - Enhanced `node add` command with automatic SSH key generation

- **Database Schema**: Added SSH key management fields to nodes table
  - `ssh_key_generated` - Boolean indicating if SSH key pair has been generated
  - `ssh_public_key` - Text field containing the public key content
  - `ssh_key_fingerprint` - String field for key fingerprint identification
  - `ssh_key_status` - String field for key status tracking
  - `ssh_connection_tested` - Boolean indicating if SSH connection has been tested
  - `ssh_connection_test_result` - Text field for last SSH connection test result
  - `ssh_setup_instructions` - Text field for setup instructions

- **Ansible Integration**: Enhanced inventory generation with SSH key validation
  - SSH connection validation before running playbooks
  - Enhanced error reporting for SSH connection issues
  - Key fingerprint tracking in inventory files
  - Automatic exclusion of nodes with SSH connection issues

### Security
- **Enhanced SSH Security**: Improved SSH authentication security
  - Unique SSH key pairs per node prevent key sharing
  - Secure key storage with proper file permissions
  - Key fingerprinting for identification and verification
  - Connection validation with sudo access testing
  - Audit trail of SSH connection tests

### Documentation
- **Comprehensive Documentation**: Added detailed SSH key management documentation
  - Complete SSH key management guide (`docs/SSH_KEY_MANAGEMENT.md`)
  - Updated README with SSH key management features
  - Migration guide for existing installations
  - Troubleshooting section with common issues and solutions
  - API reference for developers
  - Best practices for security and operations

### Migration
- **Database Migration**: Added migration script for existing installations
  - `migrations/add_ssh_key_fields.py` - Adds SSH key fields to existing databases
  - Rollback capability for safe migration management
  - Backward compatibility with existing installations

## [Previous Versions]

### [1.0.0] - 2024-01-XX

#### Added
- **Core System**: Initial release of MicroK8s Cluster Orchestrator
- **Node Management**: Add, remove, and monitor cluster nodes
- **Cluster Orchestration**: Automated cluster setup, configuration, and graceful shutdown
- **Ansible Integration**: Uses Ansible playbooks for all operations
- **SQLite Database**: Persistent storage for cluster state and history
- **Web Interface**: Modern web UI for cluster management
- **CLI Tool**: Command-line interface for automation and scripting
- **Operation Tracking**: Complete audit trail of all operations
- **Health Monitoring**: Automated health checks and status monitoring
- **Troubleshooting**: Built-in diagnostics and troubleshooting tools

#### Hardware Reporting System
- **Automatic Detection**: Discovers all hardware components automatically
- **Detailed Information**: Collects comprehensive data about CPUs, memory, storage, network, and more
- **Real-time Updates**: Hardware information is collected on-demand or scheduled
- **Web Interface**: Beautiful, responsive web interface for viewing hardware reports
- **API Access**: REST API endpoints for programmatic access to hardware data

#### UPS Power Management System
- **USB UPS Detection**: Automatically detects and configures USB-connected UPS devices
- **NUT Integration**: Uses Network UPS Tools (NUT) for UPS communication and control
- **Power Event Monitoring**: Monitors power loss, low battery, and power restoration events
- **Automated Cluster Management**: Executes configurable actions on clusters based on power events
- **Real-time Status Monitoring**: Tracks battery charge, voltage, load, and temperature
- **Rule-based Configuration**: Flexible power management rules with priority-based execution
- **Web Interface**: Complete web-based management interface for UPS devices and rules
- **CLI and API Support**: Full command-line and REST API access to all UPS functions

#### Features
- **Wake-on-LAN Support**: Configure and manage Wake-on-LAN for cluster nodes
- **Hardware Information Collection**: Comprehensive hardware reporting system
- **Network Topology Visualization**: Visual representation of network connections
- **Router/Switch Management**: Integration with network infrastructure
- **Power Management**: UPS integration for Raspberry Pi deployments
- **Privilege Management**: Automated setup of required system privileges
- **Configuration Management**: Flexible YAML-based configuration system

#### Security
- **SQLite Database**: Excluded from version control for security
- **SSH Key Management**: Secure storage of SSH keys with proper permissions
- **Configuration Security**: Environment-specific settings support
- **Data Encryption**: Support for encrypting sensitive data in the database

#### Development
- **Modular Architecture**: Clear separation of concerns with modular design
- **Turing Complete**: Fully programmable and extensible system
- **Infrastructure Agnostic**: Works with any infrastructure that supports SSH
- **Persistent State**: All state and history stored in SQLite database

---

## Version History

### Version 1.1.0 (Unreleased)
- **Major Feature**: SSH Key Management System
- **Enhancement**: Streamlined node addition workflow
- **Security**: Enhanced SSH authentication security
- **Documentation**: Comprehensive SSH key management documentation

### Version 1.0.0 (Initial Release)
- **Core System**: Complete MicroK8s cluster orchestration system
- **Hardware Reporting**: Comprehensive hardware information collection
- **UPS Management**: Power management for Raspberry Pi deployments
- **Web Interface**: Modern web UI for cluster management
- **CLI Tools**: Command-line interface for automation

---

## Migration Guide

### From Version 1.0.0 to 1.1.0

#### Database Migration
Run the migration script to add SSH key management fields:

```bash
python migrations/add_ssh_key_fields.py
```

#### Configuration Updates
No configuration changes required. The system will automatically use the new SSH key management features.

#### Breaking Changes
- **Node Addition**: The `--key-path` parameter is no longer required for `node add` command
- **SSH Key Storage**: SSH keys are now stored in the `ssh_keys/` directory instead of user-specified locations

#### New Features
- **Automatic SSH Key Generation**: SSH keys are now generated automatically when adding nodes
- **SSH Setup Instructions**: Users receive detailed setup instructions for each node
- **Connection Testing**: Built-in SSH connection testing and validation
- **Key Regeneration**: Easy key regeneration for compromised keys

---

## Support

For support with the SSH Key Management System:

1. **Check Documentation**: Review `docs/SSH_KEY_MANAGEMENT.md` for detailed information
2. **Run Migration**: Ensure database migration has been completed
3. **Check Logs**: Review operation logs for detailed error information
4. **Test Connections**: Use the built-in connection testing tools
5. **Regenerate Keys**: If issues persist, regenerate SSH keys for affected nodes

For general support:
- Check operation logs for detailed error information
- Review the troubleshooting playbooks
- Create issues in the repository for bugs or feature requests