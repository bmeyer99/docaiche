"""
Factory Functions - PRD-010
Factory functions for creating enrichment system components.

Provides dependency injection and configuration management for enrichment
pipeline components as specified in PRD-010.
"""

import logging
from typing import Optional

from .enricher import KnowledgeEnricher
from .tasks import TaskManager
from .models import EnrichmentConfig
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


async def create_knowledge_enricher(
    config: Optional[EnrichmentConfig] = None,
    db_manager: Optional[DatabaseManager] = None
) -> KnowledgeEnricher:
    """
    Create knowledge enricher with proper dependencies.
    
    Args:
        config: Enrichment configuration (creates default if None)
        db_manager: Database manager (creates default if None)
        
    Returns:
        Configured KnowledgeEnricher instance
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Use default config if not provided
        if config is None:
            config = EnrichmentConfig()
        
        # Create database manager if not provided
        if db_manager is None:
            from src.database.connection import create_database_manager
            db_manager = await create_database_manager()
        
        # Create enricher
        enricher = KnowledgeEnricher(config, db_manager)
        
        logger.info("KnowledgeEnricher created successfully")
        return enricher
        
    except Exception as e:
        logger.error(f"Failed to create KnowledgeEnricher: {e}")
        raise


def create_task_manager(
    config: EnrichmentConfig,
    db_manager: DatabaseManager
) -> TaskManager:
    """
    Create task manager with dependencies.
    
    Args:
        config: Enrichment configuration
        db_manager: Database manager
        
    Returns:
        Configured TaskManager instance
    """
    try:
        from .queue import EnrichmentTaskQueue
        
        # Create task queue
        task_queue = EnrichmentTaskQueue(config)
        
        # Create task manager
        task_manager = TaskManager(config, task_queue, db_manager)
        
        logger.info("TaskManager created successfully")
        return task_manager
        
    except Exception as e:
        logger.error(f"Failed to create TaskManager: {e}")
        raise


def create_enrichment_config(
    max_concurrent_tasks: int = 5,
    task_timeout_seconds: int = 300,
    retry_delay_seconds: int = 60,
    queue_poll_interval: int = 10,
    batch_size: int = 10,
    enable_relationship_mapping: bool = True,
    enable_tag_generation: bool = True,
    enable_quality_assessment: bool = True,
    min_confidence_threshold: float = 0.7
) -> EnrichmentConfig:
    """
    Create enrichment configuration with specified parameters.
    
    Args:
        max_concurrent_tasks: Maximum concurrent tasks
        task_timeout_seconds: Task timeout in seconds
        retry_delay_seconds: Delay between retries
        queue_poll_interval: Queue polling interval
        batch_size: Batch processing size
        enable_relationship_mapping: Enable relationship mapping
        enable_tag_generation: Enable tag generation
        enable_quality_assessment: Enable quality assessment
        min_confidence_threshold: Minimum confidence threshold
        
    Returns:
        Configured EnrichmentConfig instance
    """
    return EnrichmentConfig(
        max_concurrent_tasks=max_concurrent_tasks,
        task_timeout_seconds=task_timeout_seconds,
        retry_delay_seconds=retry_delay_seconds,
        queue_poll_interval=queue_poll_interval,
        batch_size=batch_size,
        enable_relationship_mapping=enable_relationship_mapping,
        enable_tag_generation=enable_tag_generation,
        enable_quality_assessment=enable_quality_assessment,
        min_confidence_threshold=min_confidence_threshold
    )