"""
Factory Functions - PRD-010
Factory functions for creating enrichment system components.

Provides dependency injection and configuration management for enrichment
pipeline components as specified in PRD-010.
"""

import logging
from typing import Optional, Any

from .enricher import KnowledgeEnricher
from .tasks import TaskManager
from .models import EnrichmentConfig
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


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


def create_enrichment_queue(config: EnrichmentConfig) -> "EnrichmentQueue":
    """
    Create enrichment queue with configuration.
    
    Args:
        config: Enrichment configuration
        
    Returns:
        Configured EnrichmentQueue instance
        
    Raises:
        Exception: If queue creation fails
    """
    try:
        from .queue import EnrichmentQueue
        
        queue = EnrichmentQueue(config)
        
        logger.info("EnrichmentQueue created successfully")
        return queue
        
    except Exception as e:
        logger.error(f"Failed to create EnrichmentQueue: {e}")
        raise


def create_knowledge_enricher(
    config: EnrichmentConfig,
    db_manager: Optional[DatabaseManager] = None,
    content_processor: Optional[Any] = None,
    anythingllm_client: Optional[Any] = None,
    search_orchestrator: Optional[Any] = None
) -> KnowledgeEnricher:
    """
    Create knowledge enricher with all dependencies.
    
    Args:
        config: Enrichment configuration
        db_manager: Database manager
        content_processor: Content processor instance
        anythingllm_client: AnythingLLM client instance
        search_orchestrator: Search orchestrator instance
        
    Returns:
        Configured KnowledgeEnricher instance
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Create database manager if not provided
        if db_manager is None:
            from src.database.connection import create_database_manager
            db_manager = create_database_manager()
        
        # Create enricher with all dependencies
        enricher = KnowledgeEnricher(
            config=config,
            db_manager=db_manager,
            content_processor=content_processor,
            anythingllm_client=anythingllm_client,
            search_orchestrator=search_orchestrator
        )
        
        logger.info("KnowledgeEnricher created successfully with dependencies")
        return enricher
        
    except Exception as e:
        logger.error(f"Failed to create KnowledgeEnricher: {e}")
        raise
async def create_knowledge_enricher_with_integrated_config(
    db_manager: Optional[DatabaseManager] = None,
    content_processor: Optional[Any] = None,
    anythingllm_client: Optional[Any] = None,
    search_orchestrator: Optional[Any] = None
) -> KnowledgeEnricher:
    """
    Create knowledge enricher with integrated configuration system.

    Args:
        db_manager: Database manager
        content_processor: Content processor instance
        anythingllm_client: AnythingLLM client instance
        search_orchestrator: Search orchestrator instance

    Returns:
        Configured KnowledgeEnricher instance with integrated config
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Get integrated configuration
        from .config import get_enrichment_config
        config = await get_enrichment_config()
        
        # Create database manager if not provided
        if db_manager is None:
            from src.database.connection import create_database_manager
            db_manager = create_database_manager()

        # Create enricher with integrated config
        enricher = KnowledgeEnricher(
            config=config,
            db_manager=db_manager,
            content_processor=content_processor,
            anythingllm_client=anythingllm_client,
            search_orchestrator=search_orchestrator
        )

        logger.info("KnowledgeEnricher created with integrated configuration")
        return enricher

    except Exception as e:
        logger.error(f"Failed to create KnowledgeEnricher with integrated config: {e}")
        raise


async def create_task_manager_with_integrated_config(
    db_manager: DatabaseManager
) -> TaskManager:
    """
    Create task manager with integrated configuration system.
    
    Args:
        db_manager: Database manager
        
    Returns:
        Configured TaskManager instance with integrated config
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Get integrated configuration
        from .config import get_enrichment_config
        config = await get_enrichment_config()
        
        from .queue import EnrichmentTaskQueue
        
        # Create task queue
        task_queue = EnrichmentTaskQueue(config)
        
        # Create task manager
        task_manager = TaskManager(config, task_queue, db_manager)
        
        logger.info("TaskManager created with integrated configuration")
        return task_manager
        
    except Exception as e:
        logger.error(f"Failed to create TaskManager with integrated config: {e}")
        raise