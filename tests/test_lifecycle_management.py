"""
Test Suite for Lifecycle Management - PRD-010
Comprehensive tests for lifecycle management implementation including startup/shutdown,
health monitoring, dependency validation, and recovery mechanisms.
"""

import asyncio
import pytest
import signal
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.enrichment.lifecycle import (
    LifecycleManager, ComponentState, ComponentStatus, DependencyValidation
)
from src.enrichment.models import EnrichmentConfig
from src.enrichment.concurrent import ResourceLimits
from src.enrichment.exceptions import EnrichmentError
from src.enrichment.factory import (
    create_lifecycle_manager, create_complete_enrichment_system
)


class TestLifecycleManager:
    """Test cases for LifecycleManager component coordination."""
    
    @pytest.fixture
    def enrichment_config(self):
        """Create test enrichment configuration."""
        return EnrichmentConfig(
            max_concurrent_tasks=3,
            task_timeout_seconds=30,
            retry_delay_seconds=5,
            queue_poll_interval=2,
            batch_size=5,
            enable_relationship_mapping=True,
            enable_tag_generation=True,
            enable_quality_assessment=True,
            min_confidence_threshold=0.7
        )
    
    @pytest.fixture
    def resource_limits(self):
        """Create test resource limits."""
        return ResourceLimits(
            api_calls_per_minute=30,
            max_processing_slots=3,
            max_database_connections=5,
            max_vector_db_connections=2,
            max_llm_connections=1
        )
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = AsyncMock()
        
        # Mock connection context manager
        mock_connection = AsyncMock()
        mock_connection.execute = AsyncMock()
        db_manager.get_connection.return_value.__aenter__.return_value = mock_connection
        db_manager.get_connection.return_value.__aexit__.return_value = None
        
        # Mock health check
        db_manager.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        return db_manager
    
    @pytest.fixture
    def lifecycle_manager(self, enrichment_config, mock_db_manager, resource_limits):
        """Create lifecycle manager for testing."""
        return LifecycleManager(
            config=enrichment_config,
            db_manager=mock_db_manager,
            resource_limits=resource_limits,
            shutdown_timeout=5.0
        )
    
    async def test_lifecycle_manager_initialization(self, lifecycle_manager):
        """Test lifecycle manager initializes correctly."""
        assert lifecycle_manager.config is not None
        assert lifecycle_manager.db_manager is not None
        assert lifecycle_manager.resource_limits is not None
        assert lifecycle_manager.shutdown_timeout == 5.0
        assert not lifecycle_manager._running
        assert lifecycle_manager._components == {}
        assert lifecycle_manager._component_status == {}
    
    async def test_component_dependency_setup(self, lifecycle_manager):
        """Test component dependency mapping is set up correctly."""
        lifecycle_manager._setup_component_dependencies()
        
        # Verify dependency map
        assert 'database' in lifecycle_manager._dependency_map
        assert 'task_queue' in lifecycle_manager._dependency_map
        assert 'concurrent_executor' in lifecycle_manager._dependency_map
        assert 'task_manager' in lifecycle_manager._dependency_map
        assert 'knowledge_enricher' in lifecycle_manager._dependency_map
        
        # Verify dependencies
        assert lifecycle_manager._dependency_map['database'] == []
        assert 'database' in lifecycle_manager._dependency_map['task_queue']
        assert 'database' in lifecycle_manager._dependency_map['concurrent_executor']
        assert 'task_manager' in lifecycle_manager._dependency_map['knowledge_enricher']
        
        # Verify startup order
        assert len(lifecycle_manager._startup_order) == 5
        assert lifecycle_manager._startup_order[0] == 'database'
        assert lifecycle_manager._startup_order[-1] == 'knowledge_enricher'
    
    async def test_component_initialization(self, lifecycle_manager):
        """Test component initialization with proper dependency order."""
        await lifecycle_manager.initialize_components()
        
        # Verify all components are initialized
        assert len(lifecycle_manager._components) == 5
        assert 'database' in lifecycle_manager._components
        assert 'task_queue' in lifecycle_manager._components
        assert 'concurrent_executor' in lifecycle_manager._components
        assert 'task_manager' in lifecycle_manager._components
        assert 'knowledge_enricher' in lifecycle_manager._components
        
        # Verify component status tracking
        assert len(lifecycle_manager._component_status) == 5
        for status in lifecycle_manager._component_status.values():
            assert status.state == ComponentState.STOPPED
            assert status.startup_time_ms is not None
    
    async def test_dependency_validation(self, lifecycle_manager):
        """Test dependency validation during initialization."""
        lifecycle_manager._setup_component_dependencies()
        await lifecycle_manager._initialize_component_instances()
        
        # Test specific dependency validation
        result = await lifecycle_manager._validate_dependency('task_queue', 'database')
        
        assert isinstance(result, DependencyValidation)
        assert result.component == 'task_queue'
        assert result.dependency == 'database'
        assert result.available is True
        assert result.validation_time_ms > 0
    
    async def test_component_startup(self, lifecycle_manager):
        """Test component startup process."""
        await lifecycle_manager.initialize_components()
        
        # Start all components
        startup_result = await lifecycle_manager.start_all_components()
        
        assert startup_result['status'] == 'success'
        assert startup_result['total_components'] == 5
        assert 'startup_time_seconds' in startup_result
        assert lifecycle_manager._running is True
        
        # Verify component states
        for status in lifecycle_manager._component_status.values():
            assert status.state == ComponentState.RUNNING
    
    async def test_graceful_shutdown(self, lifecycle_manager):
        """Test graceful shutdown with pending task completion."""
        await lifecycle_manager.initialize_components()
        await lifecycle_manager.start_all_components()
        
        # Perform graceful shutdown
        shutdown_result = await lifecycle_manager.graceful_shutdown(timeout=10.0)
        
        assert 'shutdown_time_seconds' in shutdown_result
        assert 'graceful' in shutdown_result
        assert 'components' in shutdown_result
        assert 'final_metrics' in shutdown_result
        assert lifecycle_manager._running is False
        
        # Verify components are stopped
        for status in lifecycle_manager._component_status.values():
            assert status.state == ComponentState.STOPPED
    
    async def test_health_monitoring(self, lifecycle_manager):
        """Test health monitoring and status reporting."""
        await lifecycle_manager.initialize_components()
        await lifecycle_manager.start_all_components()
        
        # Perform health check
        health_result = await lifecycle_manager.health_check()
        
        assert 'status' in health_result
        assert 'running' in health_result
        assert 'components' in health_result
        assert 'lifecycle_metrics' in health_result
        assert 'health_monitoring_active' in health_result
        assert 'recovery_enabled' in health_result
        assert 'timestamp' in health_result
        
        # Verify component health status
        for component_name, component_health in health_result['components'].items():
            assert 'healthy' in component_health
            assert 'state' in component_health
            assert 'health_status' in component_health
    
    async def test_component_recovery(self, lifecycle_manager):
        """Test component recovery mechanisms."""
        await lifecycle_manager.initialize_components()
        await lifecycle_manager.start_all_components()
        
        # Simulate component failure
        component_name = 'task_queue'
        lifecycle_manager._component_status[component_name].state = ComponentState.FAILED
        lifecycle_manager._component_status[component_name].health_status = 'unhealthy'
        
        # Trigger recovery
        await lifecycle_manager._recover_component(component_name)
        
        # Verify recovery
        status = lifecycle_manager._component_status[component_name]
        assert status.state == ComponentState.RUNNING
        assert status.restart_count == 1
    
    async def test_component_restart(self, lifecycle_manager):
        """Test individual component restart functionality."""
        await lifecycle_manager.initialize_components()
        await lifecycle_manager.start_all_components()
        
        # Restart specific component
        restart_result = await lifecycle_manager.restart_component('task_queue')
        
        assert restart_result['status'] == 'success'
        assert restart_result['component'] == 'task_queue'
        assert 'restart_result' in restart_result
        
        # Verify component is running
        status = lifecycle_manager._component_status['task_queue']
        assert status.state == ComponentState.RUNNING
    
    async def test_signal_handler_setup(self, lifecycle_manager):
        """Test signal handlers for container environments."""
        with patch('signal.signal') as mock_signal:
            lifecycle_manager._setup_signal_handlers()
            
            # Verify signal handlers are registered (Unix/Linux only)
            if hasattr(signal, 'SIGTERM'):
                mock_signal.assert_any_call(signal.SIGTERM, lifecycle_manager._signal_handlers.get(signal.SIGTERM))
                mock_signal.assert_any_call(signal.SIGINT, lifecycle_manager._signal_handlers.get(signal.SIGINT))
    
    async def test_component_status_retrieval(self, lifecycle_manager):
        """Test component status information retrieval."""
        await lifecycle_manager.initialize_components()
        
        # Get all component status
        all_status = await lifecycle_manager.get_component_status()
        
        assert 'components' in all_status
        assert 'running' in all_status
        assert 'lifecycle_metrics' in all_status
        assert len(all_status['components']) == 5
        
        # Get specific component status
        specific_status = await lifecycle_manager.get_component_status('database')
        
        assert specific_status['name'] == 'database'
        assert 'state' in specific_status
        assert 'health_status' in specific_status
        assert 'dependencies' in specific_status
    
    async def test_error_handling_during_startup(self, lifecycle_manager):
        """Test error handling during component startup."""
        # Mock component creation to fail
        with patch.object(lifecycle_manager, '_create_component', side_effect=Exception("Component creation failed")):
            with pytest.raises(EnrichmentError, match="Component initialization failed"):
                await lifecycle_manager.initialize_components()
    
    async def test_dependency_validation_failure(self, lifecycle_manager):
        """Test dependency validation failure handling."""
        lifecycle_manager._setup_component_dependencies()
        
        # Mock database manager to fail health check
        lifecycle_manager.db_manager.health_check = AsyncMock(return_value={'status': 'unhealthy'})
        
        # Initialize components (should still succeed)
        await lifecycle_manager._initialize_component_instances()
        
        # Dependency validation should fail
        with pytest.raises(EnrichmentError, match="Dependency validation failed"):
            await lifecycle_manager._validate_all_dependencies()


class TestLifecycleManagerIntegration:
    """Integration tests for lifecycle manager with real components."""
    
    @pytest.fixture
    def enrichment_config(self):
        """Create test enrichment configuration."""
        return EnrichmentConfig(
            max_concurrent_tasks=2,
            task_timeout_seconds=10,
            retry_delay_seconds=1,
            queue_poll_interval=1,
            batch_size=3
        )
    
    async def test_lifecycle_manager_factory_creation(self, enrichment_config):
        """Test lifecycle manager creation through factory."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            mock_db = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
            mock_create_db.return_value = mock_db
            
            lifecycle_manager = create_lifecycle_manager(enrichment_config)
            
            assert lifecycle_manager is not None
            assert lifecycle_manager.config == enrichment_config
            assert lifecycle_manager.db_manager == mock_db
    
    async def test_complete_system_creation(self, enrichment_config):
        """Test complete enrichment system creation with lifecycle management."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            with patch('src.enrichment.config.get_enrichment_config') as mock_get_config:
                mock_db = AsyncMock()
                mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
                mock_create_db.return_value = mock_db
                mock_get_config.return_value = enrichment_config
                
                lifecycle_manager = await create_complete_enrichment_system()
                
                assert lifecycle_manager is not None
                assert len(lifecycle_manager._components) == 5
                assert all(
                    status.state == ComponentState.STOPPED 
                    for status in lifecycle_manager._component_status.values()
                )
    
    async def test_full_lifecycle_workflow(self, enrichment_config):
        """Test complete lifecycle workflow from creation to shutdown."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            with patch('src.enrichment.config.get_enrichment_config') as mock_get_config:
                # Setup mocks
                mock_db = AsyncMock()
                mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
                mock_connection = AsyncMock()
                mock_connection.execute = AsyncMock()
                mock_db.get_connection.return_value.__aenter__.return_value = mock_connection
                mock_db.get_connection.return_value.__aexit__.return_value = None
                mock_create_db.return_value = mock_db
                mock_get_config.return_value = enrichment_config
                
                # Create and initialize system
                lifecycle_manager = await create_complete_enrichment_system(shutdown_timeout=2.0)
                
                # Start all components
                startup_result = await lifecycle_manager.start_all_components()
                assert startup_result['status'] == 'success'
                
                # Verify running state
                assert lifecycle_manager._running is True
                
                # Perform health check
                health_result = await lifecycle_manager.health_check()
                assert health_result['status'] in ['healthy', 'degraded']
                
                # Graceful shutdown
                shutdown_result = await lifecycle_manager.graceful_shutdown()
                assert 'shutdown_time_seconds' in shutdown_result
                assert lifecycle_manager._running is False


class TestLifecycleManagerPerformance:
    """Performance tests for lifecycle management operations."""
    
    @pytest.fixture
    def enrichment_config(self):
        """Create test enrichment configuration."""
        return EnrichmentConfig(
            max_concurrent_tasks=5,
            task_timeout_seconds=30
        )
    
    async def test_startup_performance(self, enrichment_config):
        """Test startup performance meets requirements."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            mock_db = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
            mock_connection = AsyncMock()
            mock_connection.execute = AsyncMock()
            mock_db.get_connection.return_value.__aenter__.return_value = mock_connection
            mock_db.get_connection.return_value.__aexit__.return_value = None
            mock_create_db.return_value = mock_db
            
            lifecycle_manager = LifecycleManager(
                config=enrichment_config,
                db_manager=mock_db,
                shutdown_timeout=5.0
            )
            
            # Measure startup time
            start_time = time.time()
            await lifecycle_manager.initialize_components()
            await lifecycle_manager.start_all_components()
            startup_time = time.time() - start_time
            
            # Startup should complete within reasonable time
            assert startup_time < 5.0
            
            # Measure shutdown time
            start_time = time.time()
            await lifecycle_manager.graceful_shutdown()
            shutdown_time = time.time() - start_time
            
            # Shutdown should complete within timeout
            assert shutdown_time < 6.0
    
    async def test_health_check_performance(self, enrichment_config):
        """Test health check performance."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            mock_db = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
            mock_create_db.return_value = mock_db
            
            lifecycle_manager = LifecycleManager(
                config=enrichment_config,
                db_manager=mock_db
            )
            
            await lifecycle_manager.initialize_components()
            await lifecycle_manager.start_all_components()
            
            # Measure health check time
            start_time = time.time()
            health_result = await lifecycle_manager.health_check()
            health_check_time = time.time() - start_time
            
            # Health check should be fast
            assert health_check_time < 1.0
            assert 'status' in health_result


class TestLifecycleManagerErrorConditions:
    """Test error conditions and edge cases for lifecycle management."""
    
    @pytest.fixture
    def enrichment_config(self):
        """Create test enrichment configuration."""
        return EnrichmentConfig()
    
    async def test_startup_with_failed_dependency(self, enrichment_config):
        """Test startup behavior when dependencies fail."""
        # Mock failing database manager
        mock_db = AsyncMock()
        mock_db.get_connection.side_effect = Exception("Database connection failed")
        
        lifecycle_manager = LifecycleManager(
            config=enrichment_config,
            db_manager=mock_db
        )
        
        # Initialization should fail due to dependency validation
        with pytest.raises(EnrichmentError):
            await lifecycle_manager.initialize_components()
    
    async def test_shutdown_timeout_handling(self, enrichment_config):
        """Test shutdown timeout handling."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            mock_db = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
            mock_connection = AsyncMock()
            mock_connection.execute = AsyncMock()
            mock_db.get_connection.return_value.__aenter__.return_value = mock_connection
            mock_db.get_connection.return_value.__aexit__.return_value = None
            mock_create_db.return_value = mock_db
            
            lifecycle_manager = LifecycleManager(
                config=enrichment_config,
                db_manager=mock_db,
                shutdown_timeout=0.1  # Very short timeout
            )
            
            await lifecycle_manager.initialize_components()
            await lifecycle_manager.start_all_components()
            
            # Mock slow component shutdown
            with patch.object(lifecycle_manager, '_stop_component', new_callable=AsyncMock) as mock_stop:
                async def slow_stop(*args, **kwargs):
                    await asyncio.sleep(0.2)  # Longer than timeout
                    return {'status': 'stopped'}
                
                mock_stop.side_effect = slow_stop
                
                # Shutdown should handle timeout gracefully
                shutdown_result = await lifecycle_manager.graceful_shutdown()
                assert 'shutdown_time_seconds' in shutdown_result
    
    async def test_component_recovery_failure(self, enrichment_config):
        """Test component recovery failure handling."""
        with patch('src.database.connection.create_database_manager') as mock_create_db:
            mock_db = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={'status': 'healthy'})
            mock_connection = AsyncMock()
            mock_connection.execute = AsyncMock()
            mock_db.get_connection.return_value.__aenter__.return_value = mock_connection
            mock_db.get_connection.return_value.__aexit__.return_value = None
            mock_create_db.return_value = mock_db
            
            lifecycle_manager = LifecycleManager(
                config=enrichment_config,
                db_manager=mock_db,
                shutdown_timeout=1.0
            )
            
            await lifecycle_manager.initialize_components()
            await lifecycle_manager.start_all_components()
            
            # Mock component start to fail during recovery
            with patch.object(lifecycle_manager, '_start_component', side_effect=Exception("Start failed")):
                # Recovery should handle failure gracefully
                await lifecycle_manager._recover_component('task_queue')
                
                # Component should be marked as failed
                status = lifecycle_manager._component_status['task_queue']
                assert status.state == ComponentState.FAILED
                assert "Recovery failed" in status.error_message


if __name__ == "__main__":
    pytest.main([__file__])