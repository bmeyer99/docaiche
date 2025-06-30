"""
Test Configuration Management
============================

Tests for configuration manager and deployment integration.
"""

import asyncio
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime

from mcp.config import (
    ConfigurationManager, ConfigSource, ConfigFormat,
    DeploymentConfig, DeploymentTarget, Environment,
    DeploymentBuilder
)


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    @pytest.fixture
    async def config_manager(self):
        """Create configuration manager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigurationManager(
                base_path=tmpdir,
                environment="test",
                auto_reload=False
            )
            await manager.initialize()
            yield manager
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_default_values(self, config_manager):
        """Test default configuration values."""
        # Check defaults are loaded
        assert config_manager.get("server_host") == "0.0.0.0"
        assert config_manager.get("server_port") == 8080
        assert config_manager.get("log_level") == "INFO"
    
    @pytest.mark.asyncio
    async def test_get_set_values(self, config_manager):
        """Test getting and setting configuration values."""
        # Set a value
        await config_manager.set("test_key", "test_value")
        assert config_manager.get("test_key") == "test_value"
        
        # Set nested value
        await config_manager.set("database", {"host": "localhost", "port": 5432})
        assert config_manager.get("database.host") == "localhost"
        assert config_manager.get("database.port") == 5432
    
    @pytest.mark.asyncio
    async def test_config_sources(self, config_manager):
        """Test configuration source tracking."""
        # Set values from different sources
        await config_manager.set("from_file", "value1", ConfigSource.FILE)
        await config_manager.set("from_env", "value2", ConfigSource.ENVIRONMENT)
        await config_manager.set("from_remote", "value3", ConfigSource.REMOTE)
        
        # Check sources are tracked
        assert config_manager._config["from_file"].source == ConfigSource.FILE
        assert config_manager._config["from_env"].source == ConfigSource.ENVIRONMENT
        assert config_manager._config["from_remote"].source == ConfigSource.REMOTE
    
    @pytest.mark.asyncio
    async def test_secret_detection(self, config_manager):
        """Test secret key detection."""
        assert config_manager.is_secret("api_key") is True
        assert config_manager.is_secret("database_password") is True
        assert config_manager.is_secret("jwt_secret") is True
        assert config_manager.is_secret("server_port") is False
    
    @pytest.mark.asyncio
    async def test_validation(self, config_manager):
        """Test configuration validation."""
        # Register validator
        async def port_validator(value):
            return isinstance(value, int) and 1 <= value <= 65535
        
        config_manager.register_validator("custom_port", port_validator)
        
        # Valid value
        await config_manager.set("custom_port", 8080)
        assert config_manager.get("custom_port") == 8080
        
        # Invalid value
        with pytest.raises(Exception):
            await config_manager.set("custom_port", 99999)
    
    @pytest.mark.asyncio
    async def test_change_callbacks(self, config_manager):
        """Test configuration change callbacks."""
        changes = []
        
        async def callback(key, old_value, new_value):
            changes.append((key, old_value, new_value))
        
        config_manager.register_change_callback(callback)
        
        # Trigger change
        await config_manager.set("test_key", "new_value")
        
        # Check callback was called
        assert len(changes) == 1
        assert changes[0][0] == "test_key"
        assert changes[0][2].value == "new_value"
    
    @pytest.mark.asyncio
    async def test_export_config(self, config_manager):
        """Test configuration export."""
        # Set some values
        await config_manager.set("test_key", "test_value")
        await config_manager.set("secret_key", "secret_value")
        
        # Export without secrets
        export = await config_manager.export_config(
            format=ConfigFormat.JSON,
            include_secrets=False
        )
        
        data = json.loads(export)
        assert data["test_key"]["value"] == "test_value"
        assert data["secret_key"]["value"] == "***REDACTED***"
    
    @pytest.mark.asyncio
    async def test_file_loading(self):
        """Test loading configuration from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_file = Path(tmpdir) / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump({
                    "server": {
                        "host": "127.0.0.1",
                        "port": 9000
                    },
                    "custom_setting": "custom_value"
                }, f)
            
            # Load config
            manager = ConfigurationManager(base_path=tmpdir)
            await manager.initialize()
            
            # Check values loaded
            assert manager.get("server.host") == "127.0.0.1"
            assert manager.get("server.port") == 9000
            assert manager.get("custom_setting") == "custom_value"
            
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_environment_variables(self):
        """Test loading from environment variables."""
        import os
        
        # Set environment variables
        os.environ["MCP_TEST_SETTING"] = "env_value"
        os.environ["MCP_TEST_PORT"] = "8888"
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = ConfigurationManager(base_path=tmpdir)
                await manager.initialize()
                
                # Check env vars loaded
                assert manager.get("test_setting") == "env_value"
                assert manager.get("test_port") == "8888"
                
                await manager.close()
        finally:
            # Cleanup
            del os.environ["MCP_TEST_SETTING"]
            del os.environ["MCP_TEST_PORT"]
    
    @pytest.mark.asyncio
    async def test_deployment_validation(self, config_manager):
        """Test deployment configuration validation."""
        # Set required values
        await config_manager.set("database_url", "postgresql://localhost/test")
        await config_manager.set("redis_url", "redis://localhost:6379")
        
        # Validate
        report = await config_manager.validate_deployment_config()
        
        assert report["environment"] == "test"
        assert isinstance(report["errors"], list)
        assert isinstance(report["warnings"], list)


class TestDeploymentConfig:
    """Test deployment configuration."""
    
    def test_deployment_config_defaults(self):
        """Test deployment config default values."""
        config = DeploymentConfig(
            environment=Environment.DEVELOPMENT,
            target=DeploymentTarget.DOCKER
        )
        
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8080
        assert config.ssl_enabled is True
        assert config.log_level == "INFO"
    
    def test_env_var_conversion(self):
        """Test conversion to environment variables."""
        config = DeploymentConfig(
            environment=Environment.PRODUCTION,
            target=DeploymentTarget.KUBERNETES,
            server_port=8000,
            database_url="postgresql://prod/db"
        )
        
        env_vars = config.to_env_vars()
        
        assert env_vars["MCP_ENVIRONMENT"] == "production"
        assert env_vars["MCP_SERVER_PORT"] == "8000"
        assert env_vars["MCP_DATABASE_URL"] == "postgresql://prod/db"
        assert env_vars["MCP_SSL_ENABLED"] == "true"
    
    def test_docker_config_generation(self):
        """Test Docker configuration generation."""
        result = DeploymentBuilder.build_docker_config(Environment.PRODUCTION)
        
        config = result["config"]
        dockerfile = result["dockerfile"]
        
        # Check config
        assert config.environment == Environment.PRODUCTION
        assert config.ssl_enabled is True
        assert config.worker_count == 8
        
        # Check Dockerfile
        assert "FROM python:3.11-slim" in dockerfile
        assert "EXPOSE 8080" in dockerfile
        assert "HEALTHCHECK" in dockerfile
    
    def test_kubernetes_config_generation(self):
        """Test Kubernetes configuration generation."""
        result = DeploymentBuilder.build_kubernetes_config(Environment.STAGING)
        
        config = result["config"]
        deployment = result["deployment"]
        service = result["service"]
        
        # Check deployment
        assert deployment["kind"] == "Deployment"
        assert deployment["spec"]["replicas"] == 1
        
        # Check service
        assert service["kind"] == "Service"
        assert service["spec"]["type"] == "ClusterIP"
    
    def test_docker_compose_generation(self):
        """Test Docker Compose configuration generation."""
        result = DeploymentBuilder.build_docker_compose_config(Environment.DEVELOPMENT)
        
        config = result["config"]
        compose = result["compose"]
        
        # Check services
        assert "mcp-server" in compose["services"]
        assert "postgres" in compose["services"]
        assert "redis" in compose["services"]
        
        # Check dependencies
        assert "postgres" in compose["services"]["mcp-server"]["depends_on"]
        assert "redis" in compose["services"]["mcp-server"]["depends_on"]


class TestConfigurationIntegration:
    """Test configuration integration with server."""
    
    @pytest.mark.asyncio
    async def test_server_config_integration(self):
        """Test configuration manager integration with server config."""
        from mcp.config import MCPServerConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config manager
            manager = ConfigurationManager(
                base_path=tmpdir,
                environment="production"
            )
            await manager.initialize()
            
            # Set production values
            await manager.set("ssl_enabled", True)
            await manager.set("require_authentication", True)
            await manager.set("rate_limit_enabled", True)
            
            # Create server config
            server_config = MCPServerConfig()
            
            # Apply config manager values
            server_config.require_authentication = manager.get(
                "require_authentication",
                server_config.require_authentication
            )
            
            assert server_config.require_authentication is True
            
            await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])