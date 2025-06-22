"""
Knowledge Enricher - PRD-010
Main enrichment coordinator for background knowledge enhancement.

Orchestrates the complete enrichment pipeline including content analysis,
relationship mapping, tag generation, and quality improvement.
"""

import asyncio
import html
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from .models import (
    EnrichmentTask, EnrichmentResult, EnrichmentType, 
    EnrichmentPriority, EnrichmentConfig, EnrichmentMetrics
)
from .tasks import TaskManager
from .queue import EnrichmentTaskQueue
from .exceptions import EnrichmentError
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class KnowledgeEnricher:
    """
    Main knowledge enrichment coordinator.
    
    Manages the complete enrichment pipeline as specified in PRD-010,
    including task coordination, background processing, and monitoring.
    """
    
    def __init__(
        self,
        config: EnrichmentConfig,
        db_manager: DatabaseManager,
        content_processor: Optional[Any] = None,
        anythingllm_client: Optional[Any] = None,
        search_orchestrator: Optional[Any] = None,
        auto_start: bool = True
    ):
        """
        Initialize knowledge enricher with auto-startup capability.
        
        Args:
            config: Enrichment configuration
            db_manager: Database manager
            content_processor: Content processor instance
            anythingllm_client: AnythingLLM client instance
            search_orchestrator: Search orchestrator instance
            auto_start: Automatically start enricher after initialization
        """
        self.config = config
        self.db_manager = db_manager
        self.content_processor = content_processor
        self.anythingllm_client = anythingllm_client
        self.search_orchestrator = search_orchestrator
        self.auto_start = auto_start
        
        # Initialize components
        self.task_queue = EnrichmentTaskQueue(config)
        self.task_manager = TaskManager(config, self.task_queue, db_manager)
        
        self._running = False
        self._startup_task: Optional[asyncio.Task] = None
        self._initialization_complete = False
        
        logger.info(f"KnowledgeEnricher initialized (auto_start={auto_start})")
        
        # Schedule auto-startup if enabled
        if self.auto_start:
            self._schedule_auto_startup()
    
    def _schedule_auto_startup(self) -> None:
        """
        Schedule automatic startup in the background.
        
        Prevents blocking initialization while ensuring enricher starts automatically.
        """
        try:
            # Create startup task without waiting for it
            self._startup_task = asyncio.create_task(self._auto_startup_sequence())
            logger.info("Auto-startup scheduled for KnowledgeEnricher")
            
        except Exception as e:
            logger.error(f"Failed to schedule auto-startup: {e}")
            # Fall back to marking as ready for manual start
            self._initialization_complete = True
    
    async def _auto_startup_sequence(self) -> None:
        """
        Execute automatic startup sequence with proper error handling.
        
        Ensures enricher becomes available without manual intervention.
        """
        try:
            # Wait briefly to allow other components to initialize
            await asyncio.sleep(1.0)
            
            # Perform startup with dependency validation
            await self.start()
            
            logger.info("KnowledgeEnricher auto-startup completed successfully")
            
        except Exception as e:
            logger.error(f"Auto-startup failed: {e}")
            # Mark initialization as complete but not running
            self._initialization_complete = True
            
            # Optionally retry after delay
            if not self._running:
                logger.info("Scheduling auto-startup retry in 30 seconds")
                await asyncio.sleep(30)
                try:
                    await self.start()
                    logger.info("KnowledgeEnricher auto-startup retry succeeded")
                except Exception as retry_error:
                    logger.error(f"Auto-startup retry failed: {retry_error}")
    
    async def wait_for_ready(self, timeout: float = 30.0) -> bool:
        """
        Wait for enricher to be ready (either running or initialization complete).
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if enricher is ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if self._running or self._initialization_complete:
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    async def start(self) -> None:
        """
        Start the knowledge enricher system with dependency validation.
        
        Validates all dependencies and initializes components with proper error handling.
        
        Raises:
            EnrichmentError: If startup fails or dependencies are not available
        """
        try:
            if self._running:
                logger.warning("KnowledgeEnricher already running")
                return
            
            logger.info("Starting KnowledgeEnricher with dependency validation")
            
            # Validate dependencies before starting
            await self._validate_startup_dependencies()
            
            # Start task manager
            await self.task_manager.start()
            
            self._running = True
            self._initialization_complete = True
            logger.info("KnowledgeEnricher started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start KnowledgeEnricher: {e}")
            await self.stop()
            raise EnrichmentError(
                f"Failed to start knowledge enricher: {str(e)}"
            )
    
    async def _validate_startup_dependencies(self) -> None:
        """
        Validate all required dependencies are available before startup.
        
        Raises:
            EnrichmentError: If required dependencies are not available
        """
        validation_errors = []
        
        # Validate database manager
        if not self.db_manager:
            validation_errors.append("Database manager is required")
        else:
            try:
                # Test database connection
                async with self.db_manager.get_connection() as conn:
                    await conn.execute("SELECT 1")
                logger.debug("Database connection validated")
            except Exception as e:
                validation_errors.append(f"Database connection failed: {str(e)}")
        
        # Validate task manager
        if not self.task_manager:
            validation_errors.append("Task manager is required")
        
        # Validate task queue
        if not self.task_queue:
            validation_errors.append("Task queue is required")
        else:
            try:
                # Test task queue health
                health = await self.task_queue.health_check()
                if health.get('status') != 'healthy':
                    validation_errors.append(f"Task queue unhealthy: {health}")
                logger.debug("Task queue validated")
            except Exception as e:
                validation_errors.append(f"Task queue validation failed: {str(e)}")
        
        # Optional component validation (warn but don't fail)
        if not self.content_processor:
            logger.warning("Content processor not available - some features may be limited")
        
        if not self.anythingllm_client:
            logger.warning("AnythingLLM client not available - vector operations will be limited")
        
        if not self.search_orchestrator:
            logger.warning("Search orchestrator not available - search integration will be limited")
        
        if validation_errors:
            error_message = "Dependency validation failed: " + "; ".join(validation_errors)
            logger.error(error_message)
            raise EnrichmentError(error_message)
        
        logger.info("All required dependencies validated successfully")
    
    async def stop(self) -> None:
        """Stop the knowledge enricher system."""
        try:
            logger.info("Stopping KnowledgeEnricher")
            self._running = False
            
            # Stop task manager
            await self.task_manager.stop()
            
            # Cancel startup task if running
            if self._startup_task and not self._startup_task.done():
                self._startup_task.cancel()
                try:
                    await self._startup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("KnowledgeEnricher stopped")
            
        except Exception as e:
            logger.error(f"Error stopping KnowledgeEnricher: {e}")
    
    async def enrich_content(
        self,
        content_id: str,
        enrichment_types: Optional[List[EnrichmentType]] = None,
        priority: EnrichmentPriority = EnrichmentPriority.NORMAL
    ) -> List[str]:
        """
        Submit content for enrichment processing.
        
        Args:
            content_id: Content identifier to enrich
            enrichment_types: Types of enrichment to perform (default: all)
            priority: Task priority
            
        Returns:
            List of task identifiers
            
        Raises:
            EnrichmentError: If enrichment submission fails
        """
        try:
            if not self._running:
                raise EnrichmentError("Knowledge enricher is not running")
            
            # Default to all enrichment types if not specified
            if enrichment_types is None:
                enrichment_types = [
                    EnrichmentType.CONTENT_ANALYSIS,
                    EnrichmentType.RELATIONSHIP_MAPPING,
                    EnrichmentType.TAG_GENERATION,
                    EnrichmentType.QUALITY_ASSESSMENT,
                    EnrichmentType.METADATA_ENHANCEMENT
                ]
            
            task_ids = []
            
            # Submit tasks for each enrichment type
            for enrichment_type in enrichment_types:
                task_id = await self.task_manager.submit_enrichment_task(
                    content_id=content_id,
                    task_type=enrichment_type,
                    priority=priority,
                    context={
                        'submitted_at': datetime.utcnow().isoformat(),
                        'enrichment_types': [t.value for t in enrichment_types]
                    }
                )
                task_ids.append(task_id)
            
            logger.info(
                f"Submitted {len(task_ids)} enrichment tasks for content {content_id}",
                extra={
                    "content_id": content_id,
                    "enrichment_types": [t.value for t in enrichment_types],
                    "priority": priority.value
                }
            )
            
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to enrich content {content_id}: {e}")
            raise EnrichmentError(
                f"Failed to enrich content: {str(e)}",
                error_context={"content_id": content_id}
            )
    
    def analyze_content_gaps(self, query: str) -> List[Dict[str, Any]]:
        """
        Analyze content gaps for given query with comprehensive XSS protection.
        
        Args:
            query: Search query to analyze for gaps
            
        Returns:
            List of identified content gaps
        """
        try:
            # Input validation for security
            if not query or not isinstance(query, str):
                raise ValueError("Invalid query: must be non-empty string")
            
            # Sanitize query to prevent injection and XSS
            query = query.strip()
            if len(query) > 1000:
                raise ValueError("Query too long: maximum 1000 characters")
            
            # Enhanced security validation to prevent XSS and injection attacks
            dangerous_patterns = [
                "<script", "</script", "<iframe", "</iframe", "<object", "</object",
                "<embed", "</embed", "<link", "<meta", "javascript:", "data:",
                "vbscript:", "onload=", "onerror=", "onclick=", "onmouseover=",
                "onfocus=", "onblur=", "onchange=", "onsubmit=", "onkeydown=", "ondblclick=",
                "<img", "<svg", "expression(",  # Add missing patterns for comprehensive XSS protection
                ";", "--", "DROP", "DELETE", "INSERT", "UPDATE", "UNION", "SELECT"
            ]
            
            query_lower = query.lower()
            for pattern in dangerous_patterns:
                if pattern.lower() in query_lower:
                    raise ValueError(f"Invalid query: contains potentially dangerous content")
            
            # HTML escape the query to prevent XSS in responses
            sanitized_query = html.escape(query, quote=True)
            
            # Additional validation for special characters that could be used in attacks
            if any(char in query for char in ['<', '>', '"', "'", '&']):
                # Log the potential security issue
                logger.warning(f"Query contains HTML special characters - sanitized: {sanitized_query}")
            
            # Mock implementation - would use actual content analysis
            gaps = [
                {
                    'query': sanitized_query,  # Use sanitized query in response
                    'gap_type': 'missing_examples',
                    'confidence': 0.8,
                    'suggested_sources': ['documentation', 'tutorials']
                }
            ]
            
            logger.debug(f"Content gaps analyzed for sanitized query: {sanitized_query}")
            return gaps
            
        except Exception as e:
            # Sanitize error message to prevent information leakage
            sanitized_query = html.escape(query[:50], quote=True) if isinstance(query, str) else 'invalid_input'
            logger.error(f"Content gap analysis failed for query '{sanitized_query}': {e}")
            raise
    
    # Additional methods remain the same but with proper indentation...
    async def get_enrichment_status(self, content_id: str) -> Dict[str, Any]:
        """Get enrichment status for content."""
        try:
            query = """
            SELECT content_id, title, quality_score, 
                   created_at, updated_at
            FROM content_metadata 
            WHERE content_id = ?
            """
            
            async with self.db_manager.get_connection() as conn:
                result = await conn.execute(query, (content_id,))
                row = await result.fetchone()
                
                if not row:
                    return {
                        "content_id": content_id,
                        "status": "not_found",
                        "message": "Content not found"
                    }
                
                return {
                    "content_id": content_id,
                    "status": "available",
                    "title": row[1],
                    "quality_score": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "enrichment_available": True
                }
                
        except Exception as e:
            logger.error(f"Failed to get enrichment status for {content_id}: {e}")
            return {
                "content_id": content_id,
                "status": "error",
                "error": str(e)
            }
    
    async def get_system_metrics(self) -> EnrichmentMetrics:
        """Get enrichment system metrics."""
        try:
            return await self.task_manager.get_metrics()
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return EnrichmentMetrics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform knowledge enricher health check."""
        try:
            task_manager_health = await self.task_manager.health_check()
            queue_health = await self.task_queue.health_check()
            metrics = await self.get_system_metrics()
            
            is_healthy = (
                self._running and
                task_manager_health.get('status') == 'healthy' and
                queue_health.get('status') == 'healthy'
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'running': self._running,
                'auto_start_enabled': self.auto_start,
                'initialization_complete': self._initialization_complete,
                'components': {
                    'task_manager': task_manager_health,
                    'task_queue': queue_health
                },
                'metrics': {
                    'total_processed': metrics.total_tasks_processed,
                    'success_rate': 1.0 - metrics.error_rate if metrics.total_tasks_processed > 0 else 0.0,
                    'avg_processing_time_ms': metrics.average_processing_time_ms,
                    'last_updated': metrics.last_updated.isoformat() if metrics.last_updated else None
                },
                'configuration': {
                    'max_concurrent_tasks': self.config.max_concurrent_tasks,
                    'task_timeout_seconds': self.config.task_timeout_seconds,
                    'enabled_features': {
                        'relationship_mapping': self.config.enable_relationship_mapping,
                        'tag_generation': self.config.enable_tag_generation,
                        'quality_assessment': self.config.enable_quality_assessment
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Knowledge enricher health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }