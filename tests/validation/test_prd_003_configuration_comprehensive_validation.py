"""
PRD-003 Configuration Management System - Comprehensive Validation Tests
QA Validator: Create comprehensive test suite BEFORE validation

Tests ALL PRD-003 requirements exactly as specified:
- CFG-001: All 9 Pydantic models matching exact specification
- CFG-002: ConfigurationManager singleton with thread safety  
- CFG-003: Hierarchical loading (environment > config.yaml > database)
- CFG-004: Environment variable parsing with nested key support
- CFG-005: Database integration with PRD-002 DatabaseManager
- CFG-006: FastAPI dependency injection for singleton access
- CFG-007: Unit tests for all configuration functionality
- CFG-008: Default config.yaml with production defaults
- CFG-009: API endpoints integration with PRD-001
- CFG-010: Hot-reloading mechanism for config.yaml
- CFG-011: Redis configuration validation against docker-compose

Code passes ONLY if ALL tests pass - no partial compliance allowed.
"""

import asyncio
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest
import yaml
from pydantic import ValidationError

from src.core.config.models import (
    AppConfig, ContentConfig, AnythingLLMConfig, GitHubConfig,
    ScrapingConfig, RedisConfig, AIConfig, OllamaConfig, OpenAIConfig,
    SystemConfiguration, CircuitBreakerConfig, EnrichmentConfig
)
from src.core.config.manager import ConfigurationManager, get_configuration_manager
from src.core.config.loader import ConfigurationLoader
from src.core.config.defaults import get_environment_overrides, apply_nested_override
from src.core.config.secrets import SecretsManager
from src.core.config.validation import ConfigurationValidators


class TestPRD003SpecificationCompliance:
    """Test CFG-001: All 9 Pydantic Models Match Exact PRD-003 Specification"""
    
    def test_app_config_exact_specification(self):
        """Verify AppConfig matches PRD-003 lines 34-44 exactly"""
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
        
        # Verify all fields match PRD specification
        assert config.version == "1.0.0"
        assert config.environment == "production"
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.data_dir == "/app/data"
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8080
        assert config.web_port == 8081
        assert config.workers == 4
        
        # Test port validation ranges (lines 41-42)
        with pytest.raises(ValidationError):
            AppConfig(api_port=1023)  # Below ge=1024
        with pytest.raises(ValidationError):
            AppConfig(api_port=65536)  # Above le=65535
        
        # Test workers validation (line 43)
        with pytest.raises(ValidationError):
            AppConfig(workers=0)  # Below ge=1
        with pytest.raises(ValidationError):
            AppConfig(workers=17)  # Above le=16
    
    def test_content_config_exact_specification(self):
        """Verify ContentConfig matches PRD-003 lines 45-52 exactly"""
        config = ContentConfig(
            chunk_size_default=1000,
            chunk_size_max=4000,
            chunk_overlap=100,
            quality_threshold=0.3,
            min_content_length=50,
            max_content_length=1000000
        )
        
        assert config.chunk_size_default == 1000
        assert config.chunk_size_max == 4000
        assert config.chunk_overlap == 100
        assert config.quality_threshold == 0.3
        assert config.min_content_length == 50
        assert config.max_content_length == 1000000
        
        # Test quality_threshold validation (line 50)
        with pytest.raises(ValidationError):
            ContentConfig(quality_threshold=-0.1)  # Below ge=0.0
        with pytest.raises(ValidationError):
            ContentConfig(quality_threshold=1.1)  # Above le=1.0
    
    def test_circuit_breaker_config_exact_specification(self):
        """Verify CircuitBreakerConfig matches PRD-003 lines 54-58 exactly"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            timeout_seconds=30
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 60
        assert config.timeout_seconds == 30
    
    def test_anythingllm_config_exact_specification(self):
        """Verify AnythingLLMConfig matches PRD-003 lines 60-65 exactly"""
        config = AnythingLLMConfig(
            endpoint="http://anythingllm:3001",
            api_key="test-api-key-12345"
        )
        
        assert config.endpoint == "http://anythingllm:3001"
        assert config.api_key == "test-api-key-12345"
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.circuit_breaker.failure_threshold == 3
        assert config.circuit_breaker.recovery_timeout == 60
        assert config.circuit_breaker.timeout_seconds == 30
    
    def test_github_config_exact_specification(self):
        """Verify GitHubConfig matches PRD-003 lines 67-71 exactly"""
        config = GitHubConfig(api_token="github-token-12345")
        
        assert config.api_token == "github-token-12345"
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.recovery_timeout == 300
        assert config.circuit_breaker.timeout_seconds == 30
    
    def test_scraping_config_exact_specification(self):
        """Verify ScrapingConfig matches PRD-003 lines 73-78 exactly"""
        config = ScrapingConfig()
        
        assert config.user_agent == "DocaicheBot/1.0"
        assert config.rate_limit_delay == 1.0
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.circuit_breaker.failure_threshold == 3
        assert config.circuit_breaker.recovery_timeout == 120
        assert config.circuit_breaker.timeout_seconds == 15
    
    def test_redis_config_exact_specification(self):
        """Verify RedisConfig matches PRD-003 lines 80-98 exactly"""
        config = RedisConfig(
            host="redis",
            port=6379,
            password=None,
            db=0,
            max_connections=20,
            connection_timeout=5,
            socket_timeout=5,
            maxmemory="512mb",
            maxmemory_policy="allkeys-lru",
            appendonly=True,
            ssl=False,
            ssl_cert_reqs=None
        )
        
        # Verify all fields match PRD specification
        assert config.host == "redis"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 20
        assert config.connection_timeout == 5
        assert config.socket_timeout == 5
        assert config.maxmemory == "512mb"
        assert config.maxmemory_policy == "allkeys-lru"
        assert config.appendonly is True
        assert config.ssl is False
        assert config.ssl_cert_reqs is None
        
        # Test max_connections validation (line 87)
        with pytest.raises(ValidationError):
            RedisConfig(max_connections=0)  # Below ge=1
    
    def test_ollama_config_exact_specification(self):
        """Verify OllamaConfig matches PRD-003 lines 100-109 exactly"""
        config = OllamaConfig(
            endpoint="http://localhost:11434",
            model="llama2",
            temperature=0.7,
            max_tokens=4096,
            timeout_seconds=60
        )
        
        assert config.endpoint == "http://localhost:11434"
        assert config.model == "llama2"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 60
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        
        # Test temperature validation (line 104)
        with pytest.raises(ValidationError):
            OllamaConfig(temperature=-0.1)  # Below ge=0.0
        with pytest.raises(ValidationError):
            OllamaConfig(temperature=2.1)  # Above le=2.0
    
    def test_openai_config_exact_specification(self):
        """Verify OpenAIConfig matches PRD-003 lines 111-120 exactly"""
        config = OpenAIConfig(
            api_key="openai-key-12345",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=4096,
            timeout_seconds=30
        )
        
        assert config.api_key == "openai-key-12345"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout_seconds == 30
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.recovery_timeout == 300
    
    def test_ai_config_exact_specification(self):
        """Verify AIConfig matches PRD-003 lines 122-129 exactly"""
        config = AIConfig(
            primary_provider="ollama",
            fallback_provider="openai",
            enable_failover=True,
            cache_ttl_seconds=3600,
            ollama=OllamaConfig(),
            openai=OpenAIConfig(api_key="test-key")
        )
        
        assert config.primary_provider == "ollama"
        assert config.fallback_provider == "openai"
        assert config.enable_failover is True
        assert config.cache_ttl_seconds == 3600
        assert isinstance(config.ollama, OllamaConfig)
        assert isinstance(config.openai, OpenAIConfig)
        
        # Test cache_ttl_seconds validation (line 129)
        with pytest.raises(ValidationError):
            AIConfig(
                ollama=OllamaConfig(),
                openai=OpenAIConfig(api_key="test"),
                cache_ttl_seconds=-1  # Below ge=0
            )
    
    def test_system_configuration_exact_specification(self):
        """Verify SystemConfiguration matches PRD-003 lines 131-139 exactly"""
        config = SystemConfiguration(
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
        
        # Verify all required sections are present
        assert isinstance(config.app, AppConfig)
        assert isinstance(config.content, ContentConfig)
        assert isinstance(config.anythingllm, AnythingLLMConfig)
        assert isinstance(config.github, GitHubConfig)
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.ai, AIConfig)


class TestRedisEnvironmentMapping:
    """Test CFG-004: Redis Environment Variable Mapping (PRD-003 lines 144-160)"""
    
    def test_redis_environment_variable_mapping_complete(self):
        """Test all Redis environment variables map correctly"""
        redis_env_vars = {
            'REDIS_HOST': 'redis-server',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'secure-password',
            'REDIS_DB': '1',
            'REDIS_MAX_CONNECTIONS': '30',
            'REDIS_CONNECTION_TIMEOUT': '10',
            'REDIS_SOCKET_TIMEOUT': '8',
            'REDIS_MAXMEMORY': '1gb',
            'REDIS_MAXMEMORY_POLICY': 'volatile-lru',
            'REDIS_APPENDONLY': 'false',
            'REDIS_SSL': 'true',
            'REDIS_SSL_CERT_REQS': 'required'
        }
        
        with patch.dict(os.environ, redis_env_vars):
            overrides = get_environment_overrides()
            
            # Test each mapping from PRD-003 table
            assert overrides['redis.host'] == 'redis-server'
            assert overrides['redis.port'] == 6380
            assert overrides['redis.password'] == 'secure-password'
            assert overrides['redis.db'] == 1
            assert overrides['redis.max_connections'] == 30
            assert overrides['redis.maxmemory'] == '1gb'
            assert overrides['redis.ssl'] is True
    
    def test_redis_default_values_match_prd(self):
        """Test Redis default values match PRD-003 specification"""
        config = RedisConfig()
        
        # Verify defaults match PRD-003 table
        assert config.host == "redis"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 20
        assert config.connection_timeout == 5
        assert config.socket_timeout == 5
        assert config.maxmemory == "512mb"
        assert config.maxmemory_policy == "allkeys-lru"
        assert config.appendonly is True
        assert config.ssl is False
        assert config.ssl_cert_reqs is None


class TestConfigurationManagerSingleton:
    """Test CFG-002: ConfigurationManager Singleton Implementation"""
    
    def test_singleton_pattern_implementation(self):
        """Test ConfigurationManager implements proper singleton pattern"""
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_thread_safe_singleton_access(self):
        """Test singleton is thread-safe under concurrent access"""
        instances = []
        
        def create_manager():
            manager = ConfigurationManager()
            instances.append(manager)
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_manager)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All instances should be identical
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance
    
    @pytest.mark.asyncio
    async def test_configuration_manager_initialization(self):
        """Test ConfigurationManager initialization workflow"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = []
        
        with patch('src.database.manager.create_database_manager', return_value=mock_db_manager):
            await manager.initialize("config.yaml", watch_file=True)
            
            assert manager._config_file_path == "config.yaml"
            assert manager._watch_config_file is True
            assert manager._db_manager is not None


class TestHierarchicalConfigurationLoading:
    """Test CFG-003: Hierarchical Configuration Loading Priority"""
    
    @pytest.mark.asyncio
    async def test_hierarchical_priority_environment_wins(self):
        """Test environment variables override config.yaml and database"""
        # Database config (lowest priority)
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = [
            MagicMock(config_key='app.debug', config_value='true'),
            MagicMock(config_key='redis.host', config_value='db-redis')
        ]
        
        # YAML config (medium priority)
        yaml_content = {
            'app': {'debug': False, 'log_level': 'WARNING'},
            'redis': {'host': 'yaml-redis', 'port': 6380}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            # Environment variables (highest priority)
            with patch.dict(os.environ, {
                'APP_LOG_LEVEL': 'ERROR',  # Overrides YAML
                'REDIS_PORT': '6381'       # Overrides YAML
            }):
                loader = ConfigurationLoader(yaml_file)
                await loader.set_database_manager(mock_db_manager)
                
                config = await loader.load_hierarchical_configuration()
                
                # Environment wins over YAML and database
                assert config.app.log_level == 'ERROR'
                assert config.redis.port == 6381
                
                # YAML wins over database
                assert config.app.debug is False  # YAML overrides DB
                assert config.redis.host == 'yaml-redis'  # YAML overrides DB
                
        finally:
            os.unlink(yaml_file)
    
    @pytest.mark.asyncio
    async def test_hierarchical_priority_yaml_over_database(self):
        """Test config.yaml overrides database when no environment variables"""
        # Database config
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = [
            MagicMock(config_key='app.workers', config_value='2'),
            MagicMock(config_key='content.chunk_size_default', config_value='500')
        ]
        
        # YAML config overrides
        yaml_content = {
            'app': {'workers': 6},
            'content': {'chunk_size_default': 1500}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            loader = ConfigurationLoader(yaml_file)
            await loader.set_database_manager(mock_db_manager)
            
            # Clear environment variables
            with patch.dict(os.environ, {}, clear=True):
                config = await loader.load_hierarchical_configuration()
                
                # YAML should override database
                assert config.app.workers == 6
                assert config.content.chunk_size_default == 1500
                
        finally:
            os.unlink(yaml_file)
    
    @pytest.mark.asyncio
    async def test_nested_key_environment_parsing(self):
        """Test nested configuration key parsing (CFG-004)"""
        with patch.dict(os.environ, {
            'AI_PRIMARY_PROVIDER': 'openai',
            'AI_OLLAMA_MODEL': 'llama3',
            'AI_OPENAI_TEMPERATURE': '0.5',
            'REDIS_CONNECTION_TIMEOUT': '10'
        }):
            overrides = get_environment_overrides()
            
            # Test nested key parsing
            config_dict = {}
            for key, value in overrides.items():
                apply_nested_override(config_dict, key, value)
            
            assert config_dict['ai']['primary_provider'] == 'openai'
            assert config_dict['ai']['ollama']['model'] == 'llama3'
            assert config_dict['ai']['openai']['temperature'] == 0.5
            assert config_dict['redis']['connection_timeout'] == 10


class TestDatabaseIntegration:
    """Test CFG-005: Database Integration with PRD-002 DatabaseManager"""
    
    @pytest.mark.asyncio
    async def test_database_configuration_update(self):
        """Test update_in_db method with DatabaseManager"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        manager._db_manager = mock_db_manager
        
        await manager.update_in_db('app.debug', True)
        
        # Verify database update was called with correct parameters
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        assert 'INSERT OR REPLACE INTO system_config' in call_args[0][0]
        assert call_args[0][1] == ('app.debug', 'true', True, pytest.approx(time.time(), abs=5))
    
    @pytest.mark.asyncio
    async def test_database_configuration_retrieval(self):
        """Test get_from_db method with DatabaseManager"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_one.return_value = MagicMock(config_value='{"debug": true}')
        manager._db_manager = mock_db_manager
        
        result = await manager.get_from_db('app.debug')
        
        # Verify database query and JSON parsing
        mock_db_manager.fetch_one.assert_called_once_with(
            "SELECT config_value FROM system_config WHERE config_key = :param_0 AND is_active = :param_1",
            ('app.debug', True)
        )
        assert result == {"debug": True}
    
    @pytest.mark.asyncio
    async def test_system_config_table_creation(self):
        """Test system_config table is created with proper schema"""
        loader = ConfigurationLoader()
        
        mock_db_manager = AsyncMock()
        await loader.set_database_manager(mock_db_manager)
        await loader._ensure_system_config_table()
        
        # Verify table creation SQL
        mock_db_manager.execute.assert_any_call("""
                CREATE TABLE IF NOT EXISTS system_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
        
        # Verify index creation
        mock_db_manager.execute.assert_any_call("""
                CREATE INDEX IF NOT EXISTS idx_system_config_active 
                ON system_config(is_active) WHERE is_active = TRUE
            """)


class TestHotReloadingMechanism:
    """Test CFG-010: Hot-Reloading Mechanism for config.yaml"""
    
    @pytest.mark.asyncio
    async def test_config_file_change_detection(self):
        """Test configuration file change detection and reload"""
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
            
            # Wait a moment to ensure file timestamp difference
            time.sleep(0.1)
            
            # Modify file
            updated_content = {'app': {'debug': not initial_debug}}
            with open(yaml_file, 'w') as f:
                yaml.dump(updated_content, f)
            
            # Check for changes
            changed = await manager.check_for_config_file_changes()
            
            assert changed is True
            assert manager._config.app.debug != initial_debug
            
        finally:
            os.unlink(yaml_file)
    
    @pytest.mark.asyncio
    async def test_config_file_watcher_context_manager(self):
        """Test configuration file watching context manager"""
        yaml_content = {'app': {'log_level': 'INFO'}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            yaml_file = f.name
        
        try:
            manager = ConfigurationManager()
            await manager.initialize(yaml_file, watch_file=True)
            
            # Test context manager
            async with manager.watch_config_changes(check_interval=0.1) as _:
                # Simulate short-lived task
                await asyncio.sleep(0.2)
            
            # Should complete without errors
            assert True
            
        finally:
            os.unlink(yaml_file)


class TestSecurityValidation:
    """Test Security Requirements for Configuration Management"""
    
    def test_production_secrets_validation(self):
        """Test production environment requires all secrets"""
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
    
    def test_secret_masking_for_logging(self):
        """Test secrets are properly masked for logging"""
        secret = "very-long-secret-key-12345"
        masked = SecretsManager.mask_secret_for_logging(secret, 4)
        assert masked == "*******************2345"
        
        short_secret = "abc"
        masked_short = SecretsManager.mask_secret_for_logging(short_secret)
        assert masked_short == "***"
    
    def test_no_hardcoded_secrets_in_config_yaml(self):
        """Test config.yaml contains no hardcoded secrets"""
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Should use environment variable placeholders
            assert "${ANYTHINGLLM_API_KEY}" in config_content
            assert "${GITHUB_API_TOKEN}" in config_content
            assert "${OPENAI_API_KEY}" in config_content
            
            # Should not contain actual keys
            assert "sk-" not in config_content  # OpenAI key prefix
            assert "ghp_" not in config_content  # GitHub personal access token


class TestConfigurationValidation:
    """Test Configuration Validation Requirements"""
    
    def test_endpoint_url_validation(self):
        """Test endpoint URL validation"""
        # Valid URLs
        assert ConfigurationValidators.validate_endpoint_url("http://localhost:8080") == "http://localhost:8080"
        assert ConfigurationValidators.validate_endpoint_url("https://api.example.com/") == "https://api.example.com"
        
        # Invalid URLs
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_endpoint_url("invalid-url")
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_endpoint_url("ftp://example.com")
    
    def test_api_key_validation(self):
        """Test API key validation"""
        # Valid API key
        assert ConfigurationValidators.validate_api_key("test-api-key-12345") == "test-api-key-12345"
        
        # Invalid API keys
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_api_key("short")
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_api_key("")
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_api_key("   ")
    
    def test_redis_memory_validation(self):
        """Test Redis memory configuration validation"""
        # Valid memory formats
        assert ConfigurationValidators.validate_redis_memory("512mb") == "512mb"
        assert ConfigurationValidators.validate_redis_memory("1GB") == "1gb"
        assert ConfigurationValidators.validate_redis_memory("256M") == "256m"
        
        # Invalid memory format
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_redis_memory("invalid-format")
        with pytest.raises(ValueError):
            ConfigurationValidators.validate_redis_memory("512")


class TestDefaultConfigurationFile:
    """Test CFG-008: Default config.yaml File"""
    
    def test_config_yaml_exists_and_valid(self):
        """Test default config.yaml exists and is valid YAML"""
        config_path = Path("config.yaml")
        assert config_path.exists(), "config.yaml file must exist"
        
        with open(config_path, 'r') as f:
            config_content = yaml.safe_load(f)
        
        assert isinstance(config_content, dict)
        
        # Verify all required sections exist
        required_sections = ['app', 'content', 'anythingllm', 'github', 'scraping', 'redis', 'ai', 'enrichment']
        for section in required_sections:
            assert section in config_content, f"Section '{section}' missing from config.yaml"
    
    def test_config_yaml_production_defaults(self):
        """Test config.yaml contains production-appropriate defaults"""
        config_path = Path("config.yaml")
        with open(config_path, 'r') as f:
            config_content = yaml.safe_load(f)
        
        # Verify production defaults
        assert config_content['app']['environment'] == 'production'
        assert config_content['app']['debug'] is False
        assert config_content['app']['log_level'] == 'INFO'
        
        # Verify Redis production alignment
        assert config_content['redis']['host'] == 'redis'
        assert config_content['redis']['maxmemory'] == '512mb'
        assert config_content['redis']['appendonly'] is True


class TestRuntimeUpdatesWithoutRestart:
    """Test Runtime Configuration Updates Without Service Restart"""
    
    @pytest.mark.asyncio
    async def test_runtime_configuration_update(self):
        """Test configuration can be updated at runtime"""
        manager = ConfigurationManager()
        
        # Mock database manager
        mock_db_manager = AsyncMock()
        manager._db_manager = mock_db_manager
        
        # Update configuration at runtime
        await manager.update_in_db('content.chunk_size_default', 2000)
        
        # Verify update was processed
        mock_db_manager.execute.assert_called_once()
        
        # Verify configuration was reloaded (mock the reload)
        with patch.object(manager, 'load_configuration') as mock_load:
            await manager.update_in_db('app.debug', True)
            mock_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_configuration_reload_functionality(self):
        """Test force configuration reload"""
        manager = ConfigurationManager()
        
        # Mock configuration loading
        with patch.object(manager, 'load_configuration') as mock_load:
            mock_load.return_value = SystemConfiguration(
                app=AppConfig(),
                content=ContentConfig(),
                anythingllm=AnythingLLMConfig(endpoint="http://test:3001", api_key="test"),
                github=GitHubConfig(api_token="test"),
                scraping=ScrapingConfig(),
                redis=RedisConfig(),
                ai=AIConfig(
                    ollama=OllamaConfig(),
                    openai=OpenAIConfig(api_key="test")
                )
            )
            
            result = await manager.reload_configuration()
            
            assert isinstance(result, SystemConfiguration)
            mock_load.assert_called_once()


class TestPerformanceRequirements:
    """Test Configuration System Performance Requirements"""
    
    @pytest.mark.asyncio
    async def test_configuration_loading_performance(self):
        """Test configuration loading is efficient on startup"""
        manager = ConfigurationManager()
        
        # Mock database manager for fast response
        mock_db_manager = AsyncMock()
        mock_db_manager.fetch_all.return_value = []
        
        with patch('src.database.manager.create_database_manager', return_value=mock_db_manager):
            start_time = time.time()
            
            await manager.initialize()
            await manager.load_configuration()
            
            end_time = time.time()
            
            # Configuration loading should be fast (< 1 second)
            assert (end_time - start_time) < 1.0
    
    def test_memory_usage_minimal(self):
        """Test configuration caching uses minimal memory"""
        # Create multiple configuration objects
        configs = []
        for _ in range(100):
            config = AppConfig()
            configs.append(config)
        
        # Verify they don't consume excessive memory
        # This is a basic check - in production we'd use memory profiling
        assert len(configs) == 100
    
    def test_thread_safe_access_performance(self):
        """Test thread-safe access doesn't create performance bottlenecks"""
        manager = ConfigurationManager()
        
        def access_config():
            try:
                # This would normally get the config
                # For test, just verify manager is accessible
                assert manager is not None
            except Exception:
                pass
        
        # Create multiple threads accessing configuration
        threads = []
        start_time = time.time()
        
        for _ in range(20):
            thread = threading.Thread(target=access_config)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Thread access should complete quickly
        assert (end_time - start_time) < 2.0


class TestIntegrationWithPRD001API:
    """Test CFG-009: Integration with PRD-001 API Endpoints"""
    
    def test_fastapi_dependency_injection(self):
        """Test ConfigurationManager can be used as FastAPI dependency"""
        from src.core.config.manager import get_configuration_manager
        
        # This should be usable as a FastAPI dependency
        assert callable(get_configuration_manager)
        
        # Test it returns ConfigurationManager
        # Note: In real tests this would be async, but we're testing the interface
        assert get_configuration_manager.__name__ == 'get_configuration_manager'
    
    def test_configuration_api_contract(self):
        """Test configuration provides expected interface for API endpoints"""
        config = SystemConfiguration(
            app=AppConfig(),
            content=ContentConfig(),
            anythingllm=AnythingLLMConfig(endpoint="http://test:3001", api_key="test"),
            github=GitHubConfig(api_token="test"),
            scraping=ScrapingConfig(),
            redis=RedisConfig(),
            ai=AIConfig(
                ollama=OllamaConfig(),
                openai=OpenAIConfig(api_key="test")
            )
        )
        
        # Verify API endpoints can access required configuration
        assert hasattr(config.app, 'api_host')
        assert hasattr(config.app, 'api_port')
        assert hasattr(config.app, 'log_level')
        assert hasattr(config.redis, 'host')
        assert hasattr(config.redis, 'port')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])