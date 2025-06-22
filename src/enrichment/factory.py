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
from .concurrent import ResourceLimits
from .lifecycle import LifecycleManager
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


def create_task_manager(
    config: EnrichmentConfig,
    db_manager: DatabaseManager,
    resource_limits: Optional[ResourceLimits] = None
) -> TaskManager:
    """
    Create task manager with dependencies and concurrency controls.
    
    Args:
        config: Enrichment configuration
        db_manager: Database manager
        resource_limits: Resource limits for concurrency control
        
    Returns:
        Configured TaskManager instance with concurrency controls
    """
    try:
        from .queue import EnrichmentTaskQueue
        
        # Create task queue with resource limits
        task_queue = EnrichmentTaskQueue(config, resource_limits)
        
        # Create task manager with resource limits
        task_manager = TaskManager(config, task_queue, db_manager, resource_limits)
        
        logger.info("TaskManager created successfully with concurrency controls")
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


def create_enrichment_queue(
    config: EnrichmentConfig,
    resource_limits: Optional[ResourceLimits] = None
) -> "EnrichmentQueue":
    """
    Create enrichment queue with configuration and concurrency controls.
    
    Args:
        config: Enrichment configuration
        resource_limits: Resource limits for concurrency control
        
    Returns:
        Configured EnrichmentQueue instance with concurrency controls
        
    Raises:
        Exception: If queue creation fails
    """
    try:
        from .queue import EnrichmentQueue
        
        queue = EnrichmentQueue(config, resource_limits)
        
        logger.info("EnrichmentQueue created successfully with concurrency controls")
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
    db_manager: DatabaseManager,
    resource_limits: Optional[ResourceLimits] = None
) -> TaskManager:
    """
    Create task manager with integrated configuration system and concurrency controls.
    
    Args:
        db_manager: Database manager
        resource_limits: Resource limits for concurrency control
        
    Returns:
        Configured TaskManager instance with integrated config and concurrency controls
        
    Raises:
        Exception: If creation fails
    """
    try:
        # Get integrated configuration
        from .config import get_enrichment_config
        config = await get_enrichment_config()
        
        from .queue import EnrichmentTaskQueue
        
        # Create task queue with resource limits
        task_queue = EnrichmentTaskQueue(config, resource_limits)
        
        # Create task manager with resource limits
        task_manager = TaskManager(config, task_queue, db_manager, resource_limits)
        
        logger.info("TaskManager created with integrated configuration and concurrency controls")
        return task_manager
        
    except Exception as e:
        logger.error(f"Failed to create TaskManager with integrated config: {e}")
        raise


def create_resource_limits(
    api_calls_per_minute: int = 60,
    max_processing_slots: int = 5,
    max_database_connections: int = 10,
    max_vector_db_connections: int = 3,
    max_llm_connections: int = 2
) -> ResourceLimits:
    """
    Create resource limits configuration for concurrency control.
    
    Args:
        api_calls_per_minute: Maximum API calls per minute
        max_processing_slots: Maximum concurrent processing slots
        max_database_connections: Maximum database connections
        max_vector_db_connections: Maximum vector database connections
        max_llm_connections: Maximum LLM connections
        
    Returns:
        Configured ResourceLimits instance
    """
    return ResourceLimits(
        api_calls_per_minute=api_calls_per_minute,
        max_processing_slots=max_processing_slots,
        max_database_connections=max_database_connections,
        max_vector_db_connections=max_vector_db_connections,
        max_llm_connections=max_llm_connections
    )


def create_lifecycle_manager(
    config: EnrichmentConfig,
    db_manager: Optional[DatabaseManager] = None,
    resource_limits: Optional[ResourceLimits] = None,
    shutdown_timeout: float = 30.0
) -> LifecycleManager:
    """
    Create lifecycle manager with comprehensive component management.
    
    Args:
        config: Enrichment configuration
        db_manager: Database manager instance
        resource_limits: Resource limits for concurrency control
        shutdown_timeout: Maximum time to wait for graceful shutdown
        
    Returns:
        Configured LifecycleManager instance
        
    Raises:
        Exception: If lifecycle manager creation fails
    """
    try:
        # Create database manager if not provided
        if db_manager is None:
            from src.database.connection import create_database_manager
            db_manager = create_database_manager()
        
        # Create resource limits if not provided
        if resource_limits is None:
            resource_limits = create_resource_limits()
        
        # Create lifecycle manager
        lifecycle_manager = LifecycleManager(
            config=config,
            db_manager=db_manager,
            resource_limits=resource_limits,
            shutdown_timeout=shutdown_timeout
        )
        
        logger.info("LifecycleManager created successfully")
        return lifecycle_manager
        
    except Exception as e:
        logger.error(f"Failed to create LifecycleManager: {e}")
        raise


async def create_lifecycle_manager_with_integrated_config(
    db_manager: Optional[DatabaseManager] = None,
    resource_limits: Optional[ResourceLimits] = None,
    shutdown_timeout: float = 30.0
) -> LifecycleManager:
    """
    Create lifecycle manager with integrated configuration system.
    
    Args:
        db_manager: Database manager instance
        resource_limits: Resource limits for concurrency control
        shutdown_timeout: Maximum time to wait for graceful shutdown
        
    Returns:
        Configured LifecycleManager instance with integrated config
        
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
        
        # Create resource limits if not provided
        if resource_limits is None:
            resource_limits = create_resource_limits()
        
        # Create lifecycle manager
        lifecycle_manager = LifecycleManager(
            config=config,
            db_manager=db_manager,
            resource_limits=resource_limits,
            shutdown_timeout=shutdown_timeout
        )
        
        logger.info("LifecycleManager created with integrated configuration")
        return lifecycle_manager
        
    except Exception as e:
        logger.error(f"Failed to create LifecycleManager with integrated config: {e}")
        raise


async def create_complete_enrichment_system(
    db_manager: Optional[DatabaseManager] = None,
    content_processor: Optional[Any] = None,
    anythingllm_client: Optional[Any] = None,
    search_orchestrator: Optional[Any] = None,
    resource_limits: Optional[ResourceLimits] = None,
    shutdown_timeout: float = 30.0
) -> LifecycleManager:
    """
    Create complete enrichment system with lifecycle management.
    
    Initializes all components and prepares them for coordinated startup/shutdown.
    
    Args:
        db_manager: Database manager instance
        content_processor: Content processor instance
        anythingllm_client: AnythingLLM client instance
        search_orchestrator: Search orchestrator instance
        resource_limits: Resource limits for concurrency control
        shutdown_timeout: Maximum time to wait for graceful shutdown
        
    Returns:
        Configured LifecycleManager ready for component management
        
    Raises:
        Exception: If system creation fails
    """
    try:
        logger.info("Creating complete enrichment system with lifecycle management")
        
        # Create lifecycle manager with integrated config
        lifecycle_manager = await create_lifecycle_manager_with_integrated_config(
            db_manager=db_manager,
            resource_limits=resource_limits,
            shutdown_timeout=shutdown_timeout
        )
        
        # Initialize all components
        await lifecycle_manager.initialize_components()
        
        # Inject optional components if provided
        if content_processor:
            enricher = lifecycle_manager.get_component('knowledge_enricher')
            if enricher:
                enricher.content_processor = content_processor
                logger.debug("Content processor injected into knowledge enricher")
        
        if anythingllm_client:
            enricher = lifecycle_manager.get_component('knowledge_enricher')
            if enricher:
                enricher.anythingllm_client = anythingllm_client
                logger.debug("AnythingLLM client injected into knowledge enricher")
        
        if search_orchestrator:
            enricher = lifecycle_manager.get_component('knowledge_enricher')
            if enricher:
                enricher.search_orchestrator = search_orchestrator
                logger.debug("Search orchestrator injected into knowledge enricher")
        
        logger.info("Complete enrichment system created successfully")
        return lifecycle_manager
        
    except Exception as e:
        logger.error(f"Failed to create complete enrichment system: {e}")
        raise