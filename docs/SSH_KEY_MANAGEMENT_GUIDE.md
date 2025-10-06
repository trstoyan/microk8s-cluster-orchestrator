# SSH Key Management Guide

This guide covers the automated SSH key management functionality integrated into the MicroK8s Cluster Orchestrator, which provides secure, automated SSH key generation and management for cluster nodes.

## Overview

The SSH Key Management system automates the creation, distribution, and validation of SSH key pairs for secure communication with cluster nodes. This eliminates the need for manual SSH key management and provides a streamlined workflow for node setup and management.

## Features

### Core Functionality
- **Automatic Key Generation**: SSH key pairs are automatically generated when adding new nodes
- **Secure Key Storage**: Private keys are stored securely on the orchestrator server
- **Setup Instructions**: Automated generation of setup instructions for target nodes
- **Connection Testing**: Built-in SSH connection validation and testing
- **Key Regeneration**: Ability to regenerate SSH keys when needed
- **Fingerprint Tracking**: SHA256 fingerprints for key validation and security

### Security Features
- **RSA 4096-bit Keys**: Strong cryptographic keys for maximum security
- **Secure File Permissions**: Proper file permissions on private keys (600)
- **Fingerprint Validation**: SHA256 fingerprints for key verification
- **Connection Validation**: Comprehensive SSH connection testing
- **Key Rotation**: Support for key regeneration and rotation

## Workflow

### Node Addition Workflow

When adding a new node, the system follows this automated workflow:

1. **Node Creation**: Node record is created in the database
2. **Key Generation**: SSH key pair is automatically generated
3. **Key Storage**: Private key is stored securely on the orchestrator
4. **Setup Instructions**: Instructions are generated for the target node
5. **User Guidance**: User is redirected to setup instructions page
6. **Connection Testing**: User can test the SSH connection
7. **Validation**: System validates the connection is working

### SSH Setup Instructions

The system generates comprehensive setup instructions for each node:

```bash
# SSH Key Setup Instructions for node-hostname
# 
# 1. Create .ssh directory (if it doesn't exist):
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. Add the public key to authorized_keys:
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC... user@orchestrator" >> ~/.ssh/authorized_keys

# 3. Set proper permissions:
chmod 600 ~/.ssh/authorized_keys

# 4. Verify the setup:
chmod 600 ~/.ssh/authorized_keys
```

## Configuration

### Node SSH Fields

Each node stores the following SSH-related information:

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `ssh_user` | SSH username | String | `ubuntu` |
| `ssh_port` | SSH port | Integer | `22` |
| `ssh_key_path` | Path to private key file | String | `/path/to/private.key` |
| `ssh_public_key` | Public key content | Text | `ssh-rsa AAAAB3NzaC1yc2E...` |
| `ssh_key_fingerprint` | SHA256 fingerprint | String | `SHA256:abc123...` |
| `ssh_key_generated` | Key generation status | Boolean | `true` |
| `ssh_key_status` | Current key status | String | `generated`, `tested`, `failed` |
| `ssh_connection_tested` | Connection test status | Boolean | `true` |
| `ssh_connection_test_result` | Test results (JSON) | Text | `{"success": true, ...}` |
| `ssh_setup_instructions` | Setup instructions | Text | Generated instructions |

### SSH Key Status Levels

- **Generated**: SSH key has been created and is ready for setup
- **Tested**: SSH connection has been successfully tested
- **Failed**: SSH connection test failed

## Usage

### Web Interface

#### Adding a New Node

1. Navigate to the **Nodes** page
2. Click **Add Node**
3. Fill in the node information:
   - Hostname
   - IP Address
   - SSH User (default: ubuntu)
   - SSH Port (default: 22)
   - Cluster assignment (optional)
4. Click **Add Node**
5. The system will automatically generate SSH keys
6. You'll be redirected to the SSH setup page

#### SSH Setup Page

The SSH setup page provides:

1. **Setup Instructions**: Step-by-step instructions for the target node
2. **Public Key Display**: The public key that needs to be added to the node
3. **Connection Testing**: Button to test the SSH connection
4. **Key Regeneration**: Option to regenerate SSH keys if needed

#### Testing SSH Connection

1. Follow the setup instructions on the target node
2. Return to the SSH setup page
3. Click **Test SSH Connection**
4. The system will attempt to connect and validate the setup
5. Success/failure status will be displayed

### CLI Commands

#### Node Management with SSH

```bash
# Add a node (SSH keys will be generated automatically)
python cli.py nodes add --hostname node1 --ip 192.168.1.10 --ssh-user ubuntu

# Test SSH connection for a specific node
python cli.py nodes test-ssh <node_id>

# Regenerate SSH keys for a node
python cli.py nodes regenerate-ssh <node_id>

# Get SSH setup instructions
python cli.py nodes ssh-instructions <node_id>
```

#### SSH Key Management

```bash
# List all SSH keys
python cli.py ssh list-keys

# Generate SSH key for specific node
python cli.py ssh generate-key <node_id>

# Test SSH connection
python cli.py ssh test-connection <node_id>

# Validate SSH key fingerprint
python cli.py ssh validate-fingerprint <node_id>
```

### REST API

#### Node SSH Management

```bash
# Test SSH connection
POST /api/nodes/{node_id}/test-ssh
Content-Type: application/json
{}

# Regenerate SSH key
POST /api/nodes/{node_id}/regenerate-ssh-key
Content-Type: application/json
{}

# Get SSH setup instructions
GET /api/nodes/{node_id}/ssh-instructions
```

#### SSH Key Information

```bash
# Get SSH key information
GET /api/nodes/{node_id}/ssh-key-info

# Validate SSH key
POST /api/nodes/{node_id}/validate-ssh-key
Content-Type: application/json
{
  "fingerprint": "SHA256:abc123..."
}
```

## SSH Server Configuration

### Required SSH Server Settings

For secure key-based authentication, the SSH server on target nodes must be properly configured. The system generates instructions that include these essential settings:

#### Essential Configuration (`/etc/ssh/sshd_config`)

```bash
# Enable public key authentication
PubkeyAuthentication yes

# Disable password authentication (recommended for security)
PasswordAuthentication no

# Ensure authorized keys file is set correctly
AuthorizedKeysFile .ssh/authorized_keys

# Disable root login (additional security)
PermitRootLogin no

# Optional: Change SSH port for additional security
# Port 2222
```

#### Configuration Process

1. **Before Adding Keys**: Configure SSH server settings first
2. **Add Public Key**: Add the generated public key to `~/.ssh/authorized_keys`
3. **Test Connection**: Verify key authentication works
4. **Disable Passwords**: Set `PasswordAuthentication no` for security
5. **Restart SSH**: Apply configuration changes

#### Security Warning

⚠️ **Important**: Always test key authentication before disabling password authentication to avoid being locked out of the system.

## Security Considerations

### Key Security

1. **Private Key Protection**:
   - Private keys are stored with 600 permissions (owner read/write only)
   - Keys are stored in a secure directory structure
   - Access is restricted to the orchestrator application

2. **Public Key Distribution**:
   - Public keys are embedded in setup instructions
   - Users must manually add public keys to target nodes
   - No automatic key distribution to prevent security risks

3. **Key Validation**:
   - SHA256 fingerprints are generated and stored
   - Connection testing validates key authenticity
   - Fingerprint verification prevents key tampering

4. **Server Security**:
   - Password authentication is disabled after key setup
   - Root login is disabled for additional security
   - SSH service is properly configured for key-only access

### Best Practices

1. **Key Rotation**: Regularly regenerate SSH keys for security
2. **Access Control**: Limit access to the orchestrator server
3. **Network Security**: Use secure networks for SSH connections
4. **Monitoring**: Monitor SSH connection logs for unusual activity
5. **Backup**: Backup SSH keys securely (encrypted)

### Security Recommendations

1. **Use Strong Keys**: The system generates 4096-bit RSA keys by default
2. **Regular Rotation**: Consider implementing key rotation policies
3. **Network Isolation**: Use VPNs or isolated networks for SSH access
4. **Logging**: Enable SSH logging on target nodes for audit trails
5. **Firewall Rules**: Restrict SSH access to necessary IP ranges only

## Troubleshooting

### Common Issues

#### SSH Connection Failures

1. **Check Network Connectivity**:
   ```bash
   ping <node_ip>
   telnet <node_ip> 22
   ```

2. **Verify SSH Service**:
   ```bash
   # On target node
   sudo systemctl status ssh
   sudo systemctl start ssh
   ```

3. **Check SSH Configuration**:
   ```bash
   # On target node
   sudo nano /etc/ssh/sshd_config
   # Ensure: PubkeyAuthentication yes
   # Ensure: AuthorizedKeysFile .ssh/authorized_keys
   # Ensure: PasswordAuthentication no (for security)
   # Ensure: PermitRootLogin no (for security)
   ```

4. **Validate Key Setup**:
   ```bash
   # On target node
   ls -la ~/.ssh/
   cat ~/.ssh/authorized_keys
   ```

#### Permission Issues

1. **Check Directory Permissions**:
   ```bash
   # On target node
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

2. **Check File Ownership**:
   ```bash
   # On target node
   chown -R $USER:$USER ~/.ssh/
   ```

#### Key Generation Issues

1. **Check Disk Space**:
   ```bash
   df -h
   ```

2. **Check Permissions**:
   ```bash
   # On orchestrator server
   ls -la /path/to/ssh/keys/
   ```

3. **Check SSH Key Manager Logs**:
   ```bash
   # Check application logs
   tail -f logs/app.log
   ```

### Debug Commands

```bash
# Test SSH connection with verbose output
ssh -v -i /path/to/private.key user@hostname

# Check SSH key fingerprint
ssh-keygen -lf /path/to/public.key

# Validate SSH configuration
ssh -T git@github.com  # Test SSH to known host

# Check SSH agent
ssh-add -l
```

### Log Analysis

Check the following log files for SSH-related issues:

1. **Application Logs**: `logs/app.log`
2. **SSH Logs on Target Node**: `/var/log/auth.log`
3. **System Logs**: `/var/log/syslog`

## Integration with Other Systems

### Ansible Integration

SSH keys generated by the system can be used with Ansible:

```bash
# Use generated SSH key with Ansible
ansible-playbook -i inventory/hosts playbook.yml \
  --private-key=/path/to/generated/private.key \
  --user=ubuntu
```

### CI/CD Integration

SSH keys can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Setup SSH
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    ssh-add ~/.ssh/id_rsa
```

### Monitoring Integration

SSH connection status can be monitored:

```bash
# Check SSH connection status
curl -X GET http://orchestrator:5000/api/nodes/1/ssh-status

# Monitor SSH health
python cli.py ssh health-check --all-nodes
```

## Performance Considerations

### Key Generation Performance

- **RSA 4096-bit Key Generation**: Takes 2-5 seconds per key
- **Concurrent Generation**: Multiple keys can be generated simultaneously
- **Storage Requirements**: ~3KB per key pair

### Connection Testing Performance

- **Connection Timeout**: 10 seconds default timeout
- **Retry Logic**: 3 attempts with exponential backoff
- **Parallel Testing**: Multiple connections can be tested simultaneously

### Scalability

- **Key Storage**: Efficient file-based storage scales to thousands of keys
- **Database Queries**: Optimized queries for key status and metadata
- **Memory Usage**: Minimal memory footprint for key management

## Future Enhancements

### Planned Features

1. **Key Rotation Policies**: Automated key rotation based on age or security policies
2. **Multiple Key Support**: Support for multiple SSH keys per node
3. **Key Distribution**: Automated key distribution for trusted environments
4. **SSH Key Templates**: Configurable key types and parameters
5. **Integration with External Key Stores**: Support for HashiCorp Vault, AWS KMS, etc.

### Advanced Security Features

1. **Hardware Security Module (HSM) Integration**: Use HSMs for key generation and storage
2. **Certificate-based Authentication**: Support for SSH certificates
3. **Multi-factor Authentication**: Integration with MFA systems
4. **Audit Logging**: Comprehensive audit trails for all SSH operations
5. **Compliance Reporting**: Built-in compliance reporting for security audits

## Support and Contributing

### Getting Help

- Check the troubleshooting section above
- Review SSH logs on both orchestrator and target nodes
- Consult SSH documentation for configuration issues
- Submit issues through the project's issue tracker

### Contributing

Areas where contributions would be valuable:

1. **Additional Key Types**: Support for Ed25519, ECDSA keys
2. **Enhanced Security**: Integration with external security systems
3. **Performance Improvements**: Optimized key generation and storage
4. **Additional Integrations**: Support for more automation tools
5. **Enhanced Monitoring**: Better monitoring and alerting capabilities

---

For more information about the MicroK8s Cluster Orchestrator, see the main [README.md](../README.md) file.
