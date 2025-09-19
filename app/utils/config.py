"""Configuration management utilities."""

import os
import yaml
from typing import Dict, Any, Optional

class ConfigManager:
    """Manages configuration loading and access."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self._config = None
        self.load_config()
    
    def _find_config_file(self) -> str:
        """Find the configuration file."""
        # Check environment variable first
        config_from_env = os.environ.get('ORCHESTRATOR_CONFIG')
        if config_from_env and os.path.exists(config_from_env):
            return config_from_env
        
        # Check common locations
        possible_paths = [
            'config/local.yml',
            'config/development.yml',
            'config/default.yml',
            os.path.expanduser('~/.orchestrator/config.yml'),
            '/etc/orchestrator/config.yml'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Default fallback
        return 'config/default.yml'
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Configuration file {self.config_file} not found. Using defaults.")
            self._config = self._get_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'database': {
                'path': 'cluster_data.db',
                'echo': False
            },
            'flask': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'secret_key': 'change-this-in-production'
            },
            'ansible': {
                'config_file': 'ansible/ansible.cfg',
                'playbooks_dir': 'ansible/playbooks',
                'inventory_dir': 'ansible/inventory',
                'timeout': 300
            },
            'microk8s': {
                'default_channel': '1.28/stable',
                'default_addons': ['dns', 'storage', 'ingress'],
                'network': {
                    'cluster_cidr': '10.1.0.0/16',
                    'service_cidr': '10.152.183.0/24'
                }
            },
            'ssh': {
                'default_user': 'ubuntu',
                'default_port': 22,
                'connection_timeout': 30,
                'key_directory': '~/.ssh'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/orchestrator.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        if not self._config:
            return default
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot-separated key."""
        if not self._config:
            self._config = {}
        
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_config(self, file_path: Optional[str] = None):
        """Save current configuration to file."""
        save_path = file_path or self.config_file
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config or {}

# Global configuration instance
config = ConfigManager()
