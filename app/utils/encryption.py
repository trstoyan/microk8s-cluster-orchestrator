"""
Encryption utilities for secure data transfer
Provides AES-256 encryption for sync operations
"""

import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets


class SyncEncryption:
    """Handle encryption/decryption for sync operations"""
    
    def __init__(self, password: str = None):
        """
        Initialize encryption with password
        
        Args:
            password: Optional password for encryption. If None, generates one.
        """
        if password is None:
            password = secrets.token_urlsafe(32)
        
        self.password = password
        self.salt = None
        self.fernet = None
    
    def generate_key(self, salt: bytes = None) -> bytes:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        self.salt = salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        self.fernet = Fernet(key)
        return key
    
    def encrypt(self, data: dict) -> dict:
        """
        Encrypt dictionary data
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Dictionary with encrypted payload and salt
        """
        if self.fernet is None:
            self.generate_key()
        
        # Convert dict to JSON string
        json_data = json.dumps(data)
        
        # Encrypt
        encrypted = self.fernet.encrypt(json_data.encode())
        
        return {
            'payload': base64.b64encode(encrypted).decode(),
            'salt': base64.b64encode(self.salt).decode()
        }
    
    def decrypt(self, encrypted_data: dict) -> dict:
        """
        Decrypt encrypted data
        
        Args:
            encrypted_data: Dictionary with payload and salt
            
        Returns:
            Decrypted dictionary
        """
        # Extract salt and regenerate key
        salt = base64.b64decode(encrypted_data['salt'])
        self.generate_key(salt)
        
        # Decrypt payload
        encrypted_payload = base64.b64decode(encrypted_data['payload'])
        decrypted = self.fernet.decrypt(encrypted_payload)
        
        # Convert back to dict
        return json.loads(decrypted.decode())
    
    def encrypt_file(self, file_path: str, output_path: str = None):
        """Encrypt a file"""
        if self.fernet is None:
            self.generate_key()
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted = self.fernet.encrypt(data)
        
        if output_path is None:
            output_path = f"{file_path}.encrypted"
        
        with open(output_path, 'wb') as f:
            f.write(self.salt + encrypted)
        
        return output_path
    
    def decrypt_file(self, file_path: str, output_path: str = None):
        """Decrypt a file"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Extract salt (first 16 bytes)
        salt = data[:16]
        encrypted_data = data[16:]
        
        # Regenerate key with salt
        self.generate_key(salt)
        
        # Decrypt
        decrypted = self.fernet.decrypt(encrypted_data)
        
        if output_path is None:
            output_path = file_path.replace('.encrypted', '')
        
        with open(output_path, 'wb') as f:
            f.write(decrypted)
        
        return output_path
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for authentication"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return f"mko_{secrets.token_urlsafe(48)}"


class SyncToken:
    """Manage sync tokens for authentication with JWT and single-use support"""
    
    def __init__(self):
        self.tokens = {}  # In production, use Redis or database
        self.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
    
    def create_token(self, server_id: str, expires_in: int = 3600, max_uses: int = 1) -> str:
        """
        Create a new JWT sync token with usage tracking
        
        Args:
            server_id: Identifier for the server
            expires_in: Token expiration time in seconds (default 1 hour)
            max_uses: Maximum times token can be used (default 1 = single-use)
            
        Returns:
            JWT token string
        """
        import time
        import jwt
        
        token_id = secrets.token_urlsafe(16)
        expires_at = time.time() + expires_in
        
        # JWT payload
        payload = {
            'token_id': token_id,
            'server_id': server_id,
            'expires_at': expires_at,
            'iat': time.time(),
            'type': 'sync'
        }
        
        # Generate JWT
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        # Store token metadata for usage tracking
        self.tokens[token_id] = {
            'server_id': server_id,
            'expires_at': expires_at,
            'max_uses': max_uses,
            'uses': 0,
            'revoked': False,
            'created_at': time.time()
        }
        
        return token
    
    def validate_token(self, token: str) -> bool:
        """
        Validate token and increment use counter
        
        Returns:
            True if valid, False otherwise
        """
        import time
        import jwt
        
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if not token_id or token_id not in self.tokens:
                return False
            
            token_info = self.tokens[token_id]
            
            # Check if revoked
            if token_info['revoked']:
                return False
            
            # Check expiration
            if time.time() > token_info['expires_at']:
                # Auto-cleanup expired token
                del self.tokens[token_id]
                return False
            
            # Check usage limit
            if token_info['uses'] >= token_info['max_uses']:
                return False
            
            # Increment use counter
            token_info['uses'] += 1
            token_info['last_used'] = time.time()
            
            # Auto-revoke if max uses reached
            if token_info['uses'] >= token_info['max_uses']:
                token_info['revoked'] = True
            
            return True
            
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
        except Exception:
            return False
    
    def revoke_token(self, token: str) -> bool:
        """
        Manually revoke a token
        
        Returns:
            True if revoked, False if not found
        """
        import jwt
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if token_id in self.tokens:
                self.tokens[token_id]['revoked'] = True
                return True
        except:
            pass
        return False
    
    def get_token_info(self, token: str) -> dict:
        """
        Get metadata about a token
        
        Returns:
            Token info dict or None if not found
        """
        import jwt
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if token_id in self.tokens:
                info = self.tokens[token_id].copy()
                info['token_id'] = token_id
                info['server_id'] = payload.get('server_id')
                return info
        except:
            pass
        return None


if __name__ == '__main__':
    # Test encryption
    print("🔐 Testing Encryption Utilities\n")
    
    # Test data encryption
    enc = SyncEncryption("test_password_123")
    
    test_data = {
        'nodes': ['node1', 'node2'],
        'clusters': ['production', 'staging'],
        'sensitive': 'secret_data'
    }
    
    print("Original data:", test_data)
    
    encrypted = enc.encrypt(test_data)
    print("\nEncrypted:", encrypted['payload'][:50] + "...")
    
    decrypted = enc.decrypt(encrypted)
    print("\nDecrypted:", decrypted)
    
    print("\n✅ Encryption test passed!" if test_data == decrypted else "❌ Failed!")
    
    # Test token generation
    print("\n🔑 Testing Token Generation\n")
    token_mgr = SyncToken()
    
    token = token_mgr.create_token("server_1")
    print(f"Generated token: {token}")
    print(f"Token valid: {token_mgr.validate_token(token)}")
    
    api_key = SyncEncryption.generate_api_key()
    print(f"\nGenerated API key: {api_key}")

