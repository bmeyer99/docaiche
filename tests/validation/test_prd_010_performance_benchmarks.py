"""
PRD-010 Performance Benchmarking Test Suite

Comprehensive performance testing for knowledge enrichment pipeline:
- Concurrent task processing benchmarks
- Memory usage and leak detection
- Queue performance under load
- Resource utilization limits
- Scalability characteristics
"""

import pytest
import time
import asyncio
import threading
import concurrent.futures
import psutil
import gc
from unittest.mock import patch
from typing import List, Dict, Any
from src.enrichment.enricher import KnowledgeEnricher
from src.enrichment.tasks import EnrichmentTask, TaskStatus
from src.enrichment.queue import EnrichmentQueue
from src.enrichment.concurrent import ConcurrencyManager
from src.enrichment.config import EnrichmentConfig


class TestPerformanceBenchmarks:
    """Core performance benchmarking tests"""
    
    @pytest.mark.benchmark
    def test_task_processing_throughput(self):
        """Benchmark task processing throughput under various loads"""
        enricher = KnowledgeEnricher()
        
        test_cases = [
            {"task_count": 10, "expected_min_throughput": 5.0},
            {"task_count": 50, "expected_min_throughput": 3.0},
            {"task_count": 100, "expected_min_throughput": 2.0}
        ]
        
        for case in test_cases:
            tasks = [
                EnrichmentTask(
                    content=f"benchmark content {i}",
                    source_type="benchmark",
                    priority=1
                ) for i in range(case["task_count"])
            ]
            
            start_time = time.time()
            results = []
            
            for task in tasks:
                result = enricher.process_task(task)
                results.append(result)
            
            end_time = time.time()
            
            # Calculate throughput
            duration = end_time - start_time
            throughput = case["task_count"] / duration
            
            # Verify all tasks completed successfully
            assert all(r.status == TaskStatus.COMPLETED for r in results)
            
            # Verify throughput meets benchmark
            assert throughput >= case["expected_min_throughput"], \
                f"Throughput {throughput:.2f} tasks/s below benchmark {case['expected_min_throughput']}"
    
    @pytest.mark.benchmark
    async def test_concurrent_processing_performance(self):
        """Benchmark concurrent task processing performance"""
        enricher = KnowledgeEnricher()
        concurrency_manager = ConcurrencyManager(max_concurrent_tasks=10)
        
        # Create 100 tasks to process concurrently
        tasks = [
            EnrichmentTask(
                content=f"concurrent content {i}",
                source_type="concurrent",
                priority=i % 5 + 1
            ) for i in range(100)
        ]
        
        start_time = time.time()
        
        async with concurrency_manager:
            # Process tasks in batches of 10
            results = []
            for i in range(0, len(tasks), 10):
                batch = tasks[i:i+10]
                batch_results = await asyncio.gather(*[
                    enricher.process_task_async(task) for task in batch
                ])
                results.extend(batch_results)
        
        end_time = time.time()
        
        # Verify performance
        duration = end_time - start_time
        throughput = 100 / duration
        
        assert len(results) == 100
        assert all(r.status == TaskStatus.COMPLETED for r in results)
        assert throughput >= 5.0, f"Concurrent throughput {throughput:.2f} below benchmark 5.0"
        assert duration < 30, f"Processing took {duration:.2f}s, expected < 30s"
    
    @pytest.mark.benchmark
    def test_queue_operations_performance(self):
        """Benchmark queue operation performance"""
        queue = EnrichmentQueue()
        
        # Test enqueue performance
        enqueue_tasks = [
            EnrichmentTask(
                content=f"queue test {i}",
                source_type="queue_test",
                priority=i % 10
            ) for i in range(1000)
        ]
        
        start_time = time.time()
        for task in enqueue_tasks:
            queue.enqueue(task)
        enqueue_time = time.time() - start_time
        
        # Verify enqueue performance (should handle 1000 ops in < 1s)
        assert enqueue_time < 1.0, f"Enqueue took {enqueue_time:.3f}s, expected < 1.0s"
        
        # Test dequeue performance
        start_time = time.time()
        dequeued_tasks = []
        while not queue.is_empty():
            task = queue.dequeue()
            dequeued_tasks.append(task)
        dequeue_time = time.time() - start_time
        
        # Verify dequeue performance
        assert dequeue_time < 1.0, f"Dequeue took {dequeue_time:.3f}s, expected < 1.0s"
        assert len(dequeued_tasks) == 1000
    
    @pytest.mark.benchmark
    def test_memory_usage_under_load(self):
        """Test memory usage characteristics under load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        enricher = KnowledgeEnricher()
        
        # Process tasks of various sizes
        for batch in range(10):
            tasks = []
            for i in range(50):
                # Create tasks with varying content sizes
                content_size = (i % 5 + 1) * 1024  # 1KB to 5KB
                content = "x" * content_size
                
                task = EnrichmentTask(
                    content=content,
                    source_type="memory_test",
                    priority=1
                )
                tasks.append(task)
            
            # Process batch
            for task in tasks:
                enricher.process_task(task)
            
            # Force garbage collection
            gc.collect()
            
            # Check memory usage
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory
            
            # Memory should not grow excessively (< 50MB increase)
            assert memory_increase < 50 * 1024 * 1024, \
                f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB"
    
    @pytest.mark.benchmark
    def test_large_content_processing_performance(self):
        """Benchmark processing of large content items"""
        enricher = KnowledgeEnricher()
        
        # Test different content sizes
        test_sizes = [
            {"size": 10 * 1024, "max_time": 2.0},      # 10KB - 2s
            {"size": 100 * 1024, "max_time": 5.0},     # 100KB - 5s
            {"size": 1024 * 1024, "max_time": 15.0}    # 1MB - 15s
        ]
        
        for test_case in test_sizes:
            content = "Large content data. " * (test_case["size"] // 20)
            
            task = EnrichmentTask(
                content=content,
                source_type="large_content",
                priority=1
            )
            
            start_time = time.time()
            result = enricher.process_task(task)
            processing_time = time.time() - start_time
            
            # Verify processing completed successfully
            assert result.status == TaskStatus.COMPLETED
            
            # Verify processing time is within acceptable limits
            assert processing_time < test_case["max_time"], \
                f"Processing {test_case['size']} bytes took {processing_time:.2f}s, " \
                f"expected < {test_case['max_time']}s"


class TestConcurrencyPerformance:
    """Test concurrent operation performance characteristics"""
    
    def test_thread_pool_efficiency(self):
        """Test thread pool efficiency under load"""
        enricher = KnowledgeEnricher()
        
        # Create tasks for thread pool
        tasks = [
            EnrichmentTask(
                content=f"thread test {i}",
                source_type="thread_test",
                priority=1
            ) for i in range(50)
        ]
        
        # Test with different thread pool sizes
        pool_sizes = [2, 5, 10]
        
        for pool_size in pool_sizes:
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as executor:
                futures = [
                    executor.submit(enricher.process_task, task)
                    for task in tasks
                ]
                results = [future.result() for future in futures]
            
            end_time = time.time()
            
            # Verify all tasks completed
            assert len(results) == 50
            assert all(r.status == TaskStatus.COMPLETED for r in results)
            
            # Verify reasonable performance
            duration = end_time - start_time
            assert duration < 30, f"Thread pool size {pool_size} took {duration:.2f}s"
    
    def test_lock_contention_performance(self):
        """Test performance under lock contention scenarios"""
        enricher = KnowledgeEnricher()
        concurrency_manager = ConcurrencyManager()
        
        # Simulate high contention scenario
        contention_results = []
        
        def worker_with_contention(worker_id):
            results = []
            for i in range(20):
                with concurrency_manager.acquire_lock(f"resource_{i % 5}"):
                    # Simulate some work
                    time.sleep(0.01)
                    task = EnrichmentTask(
                        content=f"worker {worker_id} task {i}",
                        source_type="contention_test",
                        priority=1
                    )
                    result = enricher.process_task(task)
                    results.append(result)
            return results
        
        start_time = time.time()
        
        # Run multiple workers with lock contention
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(
                target=lambda wid=worker_id: contention_results.extend(
                    worker_with_contention(wid)
                )
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Verify performance under contention
        duration = end_time - start_time
        assert duration < 45, f"Lock contention scenario took {duration:.2f}s"
        assert len(contention_results) == 100  # 5 workers * 20 tasks
    
    def test_async_performance_characteristics(self):
        """Test async operation performance"""
        enricher = KnowledgeEnricher()
        
        async def async_benchmark():
            # Create async tasks
            tasks = [
                EnrichmentTask(
                    content=f"async content {i}",
                    source_type="async_test",
                    priority=1
                ) for i in range(100)
            ]
            
            start_time = time.time()
            
            # Process tasks asynchronously
            results = await asyncio.gather(*[
                enricher.process_task_async(task) for task in tasks
            ])
            
            end_time = time.time()
            
            # Verify async performance
            duration = end_time - start_time
            throughput = 100 / duration
            
            assert len(results) == 100
            assert throughput >= 10.0, f"Async throughput {throughput:.2f} below benchmark"
            assert duration < 15, f"Async processing took {duration:.2f}s"
            
            return results
        
        # Run async benchmark
        results = asyncio.run(async_benchmark())
        assert all(r.status == TaskStatus.COMPLETED for r in results)


class TestResourceUtilizationLimits:
    """Test resource utilization and limit enforcement"""
    
    def test_cpu_usage_under_load(self):
        """Monitor CPU usage under heavy load"""
        enricher = KnowledgeEnricher()
        
        # Create CPU-intensive tasks
        tasks = [
            EnrichmentTask(
                content="x" * 10000,  # Large content requiring processing
                source_type="cpu_test",
                priority=1
            ) for _ in range(20)
        ]
        
        # Monitor CPU usage during processing
        cpu_samples = []
        
        def cpu_monitor():
            for _ in range(30):  # Monitor for 30 seconds
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_samples.append(cpu_percent)
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=cpu_monitor)
        monitor_thread.start()
        
        # Process tasks
        start_time = time.time()
        for task in tasks:
            enricher.process_task(task)
        processing_time = time.time() - start_time
        
        monitor_thread.join()
        
        # Analyze CPU usage
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # Verify reasonable CPU usage (shouldn't max out system)
        assert max_cpu < 90, f"CPU usage peaked at {max_cpu}%"
        assert avg_cpu < 70, f"Average CPU usage {avg_cpu:.1f}% too high"
        assert processing_time < 60, f"Processing took {processing_time:.2f}s"
    
    def test_memory_limit_enforcement(self):
        """Test memory limit enforcement"""
        config = EnrichmentConfig(memory_limit_mb=128)
        enricher = KnowledgeEnricher(config=config)
        
        # Try to process tasks that would exceed memory limit
        large_tasks = [
            EnrichmentTask(
                content="x" * (50 * 1024 * 1024),  # 50MB content
                source_type="memory_limit_test",
                priority=1
            ) for _ in range(5)  # Total: 250MB, exceeds 128MB limit
        ]
        
        processed_count = 0
        errors = 0
        
        for task in large_tasks:
            try:
                result = enricher.process_task(task)
                if result.status == TaskStatus.COMPLETED:
                    processed_count += 1
                else:
                    errors += 1
            except (MemoryError, RuntimeError):
                errors += 1
        
        # Should have hit memory limits and rejected some tasks
        assert errors > 0, "Memory limit enforcement not working"
        assert processed_count < len(large_tasks), "All tasks processed despite memory limits"
    
    def test_connection_pool_limits(self):
        """Test database connection pool limit enforcement"""
        enricher = KnowledgeEnricher()
        
        # Simulate many concurrent database operations
        def database_operation(operation_id):
            task = EnrichmentTask(
                content=f"db operation {operation_id}",
                source_type="db_test",
                priority=1
            )
            return enricher.process_task(task)
        
        start_time = time.time()
        
        # Create more concurrent operations than connection pool size
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(database_operation, i)
                for i in range(50)
            ]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        
        # Verify connection pool handled the load
        duration = end_time - start_time
        assert duration < 120, f"Connection pool operations took {duration:.2f}s"
        assert len(results) == 50
        
        # Some operations might fail due to connection limits, but most should succeed
        successful = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        assert successful >= 40, f"Only {successful}/50 operations succeeded"


class TestScalabilityCharacteristics:
    """Test system scalability characteristics"""
    
    def test_horizontal_scaling_simulation(self):
        """Simulate horizontal scaling with multiple enricher instances"""
        # Create multiple enricher instances
        enrichers = [
            KnowledgeEnricher(instance_id=f"enricher_{i}")
            for i in range(3)
        ]
        
        # Shared queue for work distribution
        shared_queue = EnrichmentQueue()
        
        # Add tasks to shared queue
        tasks = [
            EnrichmentTask(
                content=f"scaling test {i}",
                source_type="scaling_test",
                priority=i % 5 + 1
            ) for i in range(150)
        ]
        
        for task in tasks:
            shared_queue.enqueue(task)
        
        # Process tasks with multiple instances
        def worker(enricher_instance):
            processed = []
            while not shared_queue.is_empty():
                try:
                    task = shared_queue.dequeue()
                    result = enricher_instance.process_task(task)
                    processed.append(result)
                except:
                    break  # Queue empty
            return processed
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(worker, enricher)
                for enricher in enrichers
            ]
            instance_results = [future.result() for future in futures]
        
        end_time = time.time()
        
        # Verify horizontal scaling effectiveness
        total_processed = sum(len(results) for results in instance_results)
        duration = end_time - start_time
        throughput = total_processed / duration
        
        assert total_processed == 150
        assert throughput >= 8.0, f"Scaled throughput {throughput:.2f} below benchmark"
        assert duration < 25, f"Scaled processing took {duration:.2f}s"
    
    def test_load_balancing_efficiency(self):
        """Test load balancing across multiple workers"""
        enricher = KnowledgeEnricher()
        
        # Create tasks with different processing complexities
        tasks = []
        for i in range(100):
            complexity = (i % 3) + 1  # 1-3 complexity levels
            content_size = complexity * 1000
            
            task = EnrichmentTask(
                content="x" * content_size,
                source_type="load_balance_test",
                priority=complexity,
                metadata={"complexity": complexity}
            )
            tasks.append(task)
        
        # Process with load balancing
        start_time = time.time()
        
        # Distribute tasks across workers based on complexity
        worker_loads = [[], [], []]  # 3 workers
        
        for i, task in enumerate(tasks):
            worker_id = i % 3
            worker_loads[worker_id].append(task)
        
        def process_worker_load(worker_tasks):
            results = []
            for task in worker_tasks:
                result = enricher.process_task(task)
                results.append(result)
            return results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_worker_load, worker_load)
                for worker_load in worker_loads
            ]
            worker_results = [future.result() for future in futures]
        
        end_time = time.time()
        
        # Verify load balancing efficiency
        total_results = sum(len(results) for results in worker_results)
        duration = end_time - start_time
        
        assert total_results == 100
        assert duration < 45, f"Load balanced processing took {duration:.2f}s"
        
        # Verify load distribution is reasonably balanced
        load_sizes = [len(results) for results in worker_results]
        load_variance = max(load_sizes) - min(load_sizes)
        assert load_variance <= 5, f"Load imbalance variance {load_variance} too high"


# Benchmark configuration
pytest_plugins = ["pytest_benchmark"]

if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([
        __file__,
        "-v",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-min-rounds=3"
    ])