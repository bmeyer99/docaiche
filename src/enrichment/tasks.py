"""
Task Management - PRD-010
Background task management and coordination for enrichment operations.

Handles task processing, coordination, and monitoring as specified in PRD-010.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .models import (
    EnrichmentTask, EnrichmentResult, EnrichmentPriority,
    EnrichmentType, TaskStatus, EnrichmentConfig, EnrichmentMetrics
)
from .queue import EnrichmentTaskQueue
from .analyzers import ContentAnalyzer, RelationshipAnalyzer, TagGenerator
from .exceptions import TaskProcessingError, EnrichmentTimeoutError
from .concurrent import ConcurrentTaskExecutor, ResourceType, ResourceLimits
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Main task manager for enrichment operations.
    
    Coordinates task processing, manages workers, and provides monitoring
    capabilities as specified in PRD-010.
    """
    
    def __init__(
        self,
        config: EnrichmentConfig,
        task_queue: EnrichmentTaskQueue,
        db_manager: DatabaseManager,
        resource_limits: Optional[ResourceLimits] = None
    ):
        """
        Initialize task manager with concurrency controls.
        
        Args:
            config: Enrichment configuration
            task_queue: Task queue manager
            db_manager: Database manager
            resource_limits: Resource limit configuration for concurrency control
        """
        self.config = config
        self.task_queue = task_queue
        self.db_manager = db_manager
        
        # Initialize concurrent task executor
        self.concurrent_executor = ConcurrentTaskExecutor(config, resource_limits)
        
        # Initialize analyzers
        self.content_analyzer = ContentAnalyzer()
        self.relationship_analyzer = RelationshipAnalyzer()
        self.tag_generator = TagGenerator()
        
        # Worker management with concurrency control
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._metrics = EnrichmentMetrics()
        self._priority_queue_processor: Optional[asyncio.Task] = None
        
        logger.info("TaskManager initialized with concurrency controls")
    
    async def start(self) -> None:
        """
        Start the task manager with concurrent execution and priority queue processing.
        
        Raises:
            TaskProcessingError: If startup fails
        """
        try:
            if self._running:
                logger.warning("TaskManager already running")
                return
            
            self._running = True
            logger.info(f"Starting TaskManager with {self.config.max_concurrent_tasks} workers")
            
            # Start worker tasks with concurrency control
            for i in range(self.config.max_concurrent_tasks):
                worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
                self._workers.append(worker)
            
            # Start priority queue processor
            self._priority_queue_processor = asyncio.create_task(
                self.concurrent_executor.process_priority_queue()
            )
            
            logger.info("TaskManager started successfully with concurrency controls")
            
        except Exception as e:
            logger.error(f"Failed to start TaskManager: {e}")
            await self.stop()
            raise TaskProcessingError(
                f"Failed to start task manager: {str(e)}"
            )
    
    async def stop(self) -> None:
        """Stop the task manager with graceful shutdown of concurrent executor."""
        try:
            logger.info("Stopping TaskManager")
            self._running = False
            
            # Gracefully shutdown concurrent executor
            if hasattr(self, 'concurrent_executor'):
                shutdown_stats = await self.concurrent_executor.graceful_shutdown()
                logger.info(f"Concurrent executor shutdown: {shutdown_stats}")
            
            # Stop priority queue processor
            if self._priority_queue_processor:
                self._priority_queue_processor.cancel()
                try:
                    await self._priority_queue_processor
                except asyncio.CancelledError:
                    pass
            
            # Cancel all workers
            for worker in self._workers:
                worker.cancel()
            
            # Wait for workers to finish
            if self._workers:
                await asyncio.gather(*self._workers, return_exceptions=True)
            
            self._workers.clear()
            self._priority_queue_processor = None
            logger.info("TaskManager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping TaskManager: {e}")
    
    async def submit_enrichment_task(
        self, 
        content_id: str, 
        task_type: EnrichmentType,
        priority: EnrichmentPriority = EnrichmentPriority.NORMAL,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit enrichment task for processing.
        
        Args:
            content_id: Content ID to enrich
            task_type: Type of enrichment to perform
            priority: Task priority
            context: Additional task context
            
        Returns:
            Task identifier
            
        Raises:
            TaskProcessingError: If task submission fails
        """
        try:
            task = EnrichmentTask(
                content_id=content_id,
                task_type=task_type,
                priority=priority,
                context=context or {}
            )
            
            await self.task_queue.submit_task(task)
            
            logger.info(
                f"Enrichment task submitted: {content_id} ({task_type})",
                extra={
                    "content_id": content_id,
                    "task_type": task_type,
                    "priority": priority
                }
            )
            
            return content_id
            
        except Exception as e:
            logger.error(f"Failed to submit enrichment task: {e}")
            raise TaskProcessingError(
                f"Failed to submit enrichment task: {str(e)}",
                content_id=content_id,
                task_type=task_type.value
            )
    
    async def get_metrics(self) -> EnrichmentMetrics:
        """
        Get current enrichment metrics.
        
        Returns:
            Current metrics
        """
        try:
            queue_status = await self.task_queue.get_status()
            
            # Update metrics with current queue status
            self._metrics.tasks_by_priority = {
                "urgent": 0,  # Would need to track in queue
                "high": 0,
                "normal": queue_status.pending_tasks,
                "low": 0
            }
            
            self._metrics.last_updated = datetime.utcnow()
            
            return self._metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return self._metrics
    
    async def _worker_loop(self, worker_id: str) -> None:
        """
        Main worker loop for processing tasks with concurrent execution.
        
        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started with concurrency controls")
        
        while self._running:
            try:
                # Get next task
                task = await self.task_queue.get_next_task()
                
                if not task:
                    # No tasks available, wait before checking again
                    await asyncio.sleep(self.config.queue_poll_interval)
                    continue
                
                # Determine required resources based on task type
                required_resources = self._get_required_resources(task)
                
                # Execute task with concurrent executor
                try:
                    result = await self.concurrent_executor.execute_task(
                        task,
                        self._process_task,
                        required_resources
                    )
                    
                    # Complete task successfully
                    await self.task_queue.complete_task(task.content_id, True)
                    
                    # Update metrics
                    self._metrics.total_tasks_processed += 1
                    self._metrics.successful_tasks += 1
                    
                    logger.debug(
                        f"Task completed by {worker_id}: {task.content_id} (success)",
                        extra={
                            "worker_id": worker_id,
                            "content_id": task.content_id,
                            "success": True
                        }
                    )
                    
                except Exception as e:
                    # Task failed, complete with error
                    await self.task_queue.complete_task(task.content_id, False, str(e))
                    
                    # Update metrics
                    self._metrics.total_tasks_processed += 1
                    self._metrics.failed_tasks += 1
                    
                    logger.error(
                        f"Task failed by {worker_id}: {task.content_id}: {e}",
                        extra={
                            "worker_id": worker_id,
                            "content_id": task.content_id,
                            "success": False,
                            "error": str(e)
                        }
                    )
                
                # Update error rate
                if self._metrics.total_tasks_processed > 0:
                    self._metrics.error_rate = self._metrics.failed_tasks / self._metrics.total_tasks_processed
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_task(self, task: EnrichmentTask) -> None:
        """
        Process individual enrichment task.
        
        Args:
            task: Task to process
            
        Raises:
            TaskProcessingError: If task processing fails
        """
        try:
            logger.debug(f"Processing task: {task.content_id} ({task.task_type})")
            
            # Get content from database
            content_data = await self._get_content_data(task.content_id)
            if not content_data:
                raise TaskProcessingError(
                    f"Content not found: {task.content_id}",
                    content_id=task.content_id
                )
            
            result = None
            
            # Process based on task type
            if task.task_type == EnrichmentType.CONTENT_ANALYSIS:
                result = await self._process_content_analysis(task, content_data)
                
            elif task.task_type == EnrichmentType.RELATIONSHIP_MAPPING:
                result = await self._process_relationship_mapping(task, content_data)
                
            elif task.task_type == EnrichmentType.TAG_GENERATION:
                result = await self._process_tag_generation(task, content_data)
                
            elif task.task_type == EnrichmentType.QUALITY_ASSESSMENT:
                result = await self._process_quality_assessment(task, content_data)
                
            elif task.task_type == EnrichmentType.METADATA_ENHANCEMENT:
                result = await self._process_metadata_enhancement(task, content_data)
                
            else:
                raise TaskProcessingError(
                    f"Unknown task type: {task.task_type}",
                    content_id=task.content_id,
                    task_type=task.task_type.value
                )
            
            # Store enrichment result
            if result:
                await self._store_enrichment_result(result)
            
            logger.debug(f"Task completed: {task.content_id}")
            
        except Exception as e:
            logger.error(f"Task processing failed for {task.content_id}: {e}")
            raise TaskProcessingError(
                f"Task processing failed: {str(e)}",
                content_id=task.content_id,
                task_type=task.task_type.value
            )
    
    async def _get_content_data(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve content data from database.
        
        Args:
            content_id: Content identifier
            
        Returns:
            Content data or None if not found
        """
        try:
            # Query content metadata table with parameterized query for security
            query = """
            SELECT content_id, title, source_url, technology, quality_score,
                   word_count, chunk_count, created_at
            FROM content_metadata
            WHERE content_id = ?
            """
            
            # Input validation for content_id
            if not content_id or not isinstance(content_id, str):
                raise ValueError("Invalid content_id: must be non-empty string")
            
            # Sanitize content_id to prevent injection
            content_id = content_id.strip()
            if not re.match(r'^[a-zA-Z0-9_-]+$', content_id):
                raise ValueError("Invalid content_id format: contains illegal characters")
            
            async with self.db_manager.get_connection() as conn:
                result = await conn.execute(query, (content_id,))
                row = await result.fetchone()
                
                if row:
                    return {
                        'content_id': row[0],
                        'title': row[1],
                        'source_url': row[2],
                        'technology': row[3],
                        'quality_score': row[4],
                        'word_count': row[5],
                        'chunk_count': row[6],
                        'created_at': row[7],
                        'content': ''  # Would need to load actual content
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get content data for {content_id}: {e}")
            return None
    
    async def _process_content_analysis(
        self, 
        task: EnrichmentTask, 
        content_data: Dict[str, Any]
    ) -> EnrichmentResult:
        """Process content analysis task."""
        start_time = time.time()
        
        analysis = await self.content_analyzer.analyze_content(
            content_data.get('content', ''),
            task.content_id,
            content_data
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnrichmentResult(
            content_id=task.content_id,
            enhanced_tags=[],
            relationships=[],
            quality_improvements=analysis,
            processing_time_ms=processing_time,
            confidence_score=0.8,
            enrichment_metadata={
                'analysis_type': 'content_analysis',
                'analysis_data': analysis
            }
        )
    
    async def _process_relationship_mapping(
        self, 
        task: EnrichmentTask, 
        content_data: Dict[str, Any]
    ) -> EnrichmentResult:
        """Process relationship mapping task."""
        start_time = time.time()
        
        # Get existing content for relationship analysis
        existing_content = []  # Would query from database
        
        relationships = await self.relationship_analyzer.analyze_relationships(
            task.content_id,
            content_data.get('content', ''),
            existing_content
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnrichmentResult(
            content_id=task.content_id,
            enhanced_tags=[],
            relationships=relationships,
            quality_improvements={},
            processing_time_ms=processing_time,
            confidence_score=0.7,
            enrichment_metadata={
                'analysis_type': 'relationship_mapping',
                'relationships_found': len(relationships)
            }
        )
    
    async def _process_tag_generation(
        self, 
        task: EnrichmentTask, 
        content_data: Dict[str, Any]
    ) -> EnrichmentResult:
        """Process tag generation task."""
        start_time = time.time()
        
        tags = await self.tag_generator.generate_tags(
            content_data.get('content', ''),
            content_data
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnrichmentResult(
            content_id=task.content_id,
            enhanced_tags=tags,
            relationships=[],
            quality_improvements={},
            processing_time_ms=processing_time,
            confidence_score=0.9,
            enrichment_metadata={
                'analysis_type': 'tag_generation',
                'tags_generated': len(tags)
            }
        )
    
    async def _process_quality_assessment(
        self, 
        task: EnrichmentTask, 
        content_data: Dict[str, Any]
    ) -> EnrichmentResult:
        """Process quality assessment task."""
        start_time = time.time()
        
        # Perform quality assessment (simplified implementation)
        quality_improvements = {
            'current_score': content_data.get('quality_score', 0.0),
            'recommended_improvements': [],
            'assessment_timestamp': datetime.utcnow().isoformat()
        }
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnrichmentResult(
            content_id=task.content_id,
            enhanced_tags=[],
            relationships=[],
            quality_improvements=quality_improvements,
            processing_time_ms=processing_time,
            confidence_score=0.8,
            enrichment_metadata={
                'analysis_type': 'quality_assessment'
            }
        )
    
    async def _process_metadata_enhancement(
        self, 
        task: EnrichmentTask, 
        content_data: Dict[str, Any]
    ) -> EnrichmentResult:
        """Process metadata enhancement task."""
        start_time = time.time()
        
        # Enhance metadata (simplified implementation)
        enhancements = {
            'enhanced_fields': ['tags', 'categories', 'difficulty_level'],
            'enhancement_timestamp': datetime.utcnow().isoformat()
        }
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnrichmentResult(
            content_id=task.content_id,
            enhanced_tags=[],
            relationships=[],
            quality_improvements=enhancements,
            processing_time_ms=processing_time,
            confidence_score=0.7,
            enrichment_metadata={
                'analysis_type': 'metadata_enhancement'
            }
        )
    
    async def _store_enrichment_result(self, result: EnrichmentResult) -> None:
        """
        Store enrichment result in database.
        
        Args:
            result: Enrichment result to store
        """
        try:
            # Store result in database (simplified implementation)
            # In real implementation, would update content_metadata table
            # and store enrichment data
            
            logger.debug(f"Stored enrichment result for {result.content_id}")
            
        except Exception as e:
            logger.error(f"Failed to store enrichment result: {e}")
            raise
    
    def _get_required_resources(self, task: EnrichmentTask) -> List[ResourceType]:
        """
        Determine required resources based on task type.
        
        Args:
            task: Enrichment task
            
        Returns:
            List of required resource types
        """
        base_resources = [ResourceType.PROCESSING_SLOTS, ResourceType.DATABASE_CONNECTIONS]
        
        # Add task-specific resources
        if task.task_type == EnrichmentType.CONTENT_ANALYSIS:
            base_resources.append(ResourceType.API_CALLS)
            
        elif task.task_type == EnrichmentType.RELATIONSHIP_MAPPING:
            base_resources.extend([ResourceType.VECTOR_DB_CONNECTIONS, ResourceType.API_CALLS])
            
        elif task.task_type == EnrichmentType.TAG_GENERATION:
            base_resources.append(ResourceType.LLM_CONNECTIONS)
            
        elif task.task_type == EnrichmentType.QUALITY_ASSESSMENT:
            base_resources.extend([ResourceType.LLM_CONNECTIONS, ResourceType.API_CALLS])
            
        elif task.task_type == EnrichmentType.METADATA_ENHANCEMENT:
            base_resources.append(ResourceType.API_CALLS)
        
        return base_resources

    async def submit_priority_task(
        self,
        task: EnrichmentTask,
        priority: Optional[EnrichmentPriority] = None
    ) -> None:
        """
        Submit task to priority queue with concurrency controls.
        
        Args:
            task: Task to submit
            priority: Override task priority
            
        Raises:
            QueueError: If queue is at capacity
        """
        if priority:
            task.priority = priority
        
        required_resources = self._get_required_resources(task)
        
        await self.concurrent_executor.submit_priority_task(
            task,
            self._process_task,
            required_resources
        )
        
        logger.info(f"Priority task submitted: {task.content_id} with resources {[r.value for r in required_resources]}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive task manager health check with concurrency metrics.
        
        Returns:
            Health status information including concurrency controls
        """
        try:
            queue_health = await self.task_queue.health_check()
            metrics = await self.get_metrics()
            
            # Get concurrency metrics
            concurrency_health = await self.concurrent_executor.health_check()
            concurrency_metrics = await self.concurrent_executor.get_concurrency_metrics()
            
            # Check worker status
            active_workers = sum(1 for worker in self._workers if not worker.done())
            
            is_healthy = (
                self._running and
                active_workers > 0 and
                queue_health.get('status') == 'healthy' and
                concurrency_health.get('status') == 'healthy'
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'running': self._running,
                'active_workers': active_workers,
                'total_workers': len(self._workers),
                'queue_health': queue_health,
                'concurrency_health': concurrency_health,
                'metrics': {
                    'total_processed': metrics.total_tasks_processed,
                    'success_rate': 1.0 - metrics.error_rate if metrics.total_tasks_processed > 0 else 0.0,
                    'avg_processing_time_ms': metrics.average_processing_time_ms
                },
                'concurrency_metrics': {
                    'active_tasks': concurrency_metrics['active_tasks']['total'],
                    'priority_queue_size': concurrency_metrics['priority_queue']['size'],
                    'resource_utilization': {
                        pool_name: pool_metrics['utilization_percent']
                        for pool_name, pool_metrics in concurrency_metrics['resource_pools'].items()
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Task manager health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }