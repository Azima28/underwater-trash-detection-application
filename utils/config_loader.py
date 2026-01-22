import yaml
import os

class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            print(f"Warning: Configuration file {self.config_path} not found. Using defaults.")
            return {}
        
        with open(self.config_path, 'r') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                return {}

    def get(self, key_path, default=None):
        """Get value from nested config using dot notation (e.g., 'server.port')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

# Singleton instance
config = ConfigManager()
