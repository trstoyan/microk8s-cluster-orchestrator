# SSH Key Management System

The MicroK8s Cluster Orchestrator now includes a comprehensive SSH key management system that automatically generates unique SSH key pairs for each node and provides step-by-step setup instructions.

## Overview

The SSH key management system provides:

- **Automatic SSH key generation** for each node
- **Unique key pairs** per node for enhanced security
- **Step-by-step setup instructions** for users
- **Connection testing** to verify SSH access
- **Key regeneration** capabilities
- **Integration with Ansible** for cluster operations

## How It Works

### 1. Node Addition Process

When adding a new node, the system:

1. **Generates a unique SSH key pair** (RSA 2048-bit)
2. **Stores the private key** securely on the orchestrator
3. **Provides setup instructions** for adding the public key to the target node
4. **Tracks the setup status** through various stages

### 2. SSH Key Lifecycle

The SSH key goes through several status stages:

- `not_generated` - No SSH key has been created
- `generated` - SSH key pair created, setup required
- `deployed` - Public key added to target node (manual step)
- `tested` - SSH connection successfully tested
- `failed` - SSH connection test failed

### 3. Setup Instructions

The system generates detailed setup instructions that include:

- Commands to add the public key to `~/.ssh/authorized_keys`
- Proper file permissions setup
- Sudo configuration for passwordless access
- Connection testing steps

## Usage

### Web Interface

#### Adding a Node

1. Navigate to **Nodes** → **Add Node**
2. Fill in the node details (hostname, IP address, SSH user, etc.)
3. Click **Add Node**
4. The system will automatically generate an SSH key pair
5. You'll be redirected to the **SSH Setup** page with instructions

#### SSH Setup Page

The SSH setup page provides:

- **Key status** and connection information
- **Copyable public key** for easy setup
- **Step-by-step instructions** for the target node
- **Connection testing** functionality
- **Key regeneration** options

#### Node Management

The nodes list now shows SSH key status:

- 🟢 **Ready** - SSH connection tested and working
- 🟡 **Setup Required** - Key generated, setup needed
- 🔵 **Generated** - Key created, not yet deployed
- ⚫ **Not Generated** - No SSH key created

### Command Line Interface

#### Adding a Node

```bash
# Add a node with automatic SSH key generation (default)
microk8s-cluster node add --hostname node1 --ip 192.168.1.10

# Add a node without SSH key generation
microk8s-cluster node add --hostname node1 --ip 192.168.1.10 --no-generate-ssh-key
```

#### SSH Key Management

```bash
# Test SSH connection to a node
microk8s-cluster node test-ssh 1

# Show SSH key status for a node
microk8s-cluster node ssh-status 1

# Regenerate SSH key for a node
microk8s-cluster node regenerate-ssh-key 1

# Regenerate SSH key without confirmation
microk8s-cluster node regenerate-ssh-key 1 --force
```

## Security Features

### Key Security

- **Unique key pairs** for each node prevent key sharing
- **2048-bit RSA keys** provide strong encryption
- **Secure key storage** with proper file permissions (600)
- **Key fingerprinting** for identification and verification

### Access Control

- **Sudo access testing** ensures proper privileges
- **Connection validation** before cluster operations
- **Key regeneration** for compromised keys
- **Audit trail** of SSH connection tests

## Database Schema

The following fields have been added to the `nodes` table:

```sql
-- SSH Key Management Fields
ssh_key_generated BOOLEAN DEFAULT 0
ssh_public_key TEXT
ssh_key_fingerprint VARCHAR(100)
ssh_key_status VARCHAR(50) DEFAULT "not_generated"
ssh_connection_tested BOOLEAN DEFAULT 0
ssh_connection_test_result TEXT
ssh_setup_instructions TEXT
```

## File Structure

SSH keys are stored in the `ssh_keys/` directory:

```
ssh_keys/
├── node_1_hostname1          # Private key for node 1
├── node_1_hostname1.pub      # Public key for node 1
├── node_2_hostname2          # Private key for node 2
└── node_2_hostname2.pub      # Public key for node 2
```

## Ansible Integration

The SSH key management system integrates seamlessly with Ansible:

- **Automatic inventory generation** uses the generated SSH keys
- **Connection validation** before running playbooks
- **Error reporting** for SSH connection issues
- **Key fingerprint tracking** in inventory files

## Migration

For existing installations, run the migration script:

```bash
python migrations/add_ssh_key_fields.py
```

To rollback the migration:

```bash
python migrations/add_ssh_key_fields.py --rollback
```

## Troubleshooting

### Common Issues

#### SSH Connection Fails

1. **Check setup instructions** - Ensure the public key was added correctly
2. **Verify permissions** - SSH directory and files must have correct permissions
3. **Test manually** - Use the provided SSH command to test manually
4. **Check firewall** - Ensure SSH port (22) is accessible
5. **Regenerate key** - If all else fails, regenerate the SSH key

#### Sudo Access Fails

1. **Check sudoers configuration** - Ensure passwordless sudo is configured
2. **Verify user permissions** - The SSH user must have sudo privileges
3. **Test sudo manually** - SSH to the node and test `sudo -n echo "test"`

#### Key File Not Found

1. **Check key generation** - Ensure the SSH key was generated successfully
2. **Verify file permissions** - Key files must be readable by the orchestrator
3. **Regenerate key** - If the key file is missing, regenerate it

### Debug Commands

```bash
# Show detailed SSH status
microk8s-cluster node ssh-status 1

# Test SSH connection with verbose output
ssh -i /path/to/private/key -v user@hostname

# Check SSH key fingerprint
ssh-keygen -lf /path/to/public/key.pub
```

## Best Practices

### Security

- **Regular key rotation** - Regenerate SSH keys periodically
- **Monitor access logs** - Check SSH access logs on target nodes
- **Limit key scope** - Each node should have its own unique key
- **Secure key storage** - Protect the orchestrator system

### Operations

- **Test connections** before cluster operations
- **Keep setup instructions** for reference
- **Monitor SSH key status** in the web interface
- **Document key fingerprints** for verification

### Maintenance

- **Clean up old keys** when nodes are removed
- **Backup key files** before major updates
- **Monitor disk space** for key storage
- **Update documentation** when procedures change

## API Reference

### SSH Key Manager Service

The `SSHKeyManager` class provides the core functionality:

```python
from app.services.ssh_key_manager import SSHKeyManager

ssh_manager = SSHKeyManager()

# Generate key pair
key_info = ssh_manager.generate_key_pair(node_id, hostname)

# Test connection
result = ssh_manager.validate_ssh_connection(hostname, ip, user, port, key_path)

# Get setup instructions
instructions = ssh_manager.get_setup_instructions(hostname, public_key, user)

# Clean up keys
ssh_manager.cleanup_key_pair(private_key_path)
```

### Node Model Properties

The `Node` model includes SSH key properties:

```python
node.ssh_key_ready          # Boolean: Key is ready for use
node.ssh_connection_ready   # Boolean: Connection is tested and working
node.get_ssh_status_description()  # Human-readable status
```

## Future Enhancements

Planned improvements to the SSH key management system:

- **Key rotation automation** - Automatic periodic key regeneration
- **Certificate-based authentication** - Support for SSH certificates
- **Key escrow** - Secure key backup and recovery
- **Integration with external key management** - Support for HashiCorp Vault, etc.
- **Audit logging** - Comprehensive SSH access logging
- **Multi-factor authentication** - Support for 2FA/OTP
