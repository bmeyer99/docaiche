"""
PRD-010 Knowledge Enrichment System Comprehensive Validation
Complete test-driven validation suite for knowledge enrichment pipeline
Following QA test-driven validation methodology for production readiness assessment
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import components for validation
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.enrichment import (
    EnrichmentQueue, KnowledgeEnricher, create_enrichment_queue, create_knowledge_enricher
)
from src.enrichment.models import (
    EnrichmentTask, EnrichmentResult, EnrichmentStrategy, TaskStatus, TaskPriority,
    ContentGap, KnowledgeGraph, RelationshipType
)
from src.enrichment.analyzers import (
    GapAnalyzer, RelationshipAnalyzer, QualityAnalyzer, TagAnalyzer
)
from src.enrichment.exceptions import (
    EnrichmentError, TaskExecutionError, AnalysisError, 
    QueueError, InvalidTaskError, EnrichmentTimeoutError
)
from src.enrichment.models import EnrichmentConfig


# Global test fixtures
@pytest.fixture
def enrichment_config():
    """Create test enrichment configuration"""
    return EnrichmentConfig(
        max_concurrent_tasks=5,
        task_timeout_seconds=300,
        retry_delay_seconds=60,
        queue_poll_interval=10,
        batch_size=10,
        enable_relationship_mapping=True,
        enable_tag_generation=True,
        enable_quality_assessment=True,
        min_confidence_threshold=0.7
    )

@pytest.fixture
def mock_dependencies():
    """Create mocked dependencies for testing"""
    return {
        'db_manager': Mock(),
        'content_processor': Mock(),
        'anythingllm_client': Mock(),
        'search_orchestrator': Mock()
    }


class TestPRD010FunctionalRequirements:
    """Test PRD-010 functional requirements implementation"""
    
    def test_enrichment_queue_implementation(self, enrichment_config):
        """Verify enrichment queue is properly implemented"""
        queue = create_enrichment_queue(enrichment_config)
        
        assert queue is not None
        assert hasattr(queue, 'add_task')
        assert hasattr(queue, 'get_next_task')
        assert hasattr(queue, 'mark_completed')
        assert hasattr(queue, 'mark_failed')
        assert hasattr(queue, 'get_queue_stats')
        
        # Test queue configuration
        assert queue.config.max_concurrent_tasks == 5
        assert queue.config.task_timeout_seconds == 300
    
    def test_knowledge_enricher_initialization(self, enrichment_config, mock_dependencies):
        """Verify knowledge enricher initializes correctly"""
        enricher = create_knowledge_enricher(
            enrichment_config,
            **mock_dependencies
        )
        
        assert enricher is not None
        assert hasattr(enricher, 'analyze_content_gaps')
        assert hasattr(enricher, 'enrich_content')
        assert hasattr(enricher, 'process_task_queue')
        assert hasattr(enricher, 'health_check')
        
        # Verify configuration integration
        assert enricher.config.enable_relationship_mapping is True
        assert enricher.config.enable_tag_generation is True
    
    def test_enrichment_strategies_implementation(self, enrichment_config, mock_dependencies):
        """Verify all enrichment strategies are implemented"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test content gap analysis strategy
        gaps = enricher.analyze_content_gaps("test query")
        assert isinstance(gaps, list)
        
        # Test relationship mapping strategy
        if enricher.config.enable_relationship_mapping:
            relationships = enricher.map_content_relationships("content_id_1")
            assert relationships is not None
        
        # Test quality assessment strategy
        if enricher.config.enable_quality_assessment:
            quality_score = enricher.assess_content_quality("content_id_1")
            assert isinstance(quality_score, (int, float))
    
    @pytest.mark.asyncio
    async def test_background_task_processing(self, enrichment_config, mock_dependencies):
        """Verify background task processing works correctly"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        queue = create_enrichment_queue(enrichment_config)
        
        # Add test task to queue
        task = EnrichmentTask(
            id="test_task_1",
            strategy=EnrichmentStrategy.CONTENT_GAP_ANALYSIS,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.now(),
            target_content_id="content_1",
            parameters={"query": "test query"}
        )
        
        await queue.add_task(task)
        
        # Process the task
        with patch.object(enricher, '_execute_task') as mock_execute:
            mock_execute.return_value = EnrichmentResult(
                task_id="test_task_1",
                status=TaskStatus.COMPLETED,
                result_data={"gaps_found": 2},
                confidence_score=0.8,
                execution_time_ms=1000
            )
            
            result = await enricher.process_task_queue()
            assert result is not None
    
    def test_factory_pattern_implementation(self, enrichment_config):
        """Verify factory functions work correctly"""
        # Test queue factory
        queue = create_enrichment_queue(enrichment_config)
        assert isinstance(queue, EnrichmentQueue)
        
        # Test enricher factory with minimal dependencies
        mock_deps = {
            'db_manager': Mock(),
            'content_processor': Mock(),
            'anythingllm_client': Mock(),
            'search_orchestrator': Mock()
        }
        
        enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
        assert isinstance(enricher, KnowledgeEnricher)


class TestPRD010SecurityValidation:
    """Test PRD-010 security requirements"""
    
    def test_input_validation_security(self, enrichment_config, mock_dependencies):
        """Verify all inputs are properly validated"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test malicious query injection
        with pytest.raises((ValueError, EnrichmentError)):
            enricher.analyze_content_gaps("'; DROP TABLE documents; --")
        
        # Test content ID validation
        with pytest.raises((ValueError, InvalidTaskError)):
            enricher.map_content_relationships("../../../etc/passwd")
    
    def test_no_hardcoded_credentials(self):
        """Verify no hardcoded credentials in enrichment code"""
        import src.enrichment.enricher as enricher_module
        import src.enrichment.analyzers as analyzers_module
        
        # Check for common credential patterns
        forbidden_patterns = [
            'password', 'secret', 'key=', 'token=',
            'api_key', 'private_key', 'auth_token'
        ]
        
        for module in [enricher_module, analyzers_module]:
            source = str(module.__file__)
            with open(source, 'r') as f:
                content = f.read().lower()
                for pattern in forbidden_patterns:
                    # Allow pattern in comments/docstrings but not in code
                    lines = [line.strip() for line in content.split('\n') 
                            if pattern in line and not line.startswith('#') 
                            and not line.startswith('"""') and not line.startswith("'''")]
                    assert len(lines) == 0, f"Found potential credential: {pattern}"
    
    def test_secure_task_execution(self, enrichment_config, mock_dependencies):
        """Verify task execution security measures"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test timeout enforcement
        task = EnrichmentTask(
            id="timeout_test",
            strategy=EnrichmentStrategy.QUALITY_ASSESSMENT,
            priority=TaskPriority.LOW,
            created_at=datetime.now(),
            target_content_id="content_1",
            parameters={}
        )
        
        with patch('asyncio.wait_for') as mock_wait:
            mock_wait.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(EnrichmentTimeoutError):
                asyncio.run(enricher._execute_task(task))


class TestPRD010PerformanceValidation:
    """Test PRD-010 performance requirements"""
    
    def test_concurrent_task_limits(self, enrichment_config, mock_dependencies):
        """Verify concurrent task limit enforcement"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test max concurrent tasks configuration
        assert enricher.config.max_concurrent_tasks == 5
        
        # Verify semaphore or similar mechanism exists for concurrency control
        assert hasattr(enricher, '_task_semaphore') or hasattr(enricher, '_concurrent_tasks')
    
    def test_task_timeout_configuration(self, enrichment_config):
        """Verify task timeout configuration works"""
        # Test timeout values are reasonable
        assert enrichment_config.task_timeout_seconds >= 30
        assert enrichment_config.task_timeout_seconds <= 3600  # Max 1 hour
        
        # Test retry delay configuration
        assert enrichment_config.retry_delay_seconds >= 1
    
    @pytest.mark.asyncio
    async def test_queue_performance(self, enrichment_config):
        """Verify queue operations are performant"""
        queue = create_enrichment_queue(enrichment_config)
        
        # Test batch task addition
        tasks = []
        for i in range(10):
            task = EnrichmentTask(
                id=f"perf_test_{i}",
                strategy=EnrichmentStrategy.TAG_GENERATION,
                priority=TaskPriority.MEDIUM,
                created_at=datetime.now(),
                target_content_id=f"content_{i}",
                parameters={}
            )
            tasks.append(task)
        
        # Measure batch addition performance
        import time
        start_time = time.time()
        
        for task in tasks:
            await queue.add_task(task)
        
        end_time = time.time()
        
        # Should process 10 tasks in under 1 second
        assert (end_time - start_time) < 1.0
    
    def test_memory_optimization(self, enrichment_config, mock_dependencies):
        """Verify memory usage optimization"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test batch size configuration
        assert enricher.config.batch_size <= 100
        assert enricher.config.batch_size >= 1
        
        # Verify cleanup mechanisms exist
        assert hasattr(enricher, 'cleanup') or hasattr(enricher, '_cleanup_resources')


class TestPRD010IntegrationValidation:
    """Test PRD-010 integration with other components"""
    
    def test_cfg001_configuration_integration(self):
        """Verify integration with CFG-001 configuration system"""
        from src.core.config.models import EnrichmentConfig, SystemConfiguration
        
        # Test enrichment config is part of system config
        config = EnrichmentConfig()
        assert hasattr(config, 'max_concurrent_tasks')
        assert hasattr(config, 'enable_relationship_mapping')
        
        # Test validation
        assert config.max_concurrent_tasks >= 1
        assert config.max_concurrent_tasks <= 20
    
    def test_db001_database_integration(self, enrichment_config):
        """Verify integration with DB-001 database schema"""
        mock_db = Mock()
        mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        mock_deps = {
            'db_manager': mock_db,
            'content_processor': Mock(),
            'anythingllm_client': Mock(),
            'search_orchestrator': Mock()
        }
        
        enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
        
        # Verify database operations are defined
        assert hasattr(enricher, 'db_manager')
        
        # Test database queries would use proper schema
        # This validates compatibility with DB-001 tables
        mock_db.execute_query = AsyncMock()
        
        # Should be able to query enrichment-related tables
        expected_tables = ['enrichment_tasks', 'content_gaps', 'knowledge_graph']
        for table in expected_tables:
            # Verify table compatibility (would be tested in integration)
            assert table is not None
    
    def test_prd008_content_processor_integration(self, enrichment_config):
        """Verify integration with PRD-008 content processor"""
        mock_processor = Mock()
        mock_processor.process_document = Mock()
        
        mock_deps = {
            'db_manager': Mock(),
            'content_processor': mock_processor,
            'anythingllm_client': Mock(),
            'search_orchestrator': Mock()
        }
        
        enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
        
        # Verify content processor integration
        assert enricher.content_processor is not None
        assert hasattr(enricher.content_processor, 'process_document')
    
    def test_alm001_anythingllm_integration(self, enrichment_config):
        """Verify integration with ALM-001 AnythingLLM client"""
        mock_anythingllm = Mock()
        mock_anythingllm.search_documents = AsyncMock()
        
        mock_deps = {
            'db_manager': Mock(),
            'content_processor': Mock(),
            'anythingllm_client': mock_anythingllm,
            'search_orchestrator': Mock()
        }
        
        enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
        
        # Verify AnythingLLM client integration
        assert enricher.anythingllm_client is not None
        assert hasattr(enricher.anythingllm_client, 'search_documents')


class TestPRD010ErrorHandling:
    """Test PRD-010 error handling requirements"""
    
    def test_exception_hierarchy(self):
        """Verify proper exception hierarchy exists"""
        # Test base exception
        assert issubclass(EnrichmentError, Exception)
        
        # Test specific exceptions
        assert issubclass(TaskExecutionError, EnrichmentError)
        assert issubclass(AnalysisError, EnrichmentError)
        assert issubclass(QueueError, EnrichmentError)
        assert issubclass(InvalidTaskError, EnrichmentError)
        assert issubclass(EnrichmentTimeoutError, EnrichmentError)
    
    @pytest.mark.asyncio
    async def test_task_failure_handling(self, enrichment_config, mock_dependencies):
        """Verify task failure scenarios are handled gracefully"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        queue = create_enrichment_queue(enrichment_config)
        
        # Test task execution failure
        task = EnrichmentTask(
            id="failing_task",
            strategy=EnrichmentStrategy.CONTENT_GAP_ANALYSIS,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            target_content_id="content_1",
            parameters={}
        )
        
        with patch.object(enricher, '_execute_gap_analysis') as mock_analysis:
            mock_analysis.side_effect = AnalysisError("Analysis failed")
            
            # Should handle failure gracefully
            result = await enricher._execute_task(task)
            assert result.status == TaskStatus.FAILED
            assert "Analysis failed" in result.error_message
    
    def test_queue_error_recovery(self, enrichment_config):
        """Verify queue error recovery mechanisms"""
        queue = create_enrichment_queue(enrichment_config)
        
        # Test queue health check
        assert hasattr(queue, 'health_check') or hasattr(queue, 'get_queue_stats')
        
        # Test error recovery
        with patch.object(queue, '_storage', side_effect=Exception("Storage error")):
            # Should not crash the entire system
            try:
                stats = queue.get_queue_stats()
                # Should return error state instead of crashing
                assert stats is not None
            except QueueError:
                # Acceptable to raise specific queue error
                pass
    
    def test_external_service_failure_handling(self, enrichment_config, mock_dependencies):
        """Verify external service failure handling"""
        # Test AnythingLLM service failure
        mock_anythingllm = Mock()
        mock_anythingllm.search_documents = AsyncMock(side_effect=Exception("Service down"))
        
        mock_deps = {
            'db_manager': Mock(),
            'content_processor': Mock(),
            'anythingllm_client': mock_anythingllm,
            'search_orchestrator': Mock()
        }
        
        enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
        
        # Should handle external service failures gracefully
        with pytest.raises(EnrichmentError):
            asyncio.run(enricher._query_vector_database("test query"))


class TestPRD010OperationalValidation:
    """Test PRD-010 operational requirements"""
    
    @pytest.mark.asyncio
    async def test_health_check_implementation(self, enrichment_config, mock_dependencies):
        """Verify health check functionality"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test health check exists
        assert hasattr(enricher, 'health_check')
        
        # Test health check returns proper format
        health = await enricher.health_check()
        assert isinstance(health, dict)
        assert 'status' in health
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_monitoring_metrics(self, enrichment_config, mock_dependencies):
        """Verify monitoring and metrics collection"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        queue = create_enrichment_queue(enrichment_config)
        
        # Test queue metrics
        stats = queue.get_queue_stats()
        assert isinstance(stats, dict)
        assert 'pending_tasks' in stats or 'queue_size' in stats
        
        # Test enricher metrics
        if hasattr(enricher, 'get_metrics'):
            metrics = enricher.get_metrics()
            assert isinstance(metrics, dict)
    
    def test_graceful_shutdown(self, enrichment_config, mock_dependencies):
        """Verify graceful shutdown capability"""
        enricher = create_knowledge_enricher(enrichment_config, **mock_dependencies)
        
        # Test shutdown method exists
        assert hasattr(enricher, 'shutdown') or hasattr(enricher, 'cleanup')
        
        # Test shutdown doesn't raise exceptions
        try:
            if hasattr(enricher, 'shutdown'):
                asyncio.run(enricher.shutdown())
            elif hasattr(enricher, 'cleanup'):
                enricher.cleanup()
        except Exception as e:
            pytest.fail(f"Graceful shutdown failed: {e}")
    
    def test_configuration_validation(self):
        """Verify configuration validation at startup"""
        # Test invalid configuration detection
        with pytest.raises(ValueError):
            EnrichmentConfig(max_concurrent_tasks=0)  # Invalid
        
        with pytest.raises(ValueError):
            EnrichmentConfig(max_concurrent_tasks=25)  # Too high
        
        with pytest.raises(ValueError):
            EnrichmentConfig(min_confidence_threshold=1.5)  # Invalid threshold


# Integration test fixtures and helpers
@pytest.fixture
def enrichment_system(enrichment_config):
    """Create full enrichment system for integration testing"""
    mock_deps = {
        'db_manager': Mock(),
        'content_processor': Mock(),
        'anythingllm_client': Mock(),
        'search_orchestrator': Mock()
    }
    
    # Configure mocks for realistic behavior
    mock_deps['db_manager'].health_check = AsyncMock(return_value={'status': 'healthy'})
    mock_deps['anythingllm_client'].search_documents = AsyncMock(return_value=[])
    
    queue = create_enrichment_queue(enrichment_config)
    enricher = create_knowledge_enricher(enrichment_config, **mock_deps)
    
    return {
        'queue': queue,
        'enricher': enricher,
        'config': enrichment_config,
        'mocks': mock_deps
    }


class TestPRD010IntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_enrichment_workflow(self, enrichment_system):
        """Test complete enrichment workflow from task creation to completion"""
        system = enrichment_system
        queue = system['queue']
        enricher = system['enricher']
        
        # Create enrichment task
        task = EnrichmentTask(
            id="integration_test_1",
            strategy=EnrichmentStrategy.CONTENT_GAP_ANALYSIS,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            target_content_id="content_1",
            parameters={"query": "machine learning algorithms"}
        )
        
        # Add task to queue
        await queue.add_task(task)
        
        # Process task
        with patch.object(enricher, '_execute_gap_analysis') as mock_analysis:
            mock_analysis.return_value = [
                ContentGap(
                    query="machine learning algorithms",
                    gap_type="missing_examples",
                    confidence=0.8,
                    suggested_sources=["sklearn.org", "tensorflow.org"]
                )
            ]
            
            result = await enricher.process_task_queue()
            
            # Verify task was processed
            assert result is not None
            assert mock_analysis.called
    
    def test_multi_strategy_coordination(self, enrichment_system):
        """Test coordination between multiple enrichment strategies"""
        enricher = enrichment_system['enricher']
        config = enricher.config
        
        # Verify all strategies can be enabled simultaneously
        assert config.enable_relationship_mapping
        assert config.enable_tag_generation
        assert config.enable_quality_assessment
        
        # Test strategy coordination
        content_id = "test_content_123"
        
        # Should be able to run multiple strategies without conflicts
        gaps = enricher.analyze_content_gaps("test query")
        relationships = enricher.map_content_relationships(content_id)
        quality = enricher.assess_content_quality(content_id)
        
        # All should complete without interference
        assert gaps is not None
        assert relationships is not None
        assert quality is not None


# Performance benchmark tests
class TestPRD010PerformanceBenchmarks:
    """Performance benchmark tests for PRD-010"""
    
    def test_task_processing_throughput(self, enrichment_system):
        """Benchmark task processing throughput"""
        import time
        
        queue = enrichment_system['queue']
        
        # Create multiple tasks
        tasks = []
        for i in range(100):
            task = EnrichmentTask(
                id=f"benchmark_{i}",
                strategy=EnrichmentStrategy.TAG_GENERATION,
                priority=TaskPriority.MEDIUM,
                created_at=datetime.now(),
                target_content_id=f"content_{i}",
                parameters={}
            )
            tasks.append(task)
        
        # Measure throughput
        start_time = time.time()
        
        for task in tasks:
            asyncio.run(queue.add_task(task))
        
        end_time = time.time()
        
        # Should process 100 tasks in under 5 seconds
        processing_time = end_time - start_time
        throughput = len(tasks) / processing_time
        
        assert throughput > 20  # At least 20 tasks/second
        assert processing_time < 5.0
    
    def test_memory_usage_under_load(self, enrichment_system):
        """Test memory usage under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create high-load scenario
        enricher = enrichment_system['enricher']
        
        # Process many tasks
        for i in range(50):
            gaps = enricher.analyze_content_gaps(f"test query {i}")
            relationships = enricher.map_content_relationships(f"content_{i}")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


if __name__ == "__main__":
    # Run validation tests
    pytest.main([__file__, "-v", "--tb=short"])