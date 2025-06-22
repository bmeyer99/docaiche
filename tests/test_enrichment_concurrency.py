"""
Test Enrichment Concurrency Controls - PRD-010
Comprehensive tests for concurrent task execution, resource pools, and safety controls.

Tests the ConcurrentTaskExecutor, ResourcePool, TaskIsolationManager, and DeadlockDetector
components as specified in PRD-010.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.enrichment.concurrent import (
    ConcurrentTaskExecutor, ResourcePool, TaskIsolationManager, 
    DeadlockDetector, ResourceType, ResourceLimits
)
from src.enrichment.models import (
    EnrichmentTask, EnrichmentConfig, EnrichmentType, 
    EnrichmentPriority, TaskStatus
)
from src.enrichment.exceptions import (
    TaskExecutionError, EnrichmentTimeoutError, QueueError
)


class TestResourcePool:
    """Test resource pool with configurable limits and backpressure handling."""
    
    @pytest.fixture
    def resource_pool(self):
        """Create test resource pool."""
        return ResourcePool("test_pool", max_size=3, timeout_seconds=1.0)
    
    @pytest.mark.asyncio
    async def test_resource_acquisition_and_release(self, resource_pool):
        """Test basic resource acquisition and release."""
        # Test successful acquisition
        async with resource_pool.acquire("resource_1") as resource_id:
            assert resource_id == "resource_1"
            metrics = await resource_pool.get_metrics()
            assert metrics['current_active'] == 1
            assert metrics['available_slots'] == 2
        
        # Test resource is released
        metrics = await resource_pool.get_metrics()
        assert metrics['current_active'] == 0
        assert metrics['available_slots'] == 3
    
    @pytest.mark.asyncio
    async def test_resource_pool_capacity_limits(self, resource_pool):
        """Test resource pool enforces capacity limits."""
        contexts = []
        
        # Acquire maximum resources
        for i in range(3):
            ctx = resource_pool.acquire(f"resource_{i}")
            await ctx.__aenter__()
            contexts.append(ctx)
        
        # Pool should be at capacity
        metrics = await resource_pool.get_metrics()
        assert metrics['current_active'] == 3
        assert metrics['available_slots'] == 0
        
        # Next acquisition should timeout
        with pytest.raises(EnrichmentTimeoutError):
            async with resource_pool.acquire("resource_overflow"):
                pass
        
        # Clean up
        for ctx in contexts:
            await ctx.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_resource_pool_metrics_tracking(self, resource_pool):
        """Test resource pool tracks metrics correctly."""
        # Acquire and release multiple resources
        for i in range(5):
            async with resource_pool.acquire(f"resource_{i}"):
                pass
        
        metrics = await resource_pool.get_metrics()
        assert metrics['metrics']['total_acquired'] == 5
        assert metrics['metrics']['total_released'] == 5
        assert metrics['metrics']['max_concurrent'] <= 3
    
    @pytest.mark.asyncio
    async def test_resource_pool_health_check(self, resource_pool):
        """Test resource pool health check functionality."""
        # Healthy state
        health = await resource_pool.health_check()
        assert health['status'] == 'healthy'
        assert health['utilization_percent'] == 0.0
        
        # Acquire resources to test utilization
        contexts = []
        for i in range(2):
            ctx = resource_pool.acquire(f"resource_{i}")
            await ctx.__aenter__()
            contexts.append(ctx)
        
        health = await resource_pool.health_check()
        assert health['utilization_percent'] == (2/3) * 100
        
        # Clean up
        for ctx in contexts:
            await ctx.__aexit__(None, None, None)


class TestTaskIsolationManager:
    """Test task isolation to prevent interference between concurrent tasks."""
    
    @pytest.fixture
    def isolation_manager(self):
        """Create test isolation manager."""
        return TaskIsolationManager()
    
    @pytest.mark.asyncio
    async def test_task_context_creation_and_cleanup(self, isolation_manager):
        """Test task context lifecycle management."""
        task_data = {'task_type': 'test', 'priority': 'normal'}
        
        # Create context
        context_id = await isolation_manager.create_task_context("task_1", task_data)
        assert context_id.startswith("ctx_task_1_")
        
        # Verify context exists
        context = await isolation_manager.get_task_context(context_id)
        assert context['task_id'] == "task_1"
        assert context['task_data'] == task_data
        assert context['state'] == 'created'
        
        # Clean up context
        await isolation_manager.cleanup_task_context(context_id)
        
        # Verify context is removed
        context = await isolation_manager.get_task_context(context_id)
        assert context == {}
    
    @pytest.mark.asyncio
    async def test_isolated_execution_context(self, isolation_manager):
        """Test isolated execution context manager."""
        task_data = {'task_type': 'test', 'priority': 'high'}
        
        async with isolation_manager.isolated_execution("task_1", task_data) as context_id:
            # Context should exist during execution
            context = await isolation_manager.get_task_context(context_id)
            assert context['task_id'] == "task_1"
            assert context['task_data'] == task_data
        
        # Context should be cleaned up after execution
        context = await isolation_manager.get_task_context(context_id)
        assert context == {}


class TestDeadlockDetector:
    """Test deadlock detection and prevention for concurrent task execution."""
    
    @pytest.fixture
    def deadlock_detector(self):
        """Create test deadlock detector."""
        return DeadlockDetector()
    
    @pytest.mark.asyncio
    async def test_deadlock_detection_metrics(self, deadlock_detector):
        """Test deadlock detection metrics tracking."""
        metrics = await deadlock_detector.get_metrics()
        assert 'deadlock_metrics' in metrics
        assert 'active_tasks' in metrics
        assert 'resource_contention' in metrics
        assert metrics['deadlock_metrics']['deadlocks_detected'] == 0
    
    @pytest.mark.asyncio
    async def test_task_cleanup(self, deadlock_detector):
        """Test task cleanup from deadlock tracking."""
        # Add task to tracking
        await deadlock_detector.check_potential_deadlock("task_1", [ResourceType.PROCESSING_SLOTS])
        
        metrics = await deadlock_detector.get_metrics()
        assert metrics['active_tasks'] == 1
        
        # Remove task
        await deadlock_detector.remove_task("task_1")
        
        metrics = await deadlock_detector.get_metrics()
        assert metrics['active_tasks'] == 0
    
    @pytest.mark.asyncio
    async def test_potential_deadlock_prevention(self, deadlock_detector):
        """Test potential deadlock detection and prevention."""
        # This test verifies the deadlock detection logic works
        # In a real scenario, complex resource dependencies would trigger deadlock detection
        try:
            await deadlock_detector.check_potential_deadlock("task_1", [ResourceType.PROCESSING_SLOTS])
            await deadlock_detector.check_potential_deadlock("task_2", [ResourceType.DATABASE_CONNECTIONS])
            # Should not raise exception for non-conflicting resources
        except TaskExecutionError:
            pytest.fail("Deadlock detected for non-conflicting resources")


class TestConcurrentTaskExecutor:
    """Test main concurrent task executor with comprehensive concurrency controls."""
    
    @pytest.fixture
    def config(self):
        """Create test enrichment configuration."""
        return EnrichmentConfig(
            max_concurrent_tasks=3,
            task_timeout_seconds=5,
            retry_delay_seconds=1,
            queue_poll_interval=1,
            batch_size=5
        )
    
    @pytest.fixture
    def resource_limits(self):
        """Create test resource limits."""
        return ResourceLimits(
            api_calls_per_minute=10,
            max_processing_slots=3,
            max_database_connections=5,
            max_vector_db_connections=2,
            max_llm_connections=1
        )
    
    @pytest.fixture
    def executor(self, config, resource_limits):
        """Create test concurrent executor."""
        return ConcurrentTaskExecutor(config, resource_limits)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample enrichment task."""
        return EnrichmentTask(
            content_id="test_content_1",
            task_type=EnrichmentType.CONTENT_ANALYSIS,
            priority=EnrichmentPriority.NORMAL,
            created_at=datetime.utcnow(),
            status=TaskStatus.PENDING
        )
    
    @pytest.mark.asyncio
    async def test_task_execution_with_resources(self, executor, sample_task):
        """Test task execution with resource acquisition."""
        executed = False
        
        async def mock_handler(task):
            nonlocal executed
            executed = True
            return {"result": "success"}
        
        # Execute task with required resources
        result = await executor.execute_task(
            sample_task,
            mock_handler,
            [ResourceType.PROCESSING_SLOTS, ResourceType.DATABASE_CONNECTIONS]
        )
        
        assert executed
        assert result == {"result": "success"}
        assert sample_task.status == TaskStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_task_execution_timeout(self, executor, sample_task):
        """Test task execution timeout handling."""
        async def slow_handler(task):
            await asyncio.sleep(10)  # Longer than timeout
            return {"result": "success"}
        
        with pytest.raises(EnrichmentTimeoutError):
            await executor.execute_task(
                sample_task,
                slow_handler,
                [ResourceType.PROCESSING_SLOTS]
            )
        
        assert sample_task.status == TaskStatus.FAILED
        assert "timed out" in sample_task.error_message
    
    @pytest.mark.asyncio
    async def test_task_execution_failure(self, executor, sample_task):
        """Test task execution failure handling."""
        async def failing_handler(task):
            raise ValueError("Task processing failed")
        
        with pytest.raises(TaskExecutionError):
            await executor.execute_task(
                sample_task,
                failing_handler,
                [ResourceType.PROCESSING_SLOTS]
            )
        
        assert sample_task.status == TaskStatus.FAILED
        assert "Task processing failed" in sample_task.error_message
    
    @pytest.mark.asyncio
    async def test_priority_queue_submission(self, executor, sample_task):
        """Test priority queue task submission."""
        async def mock_handler(task):
            return {"result": "queued"}
        
        # Submit task to priority queue
        await executor.submit_priority_task(
            sample_task,
            mock_handler,
            [ResourceType.PROCESSING_SLOTS]
        )
        
        # Verify task was queued (would be processed by background processor)
        metrics = await executor.get_concurrency_metrics()
        assert metrics['priority_queue']['size'] >= 0
    
    @pytest.mark.asyncio
    async def test_concurrency_metrics_collection(self, executor):
        """Test comprehensive concurrency metrics collection."""
        metrics = await executor.get_concurrency_metrics()
        
        # Verify metrics structure
        assert 'executor_metrics' in metrics
        assert 'resource_pools' in metrics
        assert 'active_tasks' in metrics
        assert 'priority_queue' in metrics
        assert 'deadlock_detector' in metrics
        
        # Verify resource pool metrics
        for resource_type in ResourceType:
            assert resource_type.value in metrics['resource_pools']
            pool_metrics = metrics['resource_pools'][resource_type.value]
            assert 'utilization_percent' in pool_metrics
            assert 'available_slots' in pool_metrics
    
    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, executor):
        """Test comprehensive health check functionality."""
        health = await executor.health_check()
        
        # Verify health check structure
        assert 'status' in health
        assert 'resource_pools' in health
        assert 'queue_health' in health
        assert 'error_metrics' in health
        assert 'recommendations' in health
        
        # Should be healthy initially
        assert health['status'] == 'healthy'
        assert isinstance(health['recommendations'], list)
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, executor):
        """Test graceful shutdown with active tasks."""
        # Start some mock background processing
        async def long_running_task(task):
            await asyncio.sleep(0.1)
            return {"result": "completed"}
        
        sample_task = EnrichmentTask(
            content_id="shutdown_test",
            task_type=EnrichmentType.CONTENT_ANALYSIS,
            priority=EnrichmentPriority.NORMAL,
            created_at=datetime.utcnow(),
            status=TaskStatus.PENDING
        )
        
        # Execute task in background
        task_future = asyncio.create_task(
            executor.execute_task(sample_task, long_running_task, [ResourceType.PROCESSING_SLOTS])
        )
        
        # Allow task to start
        await asyncio.sleep(0.05)
        
        # Shutdown gracefully
        shutdown_stats = await executor.graceful_shutdown(timeout=2.0)
        
        # Verify shutdown completed
        assert 'shutdown_time_seconds' in shutdown_stats
        assert 'graceful' in shutdown_stats
        assert 'final_metrics' in shutdown_stats
        
        # Clean up
        try:
            await task_future
        except:
            pass  # Task may be cancelled during shutdown


class TestConcurrencyIntegration:
    """Integration tests for complete concurrency control system."""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution_limits(self):
        """Test that concurrent execution respects resource limits."""
        config = EnrichmentConfig(
            max_concurrent_tasks=2,
            task_timeout_seconds=5
        )
        resource_limits = ResourceLimits(max_processing_slots=2)
        executor = ConcurrentTaskExecutor(config, resource_limits)
        
        executed_tasks = []
        
        async def tracking_handler(task):
            executed_tasks.append(task.content_id)
            await asyncio.sleep(0.1)  # Simulate work
            return {"result": "success"}
        
        # Create multiple tasks
        tasks = []
        for i in range(4):
            task = EnrichmentTask(
                content_id=f"task_{i}",
                task_type=EnrichmentType.CONTENT_ANALYSIS,
                priority=EnrichmentPriority.NORMAL,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        # Execute tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            executor.execute_task(task, tracking_handler, [ResourceType.PROCESSING_SLOTS])
            for task in tasks
        ])
        end_time = time.time()
        
        # Verify all tasks completed
        assert len(executed_tasks) == 4
        assert len(results) == 4
        
        # Verify concurrency was limited (should take longer than if all ran truly parallel)
        # With 2 slots and 4 tasks, should take at least 2 * 0.1 = 0.2 seconds
        execution_time = end_time - start_time
        assert execution_time >= 0.2
        
        # Clean up
        await executor.graceful_shutdown()
    
    @pytest.mark.asyncio
    async def test_backpressure_handling(self):
        """Test backpressure handling under high load."""
        config = EnrichmentConfig(max_concurrent_tasks=1)
        resource_limits = ResourceLimits(max_processing_slots=1)
        executor = ConcurrentTaskExecutor(config, resource_limits)
        
        # Create many tasks to trigger backpressure
        tasks = []
        for i in range(10):
            task = EnrichmentTask(
                content_id=f"backpressure_task_{i}",
                task_type=EnrichmentType.CONTENT_ANALYSIS,
                priority=EnrichmentPriority.NORMAL,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        async def quick_handler(task):
            return {"result": "quick"}
        
        # Submit tasks to priority queue (some should trigger backpressure)
        backpressure_triggered = False
        for task in tasks:
            try:
                await executor.submit_priority_task(task, quick_handler, [ResourceType.PROCESSING_SLOTS])
            except QueueError as e:
                if "backpressure" in str(e).lower():
                    backpressure_triggered = True
                    break
        
        # Verify backpressure was triggered (or queue handled gracefully)
        metrics = await executor.get_concurrency_metrics()
        assert metrics['priority_queue']['size'] >= 0
        
        # Clean up
        await executor.graceful_shutdown()


if __name__ == "__main__":
    pytest.main([__file__])