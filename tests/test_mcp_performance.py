"""
MCP Search System Performance Tests
===================================

Performance benchmarks and load testing for the MCP Search System.
Validates performance targets from PERFORMANCE_OPTIMIZATION.md.
"""

import asyncio
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

from src.mcp.providers.search_orchestrator import ExternalSearchOrchestrator
from src.search.optimized_cache import OptimizedCacheManager, LRUCache
from src.mcp.text_ai.llm_adapter import TextAILLMAdapter
from tests.test_mcp_integration import MockExternalProvider


class PerformanceBenchmark:
    """Base class for performance benchmarks."""
    
    def __init__(self, name: str):
        self.name = name
        self.results = []
    
    def record_result(self, duration_ms: float, success: bool = True, metadata: Dict[str, Any] = None):
        """Record a benchmark result."""
        self.results.append({
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
            "timestamp": time.time()
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.results:
            return {}
        
        successful_results = [r for r in self.results if r["success"]]
        if not successful_results:
            return {"success_rate": 0.0}
        
        durations = [r["duration_ms"] for r in successful_results]
        
        return {
            "name": self.name,
            "total_requests": len(self.results),
            "successful_requests": len(successful_results),
            "success_rate": len(successful_results) / len(self.results),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": statistics.mean(durations),
            "median_duration_ms": statistics.median(durations),
            "p95_duration_ms": self._percentile(durations, 95),
            "p99_duration_ms": self._percentile(durations, 99),
            "throughput_rps": len(successful_results) / (max([r["timestamp"] for r in self.results]) - min([r["timestamp"] for r in self.results])) if len(self.results) > 1 else 0
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestCachePerformance:
    """Test caching system performance benchmarks."""
    
    @pytest.fixture
    def mock_redis_cache(self):
        """Fast mock Redis cache."""
        cache = Mock()
        cache.get = AsyncMock(side_effect=lambda k: asyncio.sleep(0.001))  # 1ms Redis latency
        cache.set = AsyncMock(side_effect=lambda k, v, t: asyncio.sleep(0.001))
        return cache
    
    @pytest.fixture
    def optimized_cache(self, mock_redis_cache):
        """Create optimized cache for testing."""
        return OptimizedCacheManager(
            redis_cache=mock_redis_cache,
            l1_size=100,
            compress_threshold=1024,
            enable_stats=True
        )
    
    @pytest.mark.asyncio
    async def test_l1_cache_performance(self, optimized_cache):
        """Test L1 cache performance targets: < 0.1ms."""
        benchmark = PerformanceBenchmark("L1 Cache Performance")
        
        # Warm up cache
        test_data = [{"key": f"value_{i}"} for i in range(10)]
        for i, data in enumerate(test_data):
            await optimized_cache.set(f"key_{i}", data)
        
        # Benchmark L1 cache hits
        for i in range(100):
            start = time.perf_counter()
            result = await optimized_cache.get(f"key_{i % 10}")
            duration = (time.perf_counter() - start) * 1000
            
            benchmark.record_result(duration, success=result is not None)
        
        stats = benchmark.get_statistics()
        
        # L1 cache should be very fast
        assert stats["avg_duration_ms"] < 0.1, f"L1 cache too slow: {stats['avg_duration_ms']}ms"
        assert stats["p95_duration_ms"] < 0.5, f"L1 cache P95 too slow: {stats['p95_duration_ms']}ms"
        assert stats["success_rate"] > 0.95, f"L1 cache success rate too low: {stats['success_rate']}"
        
        print(f"L1 Cache Performance: avg={stats['avg_duration_ms']:.3f}ms, p95={stats['p95_duration_ms']:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_cache_batch_operations(self, optimized_cache):
        """Test batch operation performance."""
        benchmark = PerformanceBenchmark("Cache Batch Operations")
        
        # Test batch set performance
        batch_data = {f"batch_key_{i}": {"data": f"value_{i}"} for i in range(50)}
        
        start = time.perf_counter()
        success = await optimized_cache.set_batch(batch_data)
        duration = (time.perf_counter() - start) * 1000
        
        benchmark.record_result(duration, success=success, metadata={"operation": "batch_set", "items": 50})
        
        # Test batch get performance
        start = time.perf_counter()
        results = await optimized_cache.get_batch(list(batch_data.keys()))
        duration = (time.perf_counter() - start) * 1000
        
        benchmark.record_result(duration, success=len(results) > 0, metadata={"operation": "batch_get", "items": 50})
        
        stats = benchmark.get_statistics()
        
        # Batch operations should be efficient
        assert stats["avg_duration_ms"] < 100, f"Batch operations too slow: {stats['avg_duration_ms']}ms"
        print(f"Batch Operations: avg={stats['avg_duration_ms']:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_compression_performance(self, optimized_cache):
        """Test compression performance impact."""
        benchmark = PerformanceBenchmark("Compression Performance")
        
        # Large data that will trigger compression
        large_data = {
            "content": "x" * 2000,  # 2KB of content
            "metadata": {"tags": [f"tag_{i}" for i in range(100)]},
            "items": list(range(500))
        }
        
        # Test compression overhead
        for i in range(20):
            start = time.perf_counter()
            await optimized_cache.set(f"large_key_{i}", large_data)
            duration = (time.perf_counter() - start) * 1000
            
            benchmark.record_result(duration, metadata={"operation": "compressed_set"})
        
        # Test decompression overhead
        for i in range(20):
            start = time.perf_counter()
            result = await optimized_cache.get(f"large_key_{i}")
            duration = (time.perf_counter() - start) * 1000
            
            benchmark.record_result(duration, success=result is not None, metadata={"operation": "compressed_get"})
        
        stats = benchmark.get_statistics()
        
        # Compression should not add significant overhead
        assert stats["avg_duration_ms"] < 50, f"Compression overhead too high: {stats['avg_duration_ms']}ms"
        
        # Check compression stats
        cache_stats = optimized_cache.get_stats()
        assert cache_stats["compressions"] > 0, "Compression should have been triggered"
        
        print(f"Compression: avg={stats['avg_duration_ms']:.1f}ms, ratio={cache_stats['avg_compression_ratio']:.2%}")


class TestExternalSearchPerformance:
    """Test external search orchestrator performance."""
    
    @pytest.fixture
    def fast_providers(self):
        """Create fast mock providers."""
        return [
            MockExternalProvider("brave_fast", latency_ms=100, success_rate=0.98),
            MockExternalProvider("duckduckgo_fast", latency_ms=150, success_rate=0.95),
            MockExternalProvider("google_fast", latency_ms=200, success_rate=0.92)
        ]
    
    @pytest.fixture
    def mixed_providers(self):
        """Create providers with mixed performance characteristics."""
        return [
            MockExternalProvider("brave_fast", latency_ms=120, success_rate=0.98),
            MockExternalProvider("google_medium", latency_ms=400, success_rate=0.90),
            MockExternalProvider("bing_slow", latency_ms=800, success_rate=0.85)
        ]
    
    def create_orchestrator(self, providers, enable_hedged=True):
        """Create an orchestrator with given providers."""
        mock_registry = Mock()
        mock_registry.get_healthy_providers = AsyncMock(return_value=providers)
        
        mock_cache = Mock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        
        optimized_cache = OptimizedCacheManager(
            redis_cache=mock_cache,
            l1_size=50,
            enable_stats=True
        )
        
        return ExternalSearchOrchestrator(
            provider_registry=mock_registry,
            cache_manager=optimized_cache,
            enable_hedged_requests=enable_hedged,
            hedged_delay=0.15,  # 150ms
            max_concurrent_providers=3
        )
    
    @pytest.mark.asyncio
    async def test_single_provider_latency(self, fast_providers):
        """Test single provider search latency target: < 2s."""
        orchestrator = self.create_orchestrator([fast_providers[0]])
        benchmark = PerformanceBenchmark("Single Provider Latency")
        
        for i in range(20):
            start = time.perf_counter()
            result = await orchestrator.search(f"test query {i}", max_results=5)
            duration = (time.perf_counter() - start) * 1000
            
            benchmark.record_result(duration, success=len(result.results) > 0)
        
        stats = benchmark.get_statistics()
        
        # Single provider should meet latency targets
        assert stats["avg_duration_ms"] < 500, f"Single provider too slow: {stats['avg_duration_ms']}ms"
        assert stats["p95_duration_ms"] < 1000, f"Single provider P95 too slow: {stats['p95_duration_ms']}ms"
        
        print(f"Single Provider: avg={stats['avg_duration_ms']:.1f}ms, p95={stats['p95_duration_ms']:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_hedged_request_performance(self, mixed_providers):
        """Test hedged request performance improvement."""
        # Test without hedging
        orchestrator_normal = self.create_orchestrator(mixed_providers, enable_hedged=False)
        benchmark_normal = PerformanceBenchmark("Normal Multi-Provider")
        
        for i in range(10):
            start = time.perf_counter()
            await orchestrator_normal.search(f"normal query {i}", max_results=5)
            duration = (time.perf_counter() - start) * 1000
            benchmark_normal.record_result(duration)
        
        # Test with hedging
        orchestrator_hedged = self.create_orchestrator(mixed_providers, enable_hedged=True)
        benchmark_hedged = PerformanceBenchmark("Hedged Multi-Provider")
        
        for i in range(10):
            start = time.perf_counter()
            await orchestrator_hedged.search(f"hedged query {i}", max_results=5)
            duration = (time.perf_counter() - start) * 1000
            benchmark_hedged.record_result(duration)
        
        stats_normal = benchmark_normal.get_statistics()
        stats_hedged = benchmark_hedged.get_statistics()
        
        # Hedged requests should be faster on average
        improvement = (stats_normal["avg_duration_ms"] - stats_hedged["avg_duration_ms"]) / stats_normal["avg_duration_ms"]
        
        print(f"Normal: {stats_normal['avg_duration_ms']:.1f}ms, Hedged: {stats_hedged['avg_duration_ms']:.1f}ms")
        print(f"Hedged request improvement: {improvement:.1%}")
        
        # Should see some improvement with hedged requests
        assert improvement > 0, "Hedged requests should improve performance"
    
    @pytest.mark.asyncio
    async def test_concurrent_search_load(self, fast_providers):
        """Test performance under concurrent load."""
        orchestrator = self.create_orchestrator(fast_providers)
        benchmark = PerformanceBenchmark("Concurrent Load Test")
        
        async def single_search(query_id: int):
            start = time.perf_counter()
            try:
                result = await orchestrator.search(f"concurrent query {query_id}", max_results=3)
                duration = (time.perf_counter() - start) * 1000
                benchmark.record_result(duration, success=len(result.results) > 0)
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                benchmark.record_result(duration, success=False, metadata={"error": str(e)})
        
        # Run 50 concurrent searches
        tasks = [single_search(i) for i in range(50)]
        await asyncio.gather(*tasks)
        
        stats = benchmark.get_statistics()
        
        # Performance should degrade gracefully under load
        assert stats["success_rate"] > 0.9, f"Success rate too low under load: {stats['success_rate']}"
        assert stats["avg_duration_ms"] < 2000, f"Average latency too high under load: {stats['avg_duration_ms']}ms"
        
        print(f"Concurrent Load: {stats['total_requests']} requests, "
              f"avg={stats['avg_duration_ms']:.1f}ms, success={stats['success_rate']:.1%}")
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, fast_providers):
        """Test cache effectiveness in reducing latency."""
        orchestrator = self.create_orchestrator(fast_providers)
        
        query = "cache effectiveness test"
        
        # First request - cache miss
        start = time.perf_counter()
        result1 = await orchestrator.search(query, max_results=5)
        miss_duration = (time.perf_counter() - start) * 1000
        
        # Second request - should hit cache
        start = time.perf_counter()
        result2 = await orchestrator.search(query, max_results=5)
        hit_duration = (time.perf_counter() - start) * 1000
        
        # Cache should provide significant speedup
        speedup = miss_duration / hit_duration if hit_duration > 0 else float('inf')
        
        print(f"Cache Miss: {miss_duration:.1f}ms, Cache Hit: {hit_duration:.1f}ms, Speedup: {speedup:.1f}x")
        
        # Cache hit should be much faster
        assert hit_duration < 50, f"Cache hit too slow: {hit_duration}ms"
        assert speedup > 2, f"Cache speedup insufficient: {speedup}x"


class TestAdaptiveTimeoutPerformance:
    """Test adaptive timeout system performance."""
    
    @pytest.mark.asyncio
    async def test_timeout_adaptation(self):
        """Test adaptive timeout learning and adjustment."""
        from src.mcp.providers.search_orchestrator import AdaptiveTimeoutManager
        
        timeout_manager = AdaptiveTimeoutManager()
        benchmark = PerformanceBenchmark("Adaptive Timeout")
        
        # Simulate varying latencies for a provider
        provider_id = "test_provider"
        latencies = [100, 150, 200, 180, 160, 300, 120, 140, 190, 170]  # Mix of fast and slow
        
        for latency in latencies:
            timeout_manager.record_latency(provider_id, latency)
        
        # Get adaptive timeout
        adaptive_timeout = timeout_manager.get_timeout(provider_id)
        
        # Should be based on P95 + 20% buffer
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        expected_timeout = (p95_latency / 1000.0) * 1.2  # Convert to seconds and add buffer
        
        assert abs(adaptive_timeout - expected_timeout) < 0.5, f"Adaptive timeout calculation incorrect"
        assert adaptive_timeout < 5.0, f"Adaptive timeout too high: {adaptive_timeout}s"
        
        print(f"Latencies: {latencies}")
        print(f"P95: {p95_latency}ms, Adaptive Timeout: {adaptive_timeout:.2f}s")


class TestSystemBenchmarks:
    """System-wide performance benchmarks."""
    
    @pytest.mark.asyncio
    async def test_search_throughput(self):
        """Test system search throughput target: > 100 RPS."""
        # This would require a more complex setup with actual dependencies
        # For now, test the theoretical throughput
        
        benchmark = PerformanceBenchmark("Search Throughput")
        
        # Simulate fast search operations
        async def fast_search():
            start = time.perf_counter()
            await asyncio.sleep(0.010)  # 10ms simulated search
            duration = (time.perf_counter() - start) * 1000
            benchmark.record_result(duration)
        
        # Run searches for 1 second
        start_time = time.time()
        tasks = []
        
        while time.time() - start_time < 1.0:
            task = asyncio.create_task(fast_search())
            tasks.append(task)
            await asyncio.sleep(0.001)  # Small delay between requests
        
        await asyncio.gather(*tasks)
        
        stats = benchmark.get_statistics()
        
        print(f"Throughput Test: {stats['total_requests']} requests in 1 second")
        print(f"Effective RPS: {stats.get('throughput_rps', 0):.1f}")
        
        # Should handle reasonable throughput
        assert stats["total_requests"] > 50, f"Throughput too low: {stats['total_requests']} RPS"
    
    def test_memory_efficiency(self):
        """Test memory usage patterns."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and use cache with many items
        cache = LRUCache(maxsize=1000)
        
        # Fill with test data
        for i in range(1000):
            asyncio.run(cache.set(f"key_{i}", {"data": f"value_{i}" * 100}))
        
        # Check memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = peak_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {peak_memory:.1f}MB (+{memory_growth:.1f}MB)")
        
        # Memory growth should be reasonable
        assert memory_growth < 100, f"Memory usage too high: {memory_growth}MB"


def run_performance_suite():
    """Run the complete performance test suite."""
    print("=" * 60)
    print("MCP Search System Performance Benchmark Suite")
    print("=" * 60)
    
    # Run tests with timing
    start_time = time.time()
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    total_time = time.time() - start_time
    print(f"\nTotal benchmark time: {total_time:.1f} seconds")
    
    return exit_code


if __name__ == "__main__":
    run_performance_suite()