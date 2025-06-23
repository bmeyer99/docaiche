"""
Configuration System Tests - PRD-003 CFG-007
Unit tests for hierarchical configuration loading, environment variable parsing,
database override functionality, and configuration validation.

Tests all components of the configuration management system exactly as specified
in PRD-003 requirements.
"""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.core.config.models import (
    AppConfig, ContentConfig, AnythingLLMConfig, GitHubConfig,
    ScrapingConfig, RedisConfig, AIConfig, OllamaConfig, OpenAIConfig,
    SystemConfiguration
)
from src.core.config.manager import ConfigurationManager, get_configuration_manager
from src.core.config.loader import ConfigurationLoader, create_configuration_loader
from src.core.config.defaults import get_environment_overrides, apply_nested_override
from src.core.config.secrets import SecretsManager
from src.core.config.validation import ConfigurationValidators


class TestConfigurationModels:
    """Test CFG-001: Configuration Schema Models"""
    
    def test_app_config_validation(self):
        """Test AppConfig validation with all fields"""
        config = AppConfig(
            version="1.0.0",
            environment="production",
            debug=False,
            log_level="INFO",
            data_dir="/app/data",
            api_host="0.0.0.0",
            api_port=8080,
            web_port=8081,
            workers=4
        )
        
        assert config.version == "1.0.0"
        assert config.environment == "production"
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.api_port == 8080
        assert config.workers == 4
    
    def test_app_config_port_validation(self):
        """Test AppConfig port range validation"""
        with pytest.raises(ValueError):
            AppConfig(api_port=1023)  # Below minimum
        
        with pytest.raises(ValueError):
            AppConfig(api_port=65536)  # Above maximum
    
    def test_content_config_validation(self):
        """Test ContentConfig validation and defaults"""
        config = ContentConfig()
        
        assert config.chunk_size_default == 1000
        assert config.chunk_size_max == 4000
        assert config.chunk_overlap == 100
        assert config.quality_threshold == 0.3
        assert config.min_content_length == 50
        assert config.max_content_length == 1000000
    
    def test_redis_config_validation(self):
        """Test RedisConfig validation including memory format"""
        config = RedisConfig(
            host="redis",
            port=6379,
            password="test-password",
            maxmemory="512mb",
            ssl=False
        )
        
        assert config.host == "redis"
        assert config.port == 6379
        assert config.password == "test-password"
        assert config.maxmemory == "512mb"
        assert config.ssl is False
    
    def test_redis_memory_format_validation(self):
        """Test Redis memory format validation"""
        # Valid formats
        valid_formats = ["512mb", "1gb", "256MB", "2GB", "128m", "4g"]
        for format_str in valid_formats:
            config = RedisConfig(maxmemory=format_str)
            assert config.maxmemory == format_str.lower()
        
        # Invalid formats
        with pytest.raises(ValueError):
            RedisConfig(maxmemory="invalid")
    
    def test_anythingllm_config_validation(self):
        """Test AnythingLLMConfig endpoint and API key validation"""
        config = AnythingLLMConfig(
            endpoint="http://anythingllm:3001",
            api_key="test-api-key-12345"
        )
        
        assert config.endpoint == "http://anythingllm:3001"
        assert config.api_key == "test-api-key-12345"
        assert config.circuit_breaker.failure_threshold == 3
    
    def test_anythingllm_endpoint_validation(self):
        """Test AnythingLLM endpoint URL validation"""
        with pytest.raises(ValueError):
            AnythingLLMConfig(
                endpoint="invalid-url",
                api_key="test-key"
            )
    
    def test_ai_config_with_providers(self):
        """Test AIConfig with nested provider configurations"""
        config = AIConfig(
            primary_provider="ollama",
            fallback_provider="openai",
            enable_failover=True,
            ollama=OllamaConfig(
                endpoint="http://ollama:11434",
                model="llama2"
            ),
            openai=OpenAIConfig(
                api_key="test-openai-key",
                model="gpt-3.5-turbo"
            )
        )
        
        assert config.primary_provider == "ollama"
        assert config.fallback_provider == "openai"
        assert config.enable_failover is True
        assert config.ollama.endpoint == "http://ollama:11434"
        assert config.openai.api_key == "test-openai-key"
    
    def test_system_configuration_complete(self):
        """Test complete SystemConfiguration assembly"""
        system_config = SystemConfiguration(
            app=AppConfig(),
            content=ContentConfig(),
            anythingllm=AnythingLLMConfig(
                endpoint="http://test:3001",
                api_key="test-key"
            ),
            github=GitHubConfig(api_token="github-token"),
            scraping=ScrapingConfig(),
            redis=RedisConfig(),
            ai=AIConfig(
                ollama=OllamaConfig(),
                openai=OpenAIConfig(api_key="openai-key")
            )
        )
        
        assert isinstance(system_config.app, AppConfig)
        assert isinstance(system_config.content, ContentConfig)
        assert isinstance(system_config.anythingllm, AnythingLLMConfig)
        assert isinstance(system_config.redis, RedisConfig)
        assert isinstance(system_config.ai, AIConfig)


class TestEnvironmentVariableParsing:
    """Test CFG-004: Environment Variable Parsing"""
    
    def test_environment_overrides_basic(self):
        """Test basic environment variable parsing"""
        with patch.dict(os.environ, {
            'APP_ENVIRONMENT': 'development',
            'APP_DEBUG': 'true',
            'APP_LOG_LEVEL': 'DEBUG',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6380'
        }):
            overrides = get_environment_overrides()
            
            assert overrides['app.environment'] == 'development'
            assert overrides['app.debug'] is True
            assert overrides['app.log_level'] == 'DEBUG'
            assert overrides['redis.host'] == 'localhost'
            assert overrides['redis.port'] == 6380
    
    def test_environment_nested_keys(self):
        """Test nested configuration key support"""
        with patch.dict(os.environ, {
            'AI_PRIMARY_PROVIDER': 'openai',
            'AI_OLLAMA_MODEL': 'llama3',
            'AI_OPENAI_TEMPERATURE': '0.5'
        }):
            overrides = get_environment_overrides()
            
            assert overrides['ai.primary_provider'] == 'openai'
            assert overrides['ai.ollama.model'] == 'llama3'
            assert overrides['ai.openai.temperature'] == 0.5
    
    def test_apply_nested_override(self):
        """Test nested override application"""
        config_dict = {}
        
        apply_nested_override(config_dict, 'app.debug', True)
        apply_nested_override(config_dict, 'redis.host', 'localhost')
        apply_nested_override(config_dict, 'ai.ollama.model', 'llama2')
        
        assert config_dict['app']['debug'] is True
        assert config_dict['redis']['host'] == 'localhost'
        assert config_dict['ai']['ollama']['model'] == 'llama2'
    
    def test_redis_environment_mapping(self):
        """Test Redis-specific environment variable mapping"""
        with patch.dict(os.environ, {
            'REDIS_HOST': 'redis-server',
            'REDIS_PASSWORD': 'secret-password',
            'REDIS_SSL': 'true',
            'REDIS_MAXMEMORY': '1gb'
        }):
            overrides = get_environment_overrides()
            
            assert overrides['redis.host'] == 'redis-server'
            assert overrides['redis.password'] == 'secret-password'
            assert overrides['redis.ssl'] is True
            assert overrides['redis.maxmemory'] == '1gb'


class TestConfigurationValidation:
    """Test configuration validators"""
    
    def test_endpoint_url_validator(self):
        """Test endpoint URL validation"""
        # Valid URLs
        assert ConfigurationValidators.validate_endpoint_url("http://localhost:8080") == "http://localhost:8080"
        assert ConfigurationValidators.validate_endpoint_url("https://api.example.com/") == "https://api.example.com"
        
        # Invalid URLs
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_endpoint_url("invalid-url")
    
    def test_api_key_validator(self):
        """Test API key validation"""
        # Valid API key
        assert ConfigurationValidators.validate_api_key("test-api-key-12345") == "test-api-key-12345"
        
        # Invalid API keys
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_api_key("short")
        
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_api_key("")
    
    def test_user_agent_validator(self):
        """Test user agent validation"""
        # Valid user agents
        assert ConfigurationValidators.validate_user_agent("DocaicheBot/1.0") == "DocaicheBot/1.0"
        assert ConfigurationValidators.validate_user_agent("Test-Agent_2.0") == "Test-Agent_2.0"
        
        # Invalid user agent
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_user_agent("Invalid@Agent!")
    
    def test_redis_memory_validator(self):
        """Test Redis memory configuration validation"""
        # Valid memory formats
        assert ConfigurationValidators.validate_redis_memory("512mb") == "512mb"
        assert ConfigurationValidators.validate_redis_memory("1GB") == "1gb"
        assert ConfigurationValidators.validate_redis_memory("256M") == "256m"
        
        # Invalid memory format
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_redis_memory("invalid-format")


class TestSecretsManager:
    """Test secrets management functionality"""
    
    def test_production_secrets_validation(self):
        """Test production environment secrets validation"""
        # Valid production config
        config = SystemConfiguration(
            app=AppConfig(environment="production"),
            content=ContentConfig(),
            anythingllm=AnythingLLMConfig(
                endpoint="http://test:3001",
                api_key="valid-api-key"
            ),
            github=GitHubConfig(api_token="github-token"),
            scraping=ScrapingConfig(),
            redis=RedisConfig(password="redis-password"),
            ai=AIConfig(
                primary_provider="ollama",
                ollama=OllamaConfig(),
                openai=OpenAIConfig(api_key="openai-key")
            )
        )
        
        # Should not raise exception
        SecretsManager.validate_production_secrets(config)
    
    def test_production_secrets_missing(self):
        """Test production secrets validation with missing secrets"""
        config = SystemConfiguration(
            app=AppConfig(environment="production"),
            content=ContentConfig(),
            anythingllm=AnythingLLMConfig(
                endpoint="http://test:3001",
                api_key=""  # Missing API key
            ),
            github=GitHubConfig(api_token=""),  # Missing token
            scraping=ScrapingConfig(),
            redis=RedisConfig(),
            ai=AIConfig(
                primary_provider="openai",
                ollama=OllamaConfig(),
                openai=OpenAIConfig(api_key="")  # Missing OpenAI key
            )
        )
        
        with pytest.raises(ValueError) as exc_info:
            SecretsManager.validate_production_secrets(config)
        
        error_message = str(exc_info.value)
        assert "ANYTHINGLLM_API_KEY" in error_message
        assert "GITHUB_API_TOKEN" in error_message
        assert "OPENAI_API_KEY" in error_message
    
    def test_secret_masking(self):
        """Test secret masking for logging"""
        secret = "very-long-secret-key-12345"
        masked = SecretsManager.mask_secret_for_logging(secret, 4)
        assert masked == "*******************2345"
        
        short_secret = "abc"
        masked_short = SecretsManager.mask_secret_for_logging(short_secret)
        assert masked_short == "***"


@pytest.mark.asyncio
class TestConfigurationLoader:
    """Test CFG-003: Hierarchical Configuration Loading"""
    
    async def test_yaml_configuration_loading(self):
        """Test YAML configuration file loading"""
        yaml_content = {
            'app': {
                'environment': 'testing',
                'debug': True,
                'log_level': 'DEBUG'
            },
            'redis': {
                'host': 'yaml-redis',
                'port': 6380
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            loader = ConfigurationLoader(yaml_file)
            yaml_config = await loader._load_yaml_configuration()
            
            assert yaml_config['app']['environment'] == 'testing'
            assert yaml_config['app']['debug'] is True
            assert yaml_config['redis']['host'] == 'yaml-redis'
            assert yaml_config['redis']['port'] == 6380
            
        finally:
            os.unlink(yaml_file)
    
    async def test_database_configuration_loading(self):
        """Test database configuration loading"""
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = [
            MagicMock(config_key='app.debug', config_value='true'),
            MagicMock(config_key='redis.host', config_value='db-redis'),
            MagicMock(config_key='content.chunk_size_default', config_value='2000')
        ]
        
        loader = ConfigurationLoader()
        await loader.set_database_manager(mock_db_manager)
        
        config_dict = await loader._load_database_configuration()
        
        assert config_dict['app']['debug'] == 'true'
        assert config_dict['redis']['host'] == 'db-redis'
        assert config_dict['content']['chunk_size_default'] == '2000'
    
    async def test_hierarchical_priority(self):
        """Test hierarchical configuration priority: env > yaml > database"""
        # Database config (lowest priority)
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = [
            MagicMock(config_key='app.debug', config_value='false'),
            MagicMock(config_key='redis.host', config_value='db-redis')
        ]
        
        # YAML config (medium priority)
        yaml_content = {
            'app': {'debug': True},  # Overrides database
            'redis': {'host': 'yaml-redis'},  # Overrides database
            'content': {'chunk_size_default': 1500}  # New value
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            # Environment variables (highest priority)
            with patch.dict(os.environ, {
                'APP_DEBUG': 'false',  # Overrides YAML
                'REDIS_PORT': '6380'   # New value
            }):
                loader = ConfigurationLoader(yaml_file)
                await loader.set_database_manager(mock_db_manager)
                
                config = await loader.load_hierarchical_configuration()
                
                # Environment wins
                assert config.app.debug is False
                
                # YAML wins over database
                assert config.redis.host == 'yaml-redis'
                assert config.content.chunk_size_default == 1500
                
                # Environment adds new value
                assert config.redis.port == 6380
                
        finally:
            os.unlink(yaml_file)
    
    async def test_configuration_validation_sources(self):
        """Test configuration source validation"""
        loader = ConfigurationLoader("nonexistent.yaml")
        
        validation = await loader.validate_configuration_sources()
        
        assert validation['database']['available'] is False
        assert validation['yaml_file']['available'] is False
        assert 'environment' in validation


@pytest.mark.asyncio
class TestConfigurationManager:
    """Test CFG-002: ConfigurationManager Class"""
    
    async def test_singleton_pattern(self):
        """Test ConfigurationManager singleton pattern"""
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()
        
        assert manager1 is manager2
    
    async def test_configuration_loading_with_manager(self):
        """Test configuration loading through manager"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = []
        manager._db_manager = mock_db_manager
        
        with patch.dict(os.environ, {
            'APP_ENVIRONMENT': 'testing',
            'ANYTHINGLLM_API_KEY': 'test-key',
            'GITHUB_API_TOKEN': 'github-token',
            'OPENAI_API_KEY': 'openai-key'
        }):
            config = await manager.load_configuration()
            
            assert isinstance(config, SystemConfiguration)
            assert config.app.environment == 'testing'
    
    async def test_database_configuration_update(self):
        """Test updating configuration in database"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        manager._db_manager = mock_db_manager
        
        await manager.update_in_db('app.debug', True)
        
        # Verify database update was called
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        assert 'INSERT OR REPLACE INTO system_config' in call_args[0][0]
    
    async def test_hot_reload_configuration(self):
        """Test configuration hot-reloading"""
        yaml_content = {'app': {'debug': False}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            manager = ConfigurationManager()
            await manager.initialize(yaml_file, watch_file=True)
            
            # Initial load
            config1 = await manager.load_configuration()
            initial_debug = config1.app.debug
            
            # Modify file
            updated_content = {'app': {'debug': not initial_debug}}
            with open(yaml_file, 'w') as f:
                yaml.dump(updated_content, f)
            
            # Check for changes
            changed = await manager.check_for_config_file_changes()
            
            assert changed is True
            
        finally:
            os.unlink(yaml_file)


class TestConfigurationIntegration:
    """Test configuration system integration"""
    
    def test_legacy_compatibility(self):
        """Test backward compatibility with existing code"""
        from src.core.config import get_system_configuration
        
        with patch.dict(os.environ, {
            'ANYTHINGLLM_API_KEY': 'test-key',
            'GITHUB_API_TOKEN': 'github-token', 
            'OPENAI_API_KEY': 'openai-key'
        }):
            config = get_system_configuration()
            
            assert isinstance(config, SystemConfiguration)
            assert hasattr(config, 'app')
            assert hasattr(config, 'redis')
            assert hasattr(config, 'ai')
    
    def test_fastapi_dependency_integration(self):
        """Test FastAPI dependency injection compatibility"""
        from src.core.config import get_settings
        
        with patch.dict(os.environ, {
            'ANYTHINGLLM_API_KEY': 'test-key',
            'GITHUB_API_TOKEN': 'github-token',
            'OPENAI_API_KEY': 'openai-key'
        }):
            settings = get_settings()
            
            assert isinstance(settings, SystemConfiguration)


if __name__ == '__main__':
    pytest.main([__file__])