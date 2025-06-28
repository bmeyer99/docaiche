"""
Configuration service implementation.

Provides a clean API-facing interface for managing system configuration,
connecting the API layer to the ConfigurationManager backend.
"""

from typing import Dict, Any
import datetime
from src.core.config.manager import ConfigurationManager
from src.api.schemas import ConfigurationResponse, ConfigurationItem


class ConfigService:
    """Service for handling configuration operations."""

    def __init__(self, config_manager: ConfigurationManager):
        """
        Initialize the configuration service.

        Args:
            config_manager: ConfigurationManager instance (required).
        """
        self.config_manager = config_manager

    def get_current_config(self) -> ConfigurationResponse:
        """
        Retrieves the current configuration and transforms it into the
        API schema, redacting sensitive information.

        Returns:
            ConfigurationResponse with current configuration items
        """
        config_model = self.config_manager.get_configuration()
        config_dict = config_model.model_dump()

        items = []
        sensitive_keywords = ["key", "token", "password", "secret", "credential"]

        def flatten_config(d: Dict[str, Any], parent_key: str = "") -> None:
            """Recursively flatten nested configuration dictionary."""
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k

                if isinstance(v, dict):
                    flatten_config(v, new_key)
                else:
                    # Check if this is a sensitive field
                    is_sensitive = any(
                        keyword in k.lower() for keyword in sensitive_keywords
                    )

                    # Convert value to string for display
                    if v is None:
                        display_value = "null"
                    elif isinstance(v, bool):
                        display_value = str(v).lower()
                    elif isinstance(v, (list, dict)):
                        display_value = str(v)
                    else:
                        display_value = str(v)

                    # Redact sensitive values
                    if is_sensitive and display_value and display_value != "null":
                        display_value = "********"

                    items.append(
                        ConfigurationItem(
                            key=new_key, value=display_value, is_sensitive=is_sensitive
                        )
                    )

        flatten_config(config_dict)

        return ConfigurationResponse(items=items, timestamp=datetime.datetime.utcnow())

    async def update_config_item(self, key: str, value: Any) -> ConfigurationResponse:
        """
        Updates a configuration item in the database and reloads the config.

        Args:
            key: The configuration key to update
            value: The new value for the configuration

        Returns:
            ConfigurationResponse with updated configuration
        """
        # Update the configuration in the database
        await self.config_manager.update_in_db(key, value)

        # Return the updated configuration
        return self.get_current_config()

    async def reload_config(self) -> ConfigurationResponse:
        """
        Forces a configuration reload from all sources.

        Returns:
            ConfigurationResponse with reloaded configuration
        """
        await self.config_manager.reload_configuration()
        return self.get_current_config()
