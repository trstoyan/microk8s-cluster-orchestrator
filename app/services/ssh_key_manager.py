"""SSH Key Management Service for MicroK8s Cluster Orchestrator."""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64
import hashlib

logger = logging.getLogger(__name__)

class SSHKeyManager:
    """Manages SSH key generation, storage, and validation for cluster nodes."""
    
    def __init__(self, keys_directory: str = "ssh_keys"):
        """
        Initialize SSH Key Manager.
        
        Args:
            keys_directory: Directory to store SSH keys
        """
        self.keys_directory = Path(keys_directory)
        self.keys_directory.mkdir(exist_ok=True)
        
        # Ensure proper permissions on keys directory
        os.chmod(self.keys_directory, 0o700)
    
    def generate_key_pair(self, node_id: int, node_hostname: str) -> Dict[str, str]:
        """
        Generate a new SSH key pair for a node.
        
        Args:
            node_id: Unique node identifier
            node_hostname: Node hostname for key naming
            
        Returns:
            Dictionary containing key information
        """
        try:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Get public key
            public_key = private_key.public_key()
            public_ssh = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
            
            # Create key file names
            key_name = f"node_{node_id}_{node_hostname}"
            private_key_path = self.keys_directory / f"{key_name}"
            public_key_path = self.keys_directory / f"{key_name}.pub"
            
            # Write private key
            with open(private_key_path, 'wb') as f:
                f.write(private_pem)
            os.chmod(private_key_path, 0o600)
            
            # Write public key
            with open(public_key_path, 'wb') as f:
                f.write(public_ssh)
            os.chmod(public_key_path, 0o644)
            
            # Generate key fingerprint
            fingerprint = self._generate_fingerprint(public_ssh.decode())
            
            logger.info(f"Generated SSH key pair for node {node_hostname} (ID: {node_id})")
            
            # Return ABSOLUTE paths so they work regardless of working directory
            return {
                'private_key_path': str(private_key_path.absolute()),
                'public_key_path': str(public_key_path.absolute()),
                'public_key': public_ssh.decode().strip(),
                'fingerprint': fingerprint,
                'key_name': key_name,
                'key_type': 'rsa',
                'key_size': 2048
            }
            
        except Exception as e:
            logger.error(f"Failed to generate SSH key pair for node {node_hostname}: {e}")
            raise
    
    def _generate_fingerprint(self, public_key: str) -> str:
        """Generate MD5 fingerprint of public key."""
        try:
            # Remove key type and comment, keep only the key data
            key_parts = public_key.split()
            if len(key_parts) >= 2:
                key_data = key_parts[1]
                key_bytes = base64.b64decode(key_data)
                md5_hash = hashlib.md5(key_bytes).hexdigest()
                return ':'.join(md5_hash[i:i+2] for i in range(0, len(md5_hash), 2))
        except Exception as e:
            logger.warning(f"Failed to generate fingerprint: {e}")
        return "unknown"
    
    def validate_ssh_connection(self, hostname: str, ip_address: str, ssh_user: str, 
                              ssh_port: int, private_key_path: str, 
                              timeout: int = 30) -> Dict[str, any]:
        """
        Test SSH connection to a node.
        
        Args:
            hostname: Node hostname
            ip_address: Node IP address
            ssh_user: SSH username
            ssh_port: SSH port
            private_key_path: Path to private key
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with connection test results
        """
        try:
            # Prepare SSH command
            ssh_cmd = [
                'ssh',
                '-i', private_key_path,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',
                '-p', str(ssh_port),
                f'{ssh_user}@{ip_address}',
                'echo "SSH connection successful"'
            ]
            
            # Test connection
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                # Test sudo access
                sudo_cmd = [
                    'ssh',
                    '-i', private_key_path,
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'ConnectTimeout=10',
                    '-o', 'BatchMode=yes',
                    '-p', str(ssh_port),
                    f'{ssh_user}@{ip_address}',
                    'sudo -n echo "Sudo access confirmed"'
                ]
                
                sudo_result = subprocess.run(
                    sudo_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    'success': True,
                    'ssh_connection': True,
                    'sudo_access': sudo_result.returncode == 0,
                    'message': 'SSH connection successful',
                    'sudo_message': 'Sudo access confirmed' if sudo_result.returncode == 0 else 'Sudo access failed'
                }
            else:
                return {
                    'success': False,
                    'ssh_connection': False,
                    'sudo_access': False,
                    'message': f'SSH connection failed: {result.stderr}',
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'ssh_connection': False,
                'sudo_access': False,
                'message': 'SSH connection timed out',
                'error': 'Connection timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'ssh_connection': False,
                'sudo_access': False,
                'message': f'SSH connection test failed: {str(e)}',
                'error': str(e)
            }
    
    def get_setup_instructions(self, node_hostname: str, public_key: str, 
                             ssh_user: str = 'ubuntu') -> str:
        """
        Generate setup instructions for adding the public key to a node.
        
        Args:
            node_hostname: Node hostname
            public_key: Public key content
            ssh_user: SSH username
            
        Returns:
            Formatted setup instructions
        """
        instructions = f"""
# SSH Key Setup Instructions for Node: {node_hostname}

## Step 1: Connect to the node
SSH into the target node using your current credentials:
```bash
ssh {ssh_user}@<NODE_IP_ADDRESS>
```

## Step 2: Configure SSH server for key-based authentication
**IMPORTANT**: Configure the SSH server before adding the key to ensure security:

```bash
# Edit SSH server configuration
sudo nano /etc/ssh/sshd_config
```

Add or modify the following settings:
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

Save the file and restart SSH service:
```bash
sudo systemctl restart ssh
# or on some systems:
sudo systemctl restart sshd
```

**⚠️ SECURITY WARNING**: Before restarting SSH, ensure you have:
1. Added the public key (Step 3) AND tested it (Step 6)
2. Or kept PasswordAuthentication yes until key authentication is confirmed

## Step 3: Add the public key to authorized_keys
Run the following command on the target node:
```bash
mkdir -p ~/.ssh
echo "{public_key}" >> ~/.ssh/authorized_keys
```

## Step 4: Set proper permissions
Ensure the SSH directory and files have correct permissions:
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## Step 5: Configure passwordless sudo (if not already configured)
Add the following line to /etc/sudoers.d/{ssh_user} (create the file if it doesn't exist):
```bash
{ssh_user} ALL=(ALL) NOPASSWD:ALL
```

## Step 6: Test key authentication BEFORE disabling passwords
Open a NEW terminal and test the SSH key connection:
```bash
# Test from the orchestrator (replace <NODE_IP_ADDRESS> with actual IP)
ssh -i <PRIVATE_KEY_PATH> {ssh_user}@<NODE_IP_ADDRESS>
```

If the test is successful, you can now safely disable password authentication:
```bash
# Edit SSH config again
sudo nano /etc/ssh/sshd_config

# Set PasswordAuthentication to no
PasswordAuthentication no

# Restart SSH service
sudo systemctl restart ssh
```

## Step 7: Final verification
Test the connection from the orchestrator:
```bash
# The orchestrator will automatically test the connection
# You can also test manually:
ssh -i <PRIVATE_KEY_PATH> {ssh_user}@<NODE_IP_ADDRESS>
```

## Security Notes:
- The private key is stored securely on the orchestrator
- Only the public key needs to be added to the target node
- The key is unique to this node and should not be shared
- Keep the private key secure and never share it
- Disabling password authentication prevents brute force attacks
- Always test key authentication before disabling passwords

## Troubleshooting:
- If connection fails, check that the public key was added correctly
- Ensure SSH service is running on the target node
- Verify firewall settings allow SSH connections
- Check that the SSH user has the correct permissions
- If locked out, access via console and re-enable PasswordAuthentication yes
- Verify sshd_config syntax: `sudo sshd -t`
"""
        return instructions.strip()
    
    def cleanup_key_pair(self, private_key_path: str) -> bool:
        """
        Remove SSH key pair files.
        
        Args:
            private_key_path: Path to private key file
            
        Returns:
            True if cleanup was successful
        """
        try:
            private_path = Path(private_key_path)
            public_path = private_path.with_suffix('.pub')
            
            # Remove private key
            if private_path.exists():
                private_path.unlink()
            
            # Remove public key
            if public_path.exists():
                public_path.unlink()
            
            logger.info(f"Cleaned up SSH key pair: {private_key_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup SSH key pair {private_key_path}: {e}")
            return False
    
    def list_key_pairs(self) -> List[Dict[str, str]]:
        """
        List all SSH key pairs in the keys directory.
        
        Returns:
            List of key pair information
        """
        keys = []
        try:
            for key_file in self.keys_directory.glob("node_*"):
                if not key_file.name.endswith('.pub'):
                    public_key_file = key_file.with_suffix('.pub')
                    if public_key_file.exists():
                        with open(public_key_file, 'r') as f:
                            public_key = f.read().strip()
                        
                        keys.append({
                            'private_key_path': str(key_file),
                            'public_key_path': str(public_key_file),
                            'public_key': public_key,
                            'fingerprint': self._generate_fingerprint(public_key),
                            'key_name': key_file.name,
                            'created': key_file.stat().st_mtime
                        })
        except Exception as e:
            logger.error(f"Failed to list SSH key pairs: {e}")
        
        return keys
    
    def get_key_info(self, private_key_path: str) -> Optional[Dict[str, str]]:
        """
        Get information about a specific SSH key pair.
        
        Args:
            private_key_path: Path to private key file
            
        Returns:
            Key information dictionary or None if not found
        """
        try:
            private_path = Path(private_key_path)
            public_path = private_path.with_suffix('.pub')
            
            if not private_path.exists() or not public_path.exists():
                return None
            
            with open(public_path, 'r') as f:
                public_key = f.read().strip()
            
            return {
                'private_key_path': str(private_path),
                'public_key_path': str(public_path),
                'public_key': public_key,
                'fingerprint': self._generate_fingerprint(public_key),
                'key_name': private_path.name,
                'created': private_path.stat().st_mtime,
                'size': private_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get key info for {private_key_path}: {e}")
            return None
