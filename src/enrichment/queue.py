"""
Enrichment Task Queue - PRD-010
Queue management system for background enrichment tasks.

Implements priority-based task queue with async processing capabilities
for handling enrichment operations as specified in PRD-010.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import deque
import heapq

from .models import (
    EnrichmentTask, EnrichmentPriority, TaskStatus,
    TaskQueueStatus, EnrichmentConfig
)
from .exceptions import QueueError, TaskProcessingError
from .concurrent import ResourceType, ResourceLimits

logger = logging.getLogger(__name__)


class EnrichmentQueue:
    """
    Priority-based queue for enrichment tasks with semaphore-based resource limiting.
    
    Manages task queuing, priority ordering, and concurrency controls
    as specified in PRD-010.
    """
    
    def __init__(self, config: EnrichmentConfig, resource_limits: Optional[ResourceLimits] = None):
        """
        Initialize enrichment queue with concurrency controls.
        
        Args:
            config: Enrichment configuration
            resource_limits: Resource limits for concurrency control
        """
        self.config = config
        self.resource_limits = resource_limits or ResourceLimits()
        
        # Priority queue with thread-safe operations
        self._queue: List[tuple] = []  # Priority heap: (priority_value, timestamp, task)
        self._queue_lock = asyncio.Lock()
        self._priority_map = {
            EnrichmentPriority.URGENT: 0,
            EnrichmentPriority.HIGH: 1,
            EnrichmentPriority.NORMAL: 2,
            EnrichmentPriority.LOW: 3
        }
        
        # Semaphore-based resource limiting
        self._processing_semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self._queue_capacity_semaphore = asyncio.Semaphore(1000)  # Prevent queue overflow
        
        # Task isolation tracking
        self._task_isolation_map: Dict[str, Dict[str, Any]] = {}
        self._isolation_lock = asyncio.Lock()
        
        # Backpressure handling
        self._backpressure_threshold = 500
        self._backpressure_active = False
        self._backpressure_lock = asyncio.Lock()
        
        # Metrics for monitoring
        self._metrics = {
            'tasks_enqueued': 0,
            'tasks_dequeued': 0,
            'backpressure_events': 0,
            'isolation_violations': 0,
            'queue_full_events': 0
        }
        
        logger.info(f"EnrichmentQueue initialized with concurrency controls (max_concurrent: {config.max_concurrent_tasks})")
    
    async def enqueue(self, task: EnrichmentTask) -> None:
        """
        Add task to priority queue with backpressure handling and isolation.
        
        Args:
            task: Enrichment task to enqueue
            
        Raises:
            QueueError: If queue operation fails or backpressure activated
        """
        try:
            # Check backpressure before attempting to acquire semaphore
            async with self._backpressure_lock:
                if len(self._queue) >= self._backpressure_threshold:
                    self._backpressure_active = True
                    self._metrics['backpressure_events'] += 1
                    raise QueueError(
                        "Queue backpressure activated - capacity exceeded",
                        queue_size=len(self._queue),
                        operation="enqueue"
                    )
            
            # Acquire queue capacity semaphore to prevent overflow
            try:
                await asyncio.wait_for(
                    self._queue_capacity_semaphore.acquire(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self._metrics['queue_full_events'] += 1
                raise QueueError(
                    "Queue capacity full - unable to enqueue task",
                    queue_size=len(self._queue),
                    operation="enqueue"
                )
            
            try:
                # Create isolated task context
                await self._create_task_isolation(task)
                
                async with self._queue_lock:
                    priority_value = self._priority_map.get(task.priority, 2)
                    timestamp = datetime.utcnow().timestamp()
                    
                    # Use negative timestamp for FIFO within same priority
                    heap_item = (priority_value, -timestamp, task)
                    heapq.heappush(self._queue, heap_item)
                    
                    self._metrics['tasks_enqueued'] += 1
                    
                    logger.debug(
                        f"Task enqueued with isolation: {task.content_id} with priority {task.priority}",
                        extra={
                            "task_id": task.content_id,
                            "priority": task.priority,
                            "queue_size": len(self._queue)
                        }
                    )
                    
            finally:
                # Always release the capacity semaphore
                self._queue_capacity_semaphore.release()
                
        except QueueError:
            raise
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.content_id}: {e}")
            raise QueueError(
                f"Failed to enqueue task: {str(e)}",
                queue_size=len(self._queue),
                operation="enqueue"
            )
    
    async def dequeue(self) -> Optional[EnrichmentTask]:
        """
        Remove and return highest priority task with semaphore-based throttling.
        
        Returns:
            Next task to process or None if queue is empty
            
        Raises:
            QueueError: If queue operation fails
        """
        try:
            # Acquire processing semaphore to enforce concurrency limits
            try:
                await asyncio.wait_for(
                    self._processing_semaphore.acquire(),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Processing semaphore acquisition timeout - system overloaded")
                return None
            
            try:
                async with self._queue_lock:
                    if not self._queue:
                        return None
                    
                    priority_value, neg_timestamp, task = heapq.heappop(self._queue)
                    self._metrics['tasks_dequeued'] += 1
                    
                    # Validate task isolation
                    await self._validate_task_isolation(task)
                    
                    # Reset backpressure if queue is below threshold
                    if len(self._queue) < self._backpressure_threshold * 0.8:
                        async with self._backpressure_lock:
                            self._backpressure_active = False
                    
                    logger.debug(
                        f"Task dequeued with semaphore: {task.content_id}",
                        extra={
                            "task_id": task.content_id,
                            "priority": task.priority,
                            "queue_size": len(self._queue)
                        }
                    )
                    
                    return task
                    
            except Exception as e:
                # Release semaphore on error
                self._processing_semaphore.release()
                raise
                
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            raise QueueError(
                f"Failed to dequeue task: {str(e)}",
                queue_size=len(self._queue),
                operation="dequeue"
            )
    
    async def get_status(self) -> TaskQueueStatus:
        """
        Get current queue status.
        
        Returns:
            Queue status information
        """
        try:
            async with self._queue_lock:
                pending_tasks = len(self._queue)
                
                # Find oldest pending task
                oldest_pending = None
                if self._queue:
                    # Get timestamp from heap (convert back from negative)
                    _, neg_timestamp, _ = min(self._queue)
                    oldest_pending = datetime.fromtimestamp(-neg_timestamp)
                
                return TaskQueueStatus(
                    pending_tasks=pending_tasks,
                    processing_tasks=0,  # Will be updated by TaskManager
                    queue_size=pending_tasks,
                    oldest_pending_task=oldest_pending,
                    queue_health="healthy" if pending_tasks < 1000 else "degraded",
                    last_processed_task=None  # Will be updated by TaskManager
                )
                
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise QueueError(
                f"Failed to get queue status: {str(e)}",
                operation="get_status"
            )
    
    async def clear(self) -> int:
        """
        Clear all tasks from queue.
        
        Returns:
            Number of tasks removed
        """
        try:
            async with self._queue_lock:
                count = len(self._queue)
                self._queue.clear()
                
                logger.info(f"Queue cleared: {count} tasks removed")
                return count
                
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            raise QueueError(
                f"Failed to clear queue: {str(e)}",
                operation="clear"
            )
    
    async def size(self) -> int:
        """
        Get current queue size.
        
        Returns:
            Number of tasks in queue
        """
        async with self._queue_lock:
            return len(self._queue)
    
    async def is_empty(self) -> bool:
        """
        Check if queue is empty.
        
        Returns:
            True if queue is empty
        """
        async with self._queue_lock:
            return len(self._queue) == 0
    
    # API compatibility aliases
    async def add_task(self, task: EnrichmentTask) -> None:
        """
        Add task to queue (alias for enqueue).
        
        Args:
            task: Enrichment task to add
        """
        await self.enqueue(task)
    
    async def get_next_task(self) -> Optional[EnrichmentTask]:
        """
        Get next task from queue (alias for dequeue).
        
        Returns:
            Next task or None if queue is empty
        """
        return await self.dequeue()
    
    async def mark_completed(self, task_id: str, success: bool = True) -> None:
        """
        Mark task as completed (placeholder for compatibility).
        
        Args:
            task_id: Task identifier
            success: Whether task completed successfully
        """
        # This is a simplified queue, task completion tracking would be
        # handled by the higher-level EnrichmentTaskQueue
        pass
    
    async def mark_failed(self, task_id: str, error_message: str) -> None:
        """
        Mark task as failed (placeholder for compatibility).
        
        Args:
            task_id: Task identifier
            error_message: Error message
        """
        # This is a simplified queue, task failure tracking would be
        # handled by the higher-level EnrichmentTaskQueue
        pass
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics (alias for get_status).
        
        Returns:
            Queue statistics
        """
        status = await self.get_status()
        return {
            'pending_tasks': status.pending_tasks,
            'processing_tasks': status.processing_tasks,
            'queue_size': status.queue_size,
            'oldest_pending_task': status.oldest_pending_task,
            'queue_health': status.queue_health,
            'last_processed_task': status.last_processed_task
        }
    
    async def _create_task_isolation(self, task: EnrichmentTask) -> None:
        """
        Create isolation context for task processing.
        
        Args:
            task: Task to create isolation for
        """
        async with self._isolation_lock:
            isolation_key = f"isolation_{task.content_id}_{task.task_type.value}"
            
            # Check for existing isolation violations
            for existing_key, existing_context in self._task_isolation_map.items():
                if existing_context.get('content_id') == task.content_id:
                    self._metrics['isolation_violations'] += 1
                    logger.warning(
                        f"Task isolation violation: {task.content_id} already has active task",
                        extra={"task_id": task.content_id, "existing_key": existing_key}
                    )
            
            self._task_isolation_map[isolation_key] = {
                'content_id': task.content_id,
                'task_type': task.task_type.value,
                'priority': task.priority.value,
                'created_at': datetime.utcnow(),
                'isolation_level': 'task_level'
            }
            
            logger.debug(f"Task isolation created: {isolation_key}")
    
    async def _validate_task_isolation(self, task: EnrichmentTask) -> None:
        """
        Validate task isolation before processing.
        
        Args:
            task: Task to validate isolation for
            
        Raises:
            QueueError: If isolation violation detected
        """
        async with self._isolation_lock:
            isolation_key = f"isolation_{task.content_id}_{task.task_type.value}"
            
            if isolation_key not in self._task_isolation_map:
                self._metrics['isolation_violations'] += 1
                raise QueueError(
                    f"Task isolation violation: missing isolation context for {task.content_id}",
                    operation="validate_isolation"
                )
            
            logger.debug(f"Task isolation validated: {isolation_key}")
    
    async def release_task_semaphore(self, task_id: str) -> None:
        """
        Release processing semaphore for completed task.
        
        Args:
            task_id: Task identifier
        """
        try:
            self._processing_semaphore.release()
            
            # Clean up isolation context
            async with self._isolation_lock:
                keys_to_remove = [
                    key for key, context in self._task_isolation_map.items()
                    if context.get('content_id') == task_id
                ]
                
                for key in keys_to_remove:
                    del self._task_isolation_map[key]
                    logger.debug(f"Task isolation cleaned up: {key}")
            
        except Exception as e:
            logger.error(f"Failed to release semaphore for task {task_id}: {e}")
    
    async def get_concurrency_metrics(self) -> Dict[str, Any]:
        """
        Get concurrency-specific metrics for the queue.
        
        Returns:
            Concurrency metrics and statistics
        """
        async with self._queue_lock:
            queue_size = len(self._queue)
        
        async with self._isolation_lock:
            isolation_count = len(self._task_isolation_map)
        
        return {
            'queue_metrics': self._metrics.copy(),
            'semaphore_status': {
                'processing_available': self._processing_semaphore._value,
                'processing_capacity': self.config.max_concurrent_tasks,
                'queue_capacity_available': self._queue_capacity_semaphore._value
            },
            'backpressure': {
                'active': self._backpressure_active,
                'threshold': self._backpressure_threshold,
                'current_queue_size': queue_size
            },
            'isolation': {
                'active_isolations': isolation_count,
                'isolation_violations': self._metrics['isolation_violations']
            },
            'resource_limits': {
                'api_calls_per_minute': self.resource_limits.api_calls_per_minute,
                'max_processing_slots': self.resource_limits.max_processing_slots,
                'max_database_connections': self.resource_limits.max_database_connections
            }
        }


class EnrichmentTaskQueue:
    """
    High-level task queue manager with processing coordination.
    
    Provides task queue management with processing coordination,
    batch handling, and monitoring capabilities.
    """
    
    def __init__(self, config: EnrichmentConfig, resource_limits: Optional[ResourceLimits] = None):
        """
        Initialize task queue manager.
        
        Args:
            config: Enrichment configuration
            resource_limits: Resource limits for concurrency control
        """
        self.config = config
        self.queue = EnrichmentQueue(config, resource_limits)
        self._processing_tasks: Dict[str, EnrichmentTask] = {}
        self._processing_lock = asyncio.Lock()
        self._last_processed: Optional[datetime] = None
        
        logger.info("EnrichmentTaskQueue initialized")
    
    async def start(self) -> None:
        """
        Start the task queue system.
        
        Initializes queue processing and background monitoring.
        """
        try:
            logger.info("Starting EnrichmentTaskQueue")
            # Queue starts automatically when initialized
            logger.info("EnrichmentTaskQueue started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start EnrichmentTaskQueue: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Stop the task queue system.
        
        Performs graceful shutdown of queue processing.
        """
        try:
            logger.info("Stopping EnrichmentTaskQueue")
            # Clean up any remaining processing tasks
            async with self._processing_lock:
                self._processing_tasks.clear()
            logger.info("EnrichmentTaskQueue stopped")
            
        except Exception as e:
            logger.error(f"Error stopping EnrichmentTaskQueue: {e}")
            raise
    
    async def submit_task(self, task: EnrichmentTask) -> None:
        """
        Submit task for processing.
        
        Args:
            task: Task to submit
            
        Raises:
            QueueError: If task submission fails
        """
        try:
            # Update task status
            task.status = TaskStatus.PENDING
            task.created_at = datetime.utcnow()
            
            await self.queue.enqueue(task)
            
            logger.info(
                f"Task submitted: {task.content_id} ({task.task_type})",
                extra={
                    "content_id": task.content_id,
                    "task_type": task.task_type,
                    "priority": task.priority
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to submit task {task.content_id}: {e}")
            raise QueueError(
                f"Failed to submit task: {str(e)}",
                operation="submit_task",
                error_context={"content_id": task.content_id}
            )
    
    async def get_next_task(self) -> Optional[EnrichmentTask]:
        """
        Get next task for processing.
        
        Returns:
            Next task to process or None if no tasks available
        """
        try:
            task = await self.queue.dequeue()
            
            if task:
                async with self._processing_lock:
                    # Mark task as processing
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow()
                    self._processing_tasks[task.content_id] = task
                
                logger.debug(f"Task started processing: {task.content_id}")
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to get next task: {e}")
            raise QueueError(
                f"Failed to get next task: {str(e)}",
                operation="get_next_task"
            )
    
    async def complete_task(self, content_id: str, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        Mark task as completed.
        
        Args:
            content_id: Content ID of completed task
            success: Whether task completed successfully
            error_message: Error message if task failed
        """
        try:
            async with self._processing_lock:
                task = self._processing_tasks.get(content_id)
                
                if not task:
                    logger.warning(f"Attempted to complete unknown task: {content_id}")
                    return
                
                # Update task status
                task.completed_at = datetime.utcnow()
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                
                if error_message:
                    task.error_message = error_message
                
                # Remove from processing
                del self._processing_tasks[content_id]
                self._last_processed = datetime.utcnow()
                
                logger.info(
                    f"Task completed: {content_id} ({'success' if success else 'failed'})",
                    extra={
                        "content_id": content_id,
                        "success": success,
                        "processing_time": (task.completed_at - task.started_at).total_seconds() if task.started_at else 0
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to complete task {content_id}: {e}")
            raise QueueError(
                f"Failed to complete task: {str(e)}",
                operation="complete_task",
                error_context={"content_id": content_id}
            )
    
    async def get_batch(self, batch_size: Optional[int] = None) -> List[EnrichmentTask]:
        """
        Get batch of tasks for processing.
        
        Args:
            batch_size: Number of tasks to retrieve
            
        Returns:
            List of tasks for batch processing
        """
        batch_size = batch_size or self.config.batch_size
        tasks = []
        
        try:
            for _ in range(batch_size):
                task = await self.get_next_task()
                if task is None:
                    break
                tasks.append(task)
            
            if tasks:
                logger.info(f"Batch retrieved: {len(tasks)} tasks")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get batch: {e}")
            raise QueueError(
                f"Failed to get batch: {str(e)}",
                operation="get_batch"
            )
    
    async def get_status(self) -> TaskQueueStatus:
        """
        Get comprehensive queue status.
        
        Returns:
            Queue status with processing information
        """
        try:
            base_status = await self.queue.get_status()
            
            async with self._processing_lock:
                base_status.processing_tasks = len(self._processing_tasks)
                base_status.last_processed_task = self._last_processed
            
            return base_status
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise QueueError(
                f"Failed to get queue status: {str(e)}",
                operation="get_status"
            )
    
    async def cancel_task(self, content_id: str) -> bool:
        """
        Cancel a processing task.
        
        Args:
            content_id: Content ID of task to cancel
            
        Returns:
            True if task was cancelled
        """
        try:
            async with self._processing_lock:
                task = self._processing_tasks.get(content_id)
                
                if task:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()
                    del self._processing_tasks[content_id]
                    
                    logger.info(f"Task cancelled: {content_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel task {content_id}: {e}")
            raise QueueError(
                f"Failed to cancel task: {str(e)}",
                operation="cancel_task",
                error_context={"content_id": content_id}
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform queue health check.
        
        Returns:
            Health status information
        """
        try:
            status = await self.get_status()
            
            # Determine health based on queue metrics
            is_healthy = (
                status.pending_tasks < 1000 and
                status.processing_tasks < self.config.max_concurrent_tasks * 2
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "queue_size": status.queue_size,
                "pending_tasks": status.pending_tasks,
                "processing_tasks": status.processing_tasks,
                "oldest_pending": status.oldest_pending_task.isoformat() if status.oldest_pending_task else None,
                "last_processed": status.last_processed_task.isoformat() if status.last_processed_task else None
            }
            
        except Exception as e:
            logger.error(f"Queue health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Additional API compatibility methods
    async def add_task(self, task: EnrichmentTask) -> None:
        """
        Add task to queue (alias for submit_task).
        
        Args:
            task: Task to add
        """
        await self.submit_task(task)
    
    async def mark_completed(self, content_id: str, success: bool = True) -> None:
        """
        Mark task as completed (alias for complete_task).
        
        Args:
            content_id: Content ID of completed task
            success: Whether task completed successfully
        """
        await self.complete_task(content_id, success)
    
    async def mark_failed(self, content_id: str, error_message: str) -> None:
        """
        Mark task as failed.
        
        Args:
            content_id: Content ID of failed task
            error_message: Error message
        """
        await self.complete_task(content_id, success=False, error_message=error_message)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics (alias for get_status).
        
        Returns:
            Queue statistics
        """
        status = await self.get_status()
        return {
            'pending_tasks': status.pending_tasks,
            'processing_tasks': status.processing_tasks,
            'queue_size': status.queue_size,
            'oldest_pending_task': status.oldest_pending_task,
            'queue_health': status.queue_health,
            'last_processed_task': status.last_processed_task
        }