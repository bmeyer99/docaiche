"""
Content Processor Factory - PRD-008
Factory functions for creating ContentProcessor instances with configuration integration
"""

import logging
from typing import Optional

from src.core.config.models import ContentConfig
from src.database.connection import DatabaseManager, create_database_manager
from .content_processor import ContentProcessor

logger = logging.getLogger(__name__)


async def create_content_processor(
    config: Optional[ContentConfig] = None,
    db_manager: Optional[DatabaseManager] = None
) -> ContentProcessor:
    """
    Factory function to create ContentProcessor with configuration integration.
    
    Args:
        config: Optional content configuration override
        db_manager: Optional database manager override
        
    Returns:
        Configured ContentProcessor instance
        
    Raises:
        Exception: If configuration loading or database connection fails
    """
    try:
        # Use provided config or load from system configuration
        if config is None:
            # Integrate with CFG-001 configuration system
            try:
                from src.core.config import get_system_configuration
                system_config = get_system_configuration()
                config = system_config.content
                logger.info("Loaded content configuration from system configuration")
            except Exception as e:
                logger.warning(f"Could not load system configuration, using defaults: {e}")
                # Use default configuration
                config = ContentConfig()
        
        # Use provided database manager or create one
        if db_manager is None:
            db_manager = await create_database_manager()
            logger.info("Created database manager for content processor")
        
        # Create and return ContentProcessor instance
        processor = ContentProcessor(config, db_manager)
        logger.info("Content processor created successfully")
        return processor
        
    except Exception as e:
        logger.error(f"Failed to create content processor: {e}")
        raise


def create_file_content(content: str, source_url: str, title: str = "") -> "FileContent":
    """
    Factory function to create FileContent instance.
    
    Args:
        content: Raw file content
        source_url: Source URL of the file
        title: Optional title
        
    Returns:
        FileContent instance
    """
    from .content_processor import FileContent
    return FileContent(content, source_url, title)


def create_scraped_content(content: str, source_url: str, title: str = "") -> "ScrapedContent":
    """
    Factory function to create ScrapedContent instance.
    
    Args:
        content: Raw scraped content
        source_url: Source URL of the scraped page
        title: Optional title
        
    Returns:
        ScrapedContent instance
    """
    from .content_processor import ScrapedContent
    return ScrapedContent(content, source_url, title)