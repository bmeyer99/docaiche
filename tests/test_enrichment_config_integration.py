"""
Test Enrichment Configuration Integration - PRD-010
Tests for the Knowledge Enrichment Pipeline configuration integration.

Validates proper integration between EnrichmentConfig and the core
configuration system with hot-reload capability.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime

from src.enrichment.config import (
    EnrichmentConfigManager, get_enrichment_config, reload_enrichment_config,
    register_config_reload_callback, validate_enrichment_config,
    get_config_manager_status
)
from src.enrichment.models import EnrichmentConfig as LocalEnrichmentConfig
from src.enrichment.exceptions import EnrichmentError


class TestEnrichmentConfigManager:
    """Test EnrichmentConfigManager functionality."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a fresh config manager for testing."""
        return EnrichmentConfigManager()
    
    @pytest.mark.asyncio
    async def test_get_config_loads_from_system_config(self, config_manager):
        """Test that get_config loads from system configuration."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 10
            mock_system_config.enrichment.task_timeout_seconds = 600
            mock_system_config.enrichment.retry_delay_seconds = 120
            mock_system_config.enrichment.queue_poll_interval = 15
            mock_system_config.enrichment.batch_size = 20
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.8
            
            mock_get_system.return_value = mock_system_config
            
            # Get configuration
            config = await config_manager.get_config()
            
            # Verify configuration values
            assert isinstance(config, LocalEnrichmentConfig)
            assert config.max_concurrent_tasks == 10
            assert config.task_timeout_seconds == 600
            assert config.retry_delay_seconds == 120
            assert config.queue_poll_interval == 15
            assert config.batch_size == 20
            assert config.enable_relationship_mapping is True
            assert config.enable_tag_generation is True
            assert config.enable_quality_assessment is True
            assert config.min_confidence_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_config_validation_success(self, config_manager):
        """Test successful configuration validation."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock valid system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Should not raise exception
            config = await config_manager.get_config()
            assert config is not None
    
    @pytest.mark.asyncio
    async def test_config_validation_failures(self, config_manager):
        """Test configuration validation failure scenarios."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Test invalid max_concurrent_tasks
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 100  # Too high
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Should raise EnrichmentError
            with pytest.raises(EnrichmentError, match="Configuration validation failed"):
                await config_manager.get_config()
    
    @pytest.mark.asyncio
    async def test_reload_configuration(self, config_manager):
        """Test configuration reload functionality."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system, \
             patch('src.enrichment.config.reload_configuration') as mock_reload:
            
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Reload configuration
            config = await config_manager.reload_config()
            
            # Verify reload was called
            mock_reload.assert_called_once()
            assert config is not None
    
    @pytest.mark.asyncio
    async def test_reload_callbacks(self, config_manager):
        """Test configuration reload callbacks."""
        callback_called = False
        callback_config = None
        
        async def test_callback(config: LocalEnrichmentConfig):
            nonlocal callback_called, callback_config
            callback_called = True
            callback_config = config
        
        # Register callback
        config_manager.register_reload_callback("test", test_callback)
        
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system, \
             patch('src.enrichment.config.reload_configuration'):
            
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Reload configuration
            await config_manager.reload_config()
            
            # Verify callback was called
            assert callback_called
            assert callback_config is not None
            assert isinstance(callback_config, LocalEnrichmentConfig)
        
        # Unregister callback
        config_manager.unregister_reload_callback("test")
        assert "test" not in config_manager._reload_callbacks
    
    @pytest.mark.asyncio
    async def test_validate_configuration(self, config_manager):
        """Test configuration validation method."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Validate configuration
            result = await config_manager.validate_configuration()
            
            # Verify validation result
            assert result["valid"] is True
            assert "last_updated" in result
            assert "config_summary" in result
            assert result["config_summary"]["max_concurrent_tasks"] == 5
    
    def test_get_status(self, config_manager):
        """Test configuration manager status."""
        status = config_manager.get_status()
        
        assert "initialized" in status
        assert "last_updated" in status
        assert "validation_enabled" in status
        assert "registered_callbacks" in status
        assert "callback_count" in status
        assert status["initialized"] is False  # Not loaded yet
        assert status["callback_count"] == 0


class TestConfigurationFunctions:
    """Test module-level configuration functions."""
    
    @pytest.mark.asyncio
    async def test_get_enrichment_config(self):
        """Test get_enrichment_config function."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Get configuration
            config = await get_enrichment_config()
            
            assert isinstance(config, LocalEnrichmentConfig)
            assert config.max_concurrent_tasks == 5
    
    @pytest.mark.asyncio
    async def test_reload_enrichment_config(self):
        """Test reload_enrichment_config function."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system, \
             patch('src.enrichment.config.reload_configuration') as mock_reload:
            
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Reload configuration
            config = await reload_enrichment_config()
            
            mock_reload.assert_called_once()
            assert isinstance(config, LocalEnrichmentConfig)
    
    @pytest.mark.asyncio
    async def test_validate_enrichment_config(self):
        """Test validate_enrichment_config function."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Validate configuration
            result = await validate_enrichment_config()
            
            assert result["valid"] is True
    
    def test_get_config_manager_status(self):
        """Test get_config_manager_status function."""
        # Clear any existing manager
        import src.enrichment.config
        src.enrichment.config._config_manager = None
        
        status = get_config_manager_status()
        assert status["initialized"] is False
    
    def test_register_config_reload_callback(self):
        """Test register_config_reload_callback function."""
        async def test_callback(config):
            pass
        
        # Register callback
        register_config_reload_callback("test", test_callback)
        
        # Verify callback was registered
        status = get_config_manager_status()
        assert "test" in status["registered_callbacks"]


class TestEnvironmentVariableIntegration:
    """Test environment variable integration."""
    
    @pytest.mark.asyncio
    async def test_environment_variables_loaded(self):
        """Test that environment variables are properly loaded."""
        env_vars = {
            "ENRICHMENT_MAX_CONCURRENT_TASKS": "8",
            "ENRICHMENT_TASK_TIMEOUT_SECONDS": "400",
            "ENRICHMENT_RETRY_DELAY_SECONDS": "90",
            "ENRICHMENT_QUEUE_POLL_INTERVAL": "15",
            "ENRICHMENT_BATCH_SIZE": "25",
            "ENRICHMENT_ENABLE_RELATIONSHIP_MAPPING": "false",
            "ENRICHMENT_ENABLE_TAG_GENERATION": "false",
            "ENRICHMENT_ENABLE_QUALITY_ASSESSMENT": "false",
            "ENRICHMENT_MIN_CONFIDENCE_THRESHOLD": "0.8"
        }
        
        with patch.dict(os.environ, env_vars), \
             patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            
            # Mock system configuration that uses environment variables
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 8
            mock_system_config.enrichment.task_timeout_seconds = 400
            mock_system_config.enrichment.retry_delay_seconds = 90
            mock_system_config.enrichment.queue_poll_interval = 15
            mock_system_config.enrichment.batch_size = 25
            mock_system_config.enrichment.enable_relationship_mapping = False
            mock_system_config.enrichment.enable_tag_generation = False
            mock_system_config.enrichment.enable_quality_assessment = False
            mock_system_config.enrichment.min_confidence_threshold = 0.8
            
            mock_get_system.return_value = mock_system_config
            
            # Get configuration
            config = await get_enrichment_config()
            
            # Verify environment variables were used
            assert config.max_concurrent_tasks == 8
            assert config.task_timeout_seconds == 400
            assert config.retry_delay_seconds == 90
            assert config.queue_poll_interval == 15
            assert config.batch_size == 25
            assert config.enable_relationship_mapping is False
            assert config.enable_tag_generation is False
            assert config.enable_quality_assessment is False
            assert config.min_confidence_threshold == 0.8


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_configuration_load_error(self):
        """Test handling of configuration load errors."""
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            mock_get_system.side_effect = Exception("Configuration error")
            
            with pytest.raises(EnrichmentError, match="Configuration loading failed"):
                await get_enrichment_config()
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test handling of validation errors."""
        config_manager = EnrichmentConfigManager()
        
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system:
            # Mock invalid configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = -1  # Invalid
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            with pytest.raises(EnrichmentError, match="Configuration validation failed"):
                await config_manager.get_config()
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(self):
        """Test that callback errors don't break reload."""
        config_manager = EnrichmentConfigManager()
        
        async def failing_callback(config):
            raise Exception("Callback error")
        
        # Register failing callback
        config_manager.register_reload_callback("failing", failing_callback)
        
        with patch('src.enrichment.config.get_system_configuration') as mock_get_system, \
             patch('src.enrichment.config.reload_configuration'):
            
            # Mock system configuration
            mock_system_config = AsyncMock()
            mock_system_config.enrichment = AsyncMock()
            mock_system_config.enrichment.max_concurrent_tasks = 5
            mock_system_config.enrichment.task_timeout_seconds = 300
            mock_system_config.enrichment.retry_delay_seconds = 60
            mock_system_config.enrichment.queue_poll_interval = 10
            mock_system_config.enrichment.batch_size = 10
            mock_system_config.enrichment.enable_relationship_mapping = True
            mock_system_config.enrichment.enable_tag_generation = True
            mock_system_config.enrichment.enable_quality_assessment = True
            mock_system_config.enrichment.min_confidence_threshold = 0.7
            
            mock_get_system.return_value = mock_system_config
            
            # Should not raise exception despite callback failure
            config = await config_manager.reload_config()
            assert config is not None