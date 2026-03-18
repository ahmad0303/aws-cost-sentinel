"""Configuration management for AWS Cost Sentinel."""

import os
import yaml
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager that loads from YAML and environment variables."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Load YAML configuration
        self.config = self._load_yaml(config_path)
        
        # Replace environment variable placeholders
        self._resolve_env_vars(self.config)
    
    def _load_yaml(self, config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing configuration
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> None:
        """Recursively resolve environment variable placeholders in config.
        
        Replaces ${VAR_NAME} with the value of environment variable VAR_NAME.
        
        Args:
            config: Configuration dictionary to process
        """
        for key, value in config.items():
            if isinstance(value, dict):
                self._resolve_env_vars(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]  # Remove ${ and }
                config[key] = os.getenv(env_var, value)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration key
                     Example: 'aws.region' or 'monitoring.budgets.daily_max'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration key
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access to top-level keys."""
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if top-level key exists."""
        return key in self.config


# Global configuration instance
_config: Config = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get or create the global configuration instance.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
