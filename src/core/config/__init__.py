import asyncio
import logging

from src.core.config.manager import get_configuration_manager  # noqa: F401

class ConfigManager:
    """
    Minimal stub for PRD-010 test compatibility.
    """

    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def get(*args, **kwargs):
        return None


def get_settings(*args, **kwargs):
    from src.core.config.manager import ConfigurationManager

    manager = ConfigurationManager()
    config = manager.get_configuration()
    if config is None:
        raise RuntimeError("System configuration not loaded. Application cannot start.")
    return config


# --- Implementation Engineer: Provide sync wrapper for system configuration ---

logger = logging.getLogger(__name__)


def get_system_configuration():
    """
    Synchronous wrapper to get the current system configuration for dependency injection.
    Returns None if configuration manager is not initialized.
    """
    try:
        from src.core.config.manager import ConfigurationManager

        manager = ConfigurationManager()
        # Try to get the configuration if loaded, else return None
        return manager.get_configuration()
    except Exception as e:
        logger.warning(f"get_system_configuration: returning None due to error: {e}")
        return None


def reload_configuration():
    """
    Compatibility stub for FastAPI and enrichment imports.
    Calls the async reload_configuration on the ConfigurationManager singleton.
    """
    try:
        from src.core.config.manager import ConfigurationManager

        manager = ConfigurationManager()
        return asyncio.run(manager.reload_configuration())
    except Exception as e:
        logging.getLogger(__name__).warning(f"reload_configuration: failed due to {e}")
        return None
