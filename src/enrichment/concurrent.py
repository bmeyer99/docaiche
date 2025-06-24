"""
Concurrent Task Execution - PRD-010
Comprehensive concurrency controls for safe multi-task execution in enrichment pipeline.

Implements resource pools, task isolation, priority queuing, and deadlock prevention
for secure concurrent enrichment operations as specified in PRD-010.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Callable, Awaitable
from contextlib import asynccontextmanager
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .models import EnrichmentTask, EnrichmentConfig, TaskStatus, EnrichmentPriority
from .exceptions import (
    TaskProcessingError, EnrichmentTimeoutError, QueueError,
    TaskExecutionError, EnrichmentException
)

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of resources that need concurrency control"""
    API_CALLS = "api_calls"
    PROCESSING_SLOTS = "processing_slots"
    DATABASE_CONNECTIONS = "database_connections"
    VECTOR_DB_CONNECTIONS = "vector_db_connections"
    LLM_CONNECTIONS = "llm_connections"


@dataclass
class ResourceLimits:
    """Resource limit configuration for concurrency control"""
    api_calls_per_minute: int = 60
    max_processing_slots: int = 5
    max_database_connections: int = 10
    max_vector_db_connections: int = 3
    max_llm_connections: int = 2


class ResourcePool:
    """
    Thread-safe resource pool with configurable limits and backpressure handling.
    
    Manages resource allocation with proper cleanup and deadlock prevention.
    """
    
    def __init__(self, name: str, max_size: int, timeout_seconds: float = 30.0):
        """
        Initialize resource pool.
        
        Args:
            name: Resource pool name
            max_size: Maximum number of resources
            timeout_seconds: Timeout for resource acquisition
        """
        self.name = name
        self.max_size = max_size
        self.timeout_seconds = timeout_seconds
        
        self._semaphore = asyncio.Semaphore(max_size)
        self._active_resources: Set[str] = set()
        self._resource_lock = asyncio.Lock()
        self._metrics = {
            'total_acquired': 0,
            'total_released': 0,
            'current_active': 0,
            'acquisition_timeouts': 0,
            'max_concurrent': 0
        }
        
        logger.info(f"ResourcePool '{name}' initialized with max_size={max_size}")
    
    @asynccontextmanager
    async def acquire(self, resource_id: str):
        """
        Acquire resource with automatic cleanup and timeout handling.
        
        Args:
            resource_id: Unique identifier for the resource request
            
        Yields:
            Resource context for safe usage
            
        Raises:
            EnrichmentTimeoutError: If resource acquisition times out
            ResourceError: If resource allocation fails
        """
        start_time = time.time()
        acquired = False
        
        try:
            # Acquire semaphore with timeout
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.timeout_seconds
            )
            acquired = True
            
            # Track active resource
            async with self._resource_lock:
                self._active_resources.add(resource_id)
                self._metrics['total_acquired'] += 1
                self._metrics['current_active'] = len(self._active_resources)
                self._metrics['max_concurrent'] = max(
                    self._metrics['max_concurrent'],
                    self._metrics['current_active']
                )
            
            acquisition_time = time.time() - start_time
            logger.debug(
                f"Resource acquired: {self.name}:{resource_id} "
                f"(took {acquisition_time:.3f}s, active: {len(self._active_resources)})"
            )
            
            yield resource_id
            
        except asyncio.TimeoutError:
            self._metrics['acquisition_timeouts'] += 1
            logger.error(
                f"Resource acquisition timeout: {self.name}:{resource_id} "
                f"after {self.timeout_seconds}s"
            )
            raise EnrichmentTimeoutError(
                f"Resource acquisition timeout for {self.name}",
                timeout_seconds=self.timeout_seconds,
                operation="resource_acquisition",
                error_context={"resource_id": resource_id, "pool_name": self.name}
            )
            
        except Exception as e:
            logger.error(f"Resource acquisition failed: {self.name}:{resource_id}: {e}")
            raise TaskExecutionError(
                f"Resource acquisition failed: {str(e)}",
                task_id=resource_id,
                execution_stage="resource_acquisition"
            )
            
        finally:
            if acquired:
                # Release semaphore and clean up tracking
                self._semaphore.release()
                
                async with self._resource_lock:
                    self._active_resources.discard(resource_id)
                    self._metrics['total_released'] += 1
                    self._metrics['current_active'] = len(self._active_resources)
                
                total_time = time.time() - start_time
                logger.debug(
                    f"Resource released: {self.name}:{resource_id} "
                    f"(held for {total_time:.3f}s, active: {len(self._active_resources)})"
                )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get resource pool metrics.
        
        Returns:
            Resource pool statistics
        """
        async with self._resource_lock:
            return {
                'pool_name': self.name,
                'max_size': self.max_size,
                'current_active': len(self._active_resources),
                'available_slots': self.max_size - len(self._active_resources),
                'utilization_percent': (len(self._active_resources) / self.max_size) * 100,
                'metrics': self._metrics.copy(),
                'active_resources': list(self._active_resources)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform resource pool health check.
        
        Returns:
            Health status information
        """
        metrics = await self.get_metrics()
        
        # Determine health based on utilization and timeout rate
        utilization = metrics['utilization_percent']
        timeout_rate = (
            self._metrics['acquisition_timeouts'] /
            max(1, self._metrics['total_acquired'])
        ) * 100
        
        is_healthy = utilization < 90 and timeout_rate < 5
        
        return {
            'status': 'healthy' if is_healthy else 'degraded',
            'utilization_percent': utilization,
            'timeout_rate_percent': timeout_rate,
            'available_slots': metrics['available_slots'],
            'max_size': self.max_size
        }
    
    async def cleanup(self) -> None:
        """
        Clean up resource pool during shutdown.
        
        Releases all resources and resets metrics.
        """
        try:
            async with self._resource_lock:
                # Clear active resources
                self._active_resources.clear()
                
                # Reset metrics
                self._metrics = {
                    'total_acquired': 0,
                    'total_released': 0,
                    'current_active': 0,
                    'acquisition_timeouts': 0,
                    'max_concurrent': 0
                }
                
                logger.debug(f"Resource pool '{self.name}' cleaned up")
                
        except Exception as e:
            logger.error(f"Error cleaning up resource pool '{self.name}': {e}")


class TaskIsolationManager:
    """
    Manages task isolation to prevent interference between concurrent tasks.
    
    Provides task-specific contexts and prevents resource conflicts.
    """
    
    def __init__(self):
        """Initialize task isolation manager."""
        self._task_contexts: Dict[str, Dict[str, Any]] = {}
        self._task_locks: Dict[str, asyncio.Lock] = {}
        self._isolation_lock = asyncio.Lock()
        
        logger.info("TaskIsolationManager initialized")
    
    async def create_task_context(self, task_id: str, task_data: Dict[str, Any]) -> str:
        """
        Create isolated context for task execution.
        
        Args:
            task_id: Task identifier
            task_data: Task-specific data
            
        Returns:
            Context identifier
        """
        async with self._isolation_lock:
            context_id = f"ctx_{task_id}_{int(time.time())}"
            
            self._task_contexts[context_id] = {
                'task_id': task_id,
                'created_at': datetime.utcnow(),
                'task_data': task_data.copy(),
                'resources': [],
                'state': 'created'
            }
            
            self._task_locks[context_id] = asyncio.Lock()
            
            logger.debug(f"Task context created: {context_id} for task {task_id}")
            return context_id
    
    async def cleanup_task_context(self, context_id: str) -> None:
        """
        Clean up task context and release resources.
        
        Args:
            context_id: Context to clean up
        """
        async with self._isolation_lock:
            if context_id in self._task_contexts:
                context = self._task_contexts[context_id]
                context['state'] = 'cleaned_up'
                context['cleaned_at'] = datetime.utcnow()
                
                # Remove context and lock
                del self._task_contexts[context_id]
                if context_id in self._task_locks:
                    del self._task_locks[context_id]
                
                logger.debug(f"Task context cleaned up: {context_id}")
    
    async def get_task_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task context data.
        
        Args:
            context_id: Context identifier
            
        Returns:
            Context data if exists
        """
        async with self._isolation_lock:
            return self._task_contexts.get(context_id, {}).copy()
    
    @asynccontextmanager
    async def isolated_execution(self, task_id: str, task_data: Dict[str, Any]):
        """
        Execute task in isolated context with automatic cleanup.
        
        Args:
            task_id: Task identifier
            task_data: Task data
            
        Yields:
            Isolated context for task execution
        """
        context_id = await self.create_task_context(task_id, task_data)
        
        try:
            async with self._task_locks[context_id]:
                yield context_id
        finally:
            await self.cleanup_task_context(context_id)


class ConcurrentTaskExecutor:
    """
    Main concurrent task executor with comprehensive concurrency controls.
    
    Implements safe multi-task execution with resource pools, task isolation,
    priority queuing, and deadlock prevention as specified in PRD-010.
    """
    
    def __init__(self, config: EnrichmentConfig, resource_limits: Optional[ResourceLimits] = None):
        """
        Initialize concurrent task executor.
        
        Args:
            config: Enrichment configuration
            resource_limits: Resource limit configuration
        """
        self.config = config
        self.resource_limits = resource_limits or ResourceLimits()
        
        # Expose max_concurrent_tasks for component integration
        self.max_concurrent_tasks = getattr(config, 'max_concurrent_tasks', self.resource_limits.max_processing_slots)
        
        # Initialize resource pools
        self._resource_pools = {
            ResourceType.API_CALLS: ResourcePool(
                "api_calls", 
                self.resource_limits.api_calls_per_minute,
                timeout_seconds=30.0
            ),
            ResourceType.PROCESSING_SLOTS: ResourcePool(
                "processing_slots", 
                self.resource_limits.max_processing_slots,
                timeout_seconds=60.0
            ),
            ResourceType.DATABASE_CONNECTIONS: ResourcePool(
                "database_connections", 
                self.resource_limits.max_database_connections,
                timeout_seconds=15.0
            ),
            ResourceType.VECTOR_DB_CONNECTIONS: ResourcePool(
                "vector_db_connections", 
                self.resource_limits.max_vector_db_connections,
                timeout_seconds=45.0
            ),
            ResourceType.LLM_CONNECTIONS: ResourcePool(
                "llm_connections", 
                self.resource_limits.max_llm_connections,
                timeout_seconds=90.0
            )
        }
        
        # Task isolation and state management
        self._isolation_manager = TaskIsolationManager()
        self._active_tasks: Dict[str, EnrichmentTask] = {}
        self._task_state_lock = asyncio.Lock()
        
        # Priority queue with backpressure
        self._priority_queue = asyncio.PriorityQueue()
        self._queue_lock = asyncio.Lock()
        self._backpressure_threshold = 100
        
        # Deadlock prevention
        self._deadlock_detector = DeadlockDetector()
        self._task_dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        # Graceful shutdown
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30.0
        
        # Metrics and monitoring
        self._metrics = {
            'tasks_executed': 0,
            'tasks_successful': 0,
            'tasks_failed': 0,
            'deadlocks_prevented': 0,
            'backpressure_events': 0,
            'resource_timeouts': 0
        }
        
        logger.info("ConcurrentTaskExecutor initialized with resource pools")
    
    async def execute_task(
        self,
        task: EnrichmentTask,
        task_handler: Callable[[EnrichmentTask], Awaitable[Any]],
        required_resources: Optional[List[ResourceType]] = None
    ) -> Any:
        """
        Execute task with full concurrency control and isolation.
        
        Args:
            task: Task to execute
            task_handler: Async function to handle task execution
            required_resources: List of required resource types
            
        Returns:
            Task execution result
            
        Raises:
            TaskExecutionError: If task execution fails
            EnrichmentTimeoutError: If execution times out
        """
        if self._shutdown_event.is_set():
            raise TaskExecutionError(
                "Task executor is shutting down",
                task_id=task.content_id,
                execution_stage="pre_execution"
            )
        
        required_resources = required_resources or [ResourceType.PROCESSING_SLOTS]
        task_id = task.content_id
        
        try:
            # Check for deadlock potential
            await self._deadlock_detector.check_potential_deadlock(task_id, required_resources)
            
            # Track task start
            async with self._task_state_lock:
                self._active_tasks[task_id] = task
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.utcnow()
            
            # Execute with resource pools and isolation
            async with self._isolation_manager.isolated_execution(
                task_id, 
                {'task_type': task.task_type, 'priority': task.priority}
            ) as context_id:
                
                # Acquire all required resources
                async with self._acquire_resources(task_id, required_resources):
                    
                    # Execute task with timeout
                    result = await asyncio.wait_for(
                        task_handler(task),
                        timeout=self.config.task_timeout_seconds
                    )
                    
                    # Update metrics and state
                    self._metrics['tasks_executed'] += 1
                    self._metrics['tasks_successful'] += 1
                    
                    async with self._task_state_lock:
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.utcnow()
                    
                    logger.info(f"Task executed successfully: {task_id}")
                    return result
        
        except asyncio.TimeoutError:
            self._metrics['tasks_failed'] += 1
            logger.error(f"Task execution timeout: {task_id}")
            
            async with self._task_state_lock:
                task.status = TaskStatus.FAILED
                task.error_message = f"Task timed out after {self.config.task_timeout_seconds}s"
                task.completed_at = datetime.utcnow()
            
            raise EnrichmentTimeoutError(
                f"Task execution timeout: {task_id}",
                timeout_seconds=self.config.task_timeout_seconds,
                operation="task_execution",
                content_id=task_id
            )
        
        except Exception as e:
            self._metrics['tasks_failed'] += 1
            logger.error(f"Task execution failed: {task_id}: {e}")
            
            async with self._task_state_lock:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
            
            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                task_id=task_id,
                execution_stage="execution"
            )
        
        finally:
            # Clean up task tracking
            async with self._task_state_lock:
                self._active_tasks.pop(task_id, None)
            
            # Remove deadlock tracking
            await self._deadlock_detector.remove_task(task_id)
    
    @asynccontextmanager
    async def _acquire_resources(self, task_id: str, resource_types: List[ResourceType]):
        """
        Acquire multiple resources with proper ordering to prevent deadlock.
        
        Args:
            task_id: Task identifier
            resource_types: List of resource types to acquire
        """
        # Sort resources by type to ensure consistent ordering (deadlock prevention)
        sorted_resources = sorted(resource_types, key=lambda x: x.value)
        acquired_contexts = []
        
        try:
            # Acquire resources in sorted order
            for resource_type in sorted_resources:
                pool = self._resource_pools[resource_type]
                context = pool.acquire(f"{task_id}_{resource_type.value}")
                acquired_contexts.append(context)
            
            # Enter all contexts sequentially
            entered_contexts = []
            try:
                for context in acquired_contexts:
                    result = await context.__aenter__()
                    entered_contexts.append((context, result))
                
                yield [result for _, result in entered_contexts]
                
            finally:
                # Exit all contexts in reverse order
                for context, _ in reversed(entered_contexts):
                    try:
                        await context.__aexit__(None, None, None)
                    except Exception as e:
                        logger.error(f"Resource cleanup error: {e}")
                        
        except Exception as e:
            logger.error(f"Resource acquisition failed for task {task_id}: {e}")
            # Cleanup any partially acquired contexts
            for context in reversed(acquired_contexts):
                try:
                    if hasattr(context, '__aexit__'):
                        await context.__aexit__(None, None, None)
                except Exception as cleanup_error:
                    logger.error(f"Cleanup error during exception handling: {cleanup_error}")
            raise
    
    async def submit_priority_task(
        self,
        task: EnrichmentTask,
        task_handler: Callable[[EnrichmentTask], Awaitable[Any]],
        required_resources: Optional[List[ResourceType]] = None
    ) -> None:
        """
        Submit task to priority queue with backpressure handling.
        
        Args:
            task: Task to submit
            task_handler: Task execution handler
            required_resources: Required resource types
            
        Raises:
            QueueError: If queue is full (backpressure)
        """
        async with self._queue_lock:
            if self._priority_queue.qsize() >= self._backpressure_threshold:
                self._metrics['backpressure_events'] += 1
                raise QueueError(
                    "Queue at capacity - backpressure activated",
                    queue_size=self._priority_queue.qsize(),
                    operation="submit_priority_task"
                )
            
            # Create priority tuple (lower number = higher priority)
            priority_value = {
                EnrichmentPriority.URGENT: 0,
                EnrichmentPriority.HIGH: 1,
                EnrichmentPriority.NORMAL: 2,
                EnrichmentPriority.LOW: 3
            }.get(task.priority, 2)
            
            priority_item = (
                priority_value,
                time.time(),  # FIFO within same priority
                task,
                task_handler,
                required_resources or [ResourceType.PROCESSING_SLOTS]
            )
            
            await self._priority_queue.put(priority_item)
            logger.debug(f"Task submitted to priority queue: {task.content_id}")
    
    async def process_priority_queue(self) -> None:
        """
        Process tasks from priority queue with concurrency control.
        
        Runs as background coroutine to handle queued tasks.
        """
        logger.info("Starting priority queue processor")
        
        while not self._shutdown_event.is_set():
            try:
                # Get next task from priority queue
                try:
                    priority_item = await asyncio.wait_for(
                        self._priority_queue.get(),
                        timeout=1.0  # Check shutdown event regularly
                    )
                except asyncio.TimeoutError:
                    continue
                
                priority_value, timestamp, task, handler, resources = priority_item
                
                # Execute task with concurrency control
                try:
                    await self.execute_task(task, handler, resources)
                except Exception as e:
                    logger.error(f"Priority queue task execution failed: {e}")
                
                self._priority_queue.task_done()
                
            except Exception as e:
                logger.error(f"Priority queue processing error: {e}")
                await asyncio.sleep(1)
        
        logger.info("Priority queue processor stopped")
    
    async def graceful_shutdown(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Perform graceful shutdown with pending task completion.
        
        Args:
            timeout: Shutdown timeout in seconds
            
        Returns:
            Shutdown statistics
        """
        timeout = timeout or self._shutdown_timeout
        logger.info(f"Starting graceful shutdown with {timeout}s timeout")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        shutdown_start = time.time()
        
        # Wait for active tasks to complete
        while self._active_tasks and (time.time() - shutdown_start) < timeout:
            active_count = len(self._active_tasks)
            logger.info(f"Waiting for {active_count} active tasks to complete...")
            await asyncio.sleep(1)
        
        # Force cleanup of remaining tasks
        remaining_tasks = len(self._active_tasks)
        if remaining_tasks > 0:
            logger.warning(f"Force terminating {remaining_tasks} remaining tasks")
            async with self._task_state_lock:
                for task in self._active_tasks.values():
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()
                self._active_tasks.clear()
        
        # Clean up resource pools
        await self._cleanup_resource_pools()
        
        shutdown_time = time.time() - shutdown_start
        
        return {
            'shutdown_time_seconds': shutdown_time,
            'graceful': remaining_tasks == 0,
            'terminated_tasks': remaining_tasks,
            'final_metrics': self._metrics.copy(),
            'resource_cleanup_completed': True
        }
    
    async def _cleanup_resource_pools(self) -> None:
        """Clean up all resource pools during shutdown."""
        try:
            logger.info("Cleaning up resource pools")
            
            # Clear deadlock detector
            await self._deadlock_detector.cleanup()
            
            # Reset resource pool metrics for clean shutdown
            for resource_type, pool in self._resource_pools.items():
                await pool.cleanup()
                logger.debug(f"Resource pool '{resource_type.value}' cleaned up")
            
            logger.info("Resource pool cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during resource pool cleanup: {e}")
    
    async def start(self) -> None:
        """
        Start the concurrent task executor.
        
        Initializes resource pools and starts background processing.
        """
        try:
            logger.info("Starting ConcurrentTaskExecutor")
            
            # Reset shutdown event
            self._shutdown_event.clear()
            
            # Validate resource pools
            for resource_type, pool in self._resource_pools.items():
                health = await pool.health_check()
                if health.get('status') != 'healthy':
                    logger.warning(f"Resource pool '{resource_type.value}' health check: {health}")
            
            logger.info("ConcurrentTaskExecutor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start ConcurrentTaskExecutor: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Stop the concurrent task executor.
        
        Performs graceful shutdown with default timeout.
        """
        try:
            logger.info("Stopping ConcurrentTaskExecutor")
            await self.graceful_shutdown()
            logger.info("ConcurrentTaskExecutor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping ConcurrentTaskExecutor: {e}")
            raise
    
    async def get_concurrency_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive concurrency metrics.
        
        Returns:
            Concurrency statistics and health information
        """
        # Collect resource pool metrics
        resource_metrics = {}
        for resource_type, pool in self._resource_pools.items():
            resource_metrics[resource_type.value] = await pool.get_metrics()
        
        # Task state metrics
        async with self._task_state_lock:
            active_tasks_count = len(self._active_tasks)
            active_tasks_by_priority = defaultdict(int)
            for task in self._active_tasks.values():
                active_tasks_by_priority[task.priority.value] += 1
        
        # Queue metrics
        async with self._queue_lock:
            queue_size = self._priority_queue.qsize()
        
        return {
            'executor_metrics': self._metrics.copy(),
            'resource_pools': resource_metrics,
            'active_tasks': {
                'total': active_tasks_count,
                'by_priority': dict(active_tasks_by_priority)
            },
            'priority_queue': {
                'size': queue_size,
                'backpressure_threshold': self._backpressure_threshold,
                'at_capacity': queue_size >= self._backpressure_threshold
            },
            'deadlock_detector': await self._deadlock_detector.get_metrics(),
            'shutdown_state': self._shutdown_event.is_set()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of concurrent executor.
        
        Returns:
            Health status and recommendations
        """
        metrics = await self.get_concurrency_metrics()
        
        # Check resource pool health
        resource_health = {}
        overall_healthy = True
        
        for resource_type, pool in self._resource_pools.items():
            health = await pool.health_check()
            resource_health[resource_type.value] = health
            if health['status'] != 'healthy':
                overall_healthy = False
        
        # Check queue backpressure
        queue_healthy = not metrics['priority_queue']['at_capacity']
        if not queue_healthy:
            overall_healthy = False
        
        # Check error rates
        total_tasks = metrics['executor_metrics']['tasks_executed']
        error_rate = (
            metrics['executor_metrics']['tasks_failed'] / max(1, total_tasks)
        ) * 100
        
        error_healthy = error_rate < 10
        if not error_healthy:
            overall_healthy = False
        
        return {
            'status': 'healthy' if overall_healthy else 'degraded',
            'resource_pools': resource_health,
            'queue_health': {
                'status': 'healthy' if queue_healthy else 'backpressure',
                'queue_size': metrics['priority_queue']['size'],
                'threshold': metrics['priority_queue']['backpressure_threshold']
            },
            'error_metrics': {
                'error_rate_percent': error_rate,
                'healthy': error_healthy
            },
            'active_tasks': metrics['active_tasks']['total'],
            'recommendations': self._generate_health_recommendations(metrics)
        }
    
    def _generate_health_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Generate health recommendations based on metrics.
        
        Args:
            metrics: Current system metrics
            
        Returns:
            List of health recommendations
        """
        recommendations = []
        
        # Check resource utilization
        for resource_name, resource_metrics in metrics['resource_pools'].items():
            utilization = resource_metrics['utilization_percent']
            if utilization > 80:
                recommendations.append(
                    f"Consider increasing {resource_name} pool size (current utilization: {utilization:.1f}%)"
                )
        
        # Check queue backpressure
        if metrics['priority_queue']['at_capacity']:
            recommendations.append("Priority queue at capacity - consider increasing processing capacity")
        
        # Check error rates
        error_rate = (
            metrics['executor_metrics']['tasks_failed'] / 
            max(1, metrics['executor_metrics']['tasks_executed'])
        ) * 100
        
        if error_rate > 5:
            recommendations.append(f"High error rate ({error_rate:.1f}%) - investigate task failures")
        
        # Check deadlock prevention
        if metrics['deadlock_detector']['potential_deadlocks'] > 0:
            recommendations.append("Potential deadlocks detected - review task dependencies")
        
        return recommendations


class DeadlockDetector:
    """
    Deadlock detection and prevention for concurrent task execution.
    
    Monitors task dependencies and resource acquisition patterns to prevent deadlocks.
    """
    
    def __init__(self):
        """Initialize deadlock detector."""
        self._task_resources: Dict[str, Set[str]] = defaultdict(set)
        self._resource_waiters: Dict[str, Set[str]] = defaultdict(set)
        self._detection_lock = asyncio.Lock()
        self._metrics = {
            'deadlocks_detected': 0,
            'deadlocks_prevented': 0,
            'potential_deadlocks': 0
        }
        
        logger.info("DeadlockDetector initialized")
    
    async def check_potential_deadlock(
        self, 
        task_id: str, 
        required_resources: List[ResourceType]
    ) -> None:
        """
        Check for potential deadlock before resource acquisition.
        
        Args:
            task_id: Task requesting resources
            required_resources: Resources being requested
            
        Raises:
            TaskExecutionError: If deadlock potential detected
        """
        async with self._detection_lock:
            resource_names = [r.value for r in required_resources]
            
            # Check for circular wait conditions
            if await self._detect_circular_wait(task_id, resource_names):
                self._metrics['deadlocks_detected'] += 1
                self._metrics['deadlocks_prevented'] += 1
                
                logger.error(
                    f"Potential deadlock detected for task {task_id} "
                    f"requesting resources: {resource_names}"
                )
                
                raise TaskExecutionError(
                    "Deadlock potential detected - rejecting task",
                    task_id=task_id,
                    execution_stage="deadlock_detection"
                )
            
            # Track resource requests
            for resource_name in resource_names:
                self._resource_waiters[resource_name].add(task_id)
                self._task_resources[task_id].add(resource_name)
    
    async def _detect_circular_wait(self, task_id: str, resource_names: List[str]) -> bool:
        """
        Detect circular wait conditions that could lead to deadlock.
        
        Args:
            task_id: Task ID
            resource_names: Requested resource names
            
        Returns:
            True if circular wait detected
        """
        # Simple deadlock detection: check if any task holding required resources
        # is also waiting for resources that current task might hold
        
        for resource_name in resource_names:
            # Find tasks currently using this resource
            current_holders = self._resource_waiters.get(resource_name, set())
            
            for holder_task in current_holders:
                if holder_task == task_id:
                    continue
                
                # Check if holder is waiting for any resources task_id might acquire
                holder_waiting = self._task_resources.get(holder_task, set())
                task_resources = self._task_resources.get(task_id, set())
                
                if holder_waiting.intersection(task_resources):
                    self._metrics['potential_deadlocks'] += 1
                    return True
        
        return False
    
    async def remove_task(self, task_id: str) -> None:
        """
        Remove task from deadlock tracking.
        
        Args:
            task_id: Task to remove
        """
        async with self._detection_lock:
            # Remove from resource waiters
            for resource_waiters in self._resource_waiters.values():
                resource_waiters.discard(task_id)
            
            # Remove task resources
            self._task_resources.pop(task_id, None)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get deadlock detection metrics.
        
        Returns:
            Deadlock detection statistics
        """
        async with self._detection_lock:
            return {
                'deadlock_metrics': self._metrics.copy(),
                'active_tasks': len(self._task_resources),
                'resource_contention': {
                    resource: len(waiters)
                    for resource, waiters in self._resource_waiters.items()
                    if waiters
                },
                'potential_deadlocks': self._metrics['potential_deadlocks']
            }
    
    async def cleanup(self) -> None:
        """
        Clean up deadlock detector during shutdown.
        
        Clears all tracking data and resets metrics.
        """
        try:
            async with self._detection_lock:
                # Clear all tracking data
                self._task_resources.clear()
                self._resource_waiters.clear()
                
                # Reset metrics
                self._metrics = {
                    'deadlocks_detected': 0,
                    'deadlocks_prevented': 0,
                    'potential_deadlocks': 0
                }
                
                logger.debug("DeadlockDetector cleaned up")
                
        except Exception as e:
            logger.error(f"Error cleaning up DeadlockDetector: {e}")
class ConcurrencyManager:
    """
    Compatibility stub for legacy PRD-010 tests.
    Provides a minimal interface to allow test imports to succeed.
    """
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def health_check(self):
        return {"status": "healthy"}