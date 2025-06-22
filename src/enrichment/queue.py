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

logger = logging.getLogger(__name__)


class EnrichmentQueue:
    """
    Priority-based queue for enrichment tasks.
    
    Manages task queuing, priority ordering, and basic queue operations
    as specified in PRD-010.
    """
    
    def __init__(self, config: EnrichmentConfig):
        """
        Initialize enrichment queue.
        
        Args:
            config: Enrichment configuration
        """
        self.config = config
        self._queue: List[tuple] = []  # Priority heap: (priority_value, timestamp, task)
        self._queue_lock = asyncio.Lock()
        self._priority_map = {
            EnrichmentPriority.URGENT: 0,
            EnrichmentPriority.HIGH: 1,
            EnrichmentPriority.NORMAL: 2,
            EnrichmentPriority.LOW: 3
        }
        
        logger.info("EnrichmentQueue initialized")
    
    async def enqueue(self, task: EnrichmentTask) -> None:
        """
        Add task to priority queue.
        
        Args:
            task: Enrichment task to enqueue
            
        Raises:
            QueueError: If queue operation fails
        """
        try:
            async with self._queue_lock:
                priority_value = self._priority_map.get(task.priority, 2)
                timestamp = datetime.utcnow().timestamp()
                
                # Use negative timestamp for FIFO within same priority
                heap_item = (priority_value, -timestamp, task)
                heapq.heappush(self._queue, heap_item)
                
                logger.debug(
                    f"Task enqueued: {task.content_id} with priority {task.priority}",
                    extra={"task_id": task.content_id, "priority": task.priority}
                )
                
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.content_id}: {e}")
            raise QueueError(
                f"Failed to enqueue task: {str(e)}",
                queue_size=len(self._queue),
                operation="enqueue"
            )
    
    async def dequeue(self) -> Optional[EnrichmentTask]:
        """
        Remove and return highest priority task.
        
        Returns:
            Next task to process or None if queue is empty
            
        Raises:
            QueueError: If queue operation fails
        """
        try:
            async with self._queue_lock:
                if not self._queue:
                    return None
                
                priority_value, neg_timestamp, task = heapq.heappop(self._queue)
                
                logger.debug(
                    f"Task dequeued: {task.content_id}",
                    extra={"task_id": task.content_id, "priority": task.priority}
                )
                
                return task
                
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


class EnrichmentTaskQueue:
    """
    High-level task queue manager with processing coordination.
    
    Provides task queue management with processing coordination,
    batch handling, and monitoring capabilities.
    """
    
    def __init__(self, config: EnrichmentConfig):
        """
        Initialize task queue manager.
        
        Args:
            config: Enrichment configuration
        """
        self.config = config
        self.queue = EnrichmentQueue(config)
        self._processing_tasks: Dict[str, EnrichmentTask] = {}
        self._processing_lock = asyncio.Lock()
        self._last_processed: Optional[datetime] = None
        
        logger.info("EnrichmentTaskQueue initialized")
    
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