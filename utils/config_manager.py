import json
import os
from typing import Any, Dict
import logging


class ConfigManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.load_config()

    def load_config(self) -> None:
        """Load the configuration from the file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.logger.warning(
                    f"Config file {self.config_file} not found. Creating a new one.")
                self.save_config()
        except json.JSONDecodeError:
            self.logger.error(
                f"Error decoding JSON from {self.config_file}. Using empty config.")
            self.config = {}
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            raise

    def save_config(self) -> None:
        """Save the current configuration to the file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            raise

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key (str): The configuration key.
            default (Any, optional): The default value if the key is not found.

        Returns:
            Any: The configuration value or the default.
        """
        return self.config.get(key, default)

    def update_config(self, key: str, value: Any) -> None:
        """
        Update a configuration value and save the config.

        Args:
            key (str): The configuration key.
            value (Any): The new value.
        """
        self.config[key] = value
        self.save_config()

    def delete_config(self, key: str) -> None:
        """
        Delete a configuration key and save the config.

        Args:
            key (str): The configuration key to delete.
        """
        self.config.pop(key, None)
        self.save_config()

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration key-value pairs.
        """
        return self.config.copy()

    def clear_config(self) -> None:
        """Clear all configuration and save an empty config."""
        self.config.clear()
        self.save_config()

    def set_default_config(self, default_config: Dict[str, Any]) -> None:
        """
        Set default configuration values if they don't exist.

        Args:
            default_config (Dict[str, Any]): Default configuration key-value pairs.
        """
        for key, value in default_config.items():
            if key not in self.config:
                self.config[key] = value
        self.save_config()

    def is_config_empty(self) -> bool:
        """
        Check if the configuration is empty.

        Returns:
            bool: True if the configuration is empty, False otherwise.
        """
        return len(self.config) == 0

    def get_nested_config(self, keys: list, default: Any = None) -> Any:
        """
        Get a nested configuration value.

        Args:
            keys (list): List of keys to traverse the nested structure.
            default (Any, optional): The default value if the key is not found.

        Returns:
            Any: The nested configuration value or the default.
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value

    def update_nested_config(self, keys: list, value: Any) -> None:
        """
        Update a nested configuration value and save the config.

        Args:
            keys (list): List of keys to traverse the nested structure.
            value (Any): The new value.
        """
        current = self.config
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value
        self.save_config()
