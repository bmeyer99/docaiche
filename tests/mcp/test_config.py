"""
Unit tests for Configuration Management
=======================================

Tests for configuration loading, validation, and deployment integration.
"""

import pytest
import os
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.mcp.config.config_manager import (
    ConfigurationManager,
    ConfigValidator,
    ConfigSource,
    ValidationError
)
from src.mcp.config.deployment import (
    DeploymentConfig,
    DeploymentBuilder,
    DeploymentTarget,
    Environment,
    generate_deployment_files
)


class TestConfigValidator:
    """Test configuration validation."""
    
    @pytest.fixture
    def validator(self):
        return ConfigValidator()
    
    def test_validate_valid_config(self, validator):
        """Test validation of valid configuration."""
        config = {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "workers": 4
            },
            "security": {
                "enable_auth": True,
                "jwt_secret": "secret123"
            },
            "database": {
                "url": "postgresql://localhost/docaiche"
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) == 0
    
    def test_validate_missing_required(self, validator):
        """Test validation with missing required fields."""
        config = {
            "server": {
                "host": "0.0.0.0"
                # Missing port
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) > 0
        assert any("port" in error.lower() for error in errors)
    
    def test_validate_invalid_types(self, validator):
        """Test validation with invalid types."""
        config = {
            "server": {
                "host": "0.0.0.0",
                "port": "8080",  # Should be int
                "workers": 4
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) > 0
        assert any("type" in error.lower() for error in errors)
    
    def test_validate_invalid_values(self, validator):
        """Test validation with invalid values."""
        config = {
            "server": {
                "host": "0.0.0.0",
                "port": -1,  # Invalid port
                "workers": 0  # Invalid worker count
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) > 0
        assert any("port" in error.lower() for error in errors)
        assert any("workers" in error.lower() for error in errors)
    
    def test_validate_security_config(self, validator):
        """Test security configuration validation."""
        # Missing JWT secret when auth enabled
        config = {
            "security": {
                "enable_auth": True
                # Missing jwt_secret
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) > 0
        assert any("jwt_secret" in error.lower() for error in errors)
    
    def test_validate_resource_limits(self, validator):
        """Test resource limit validation."""
        config = {
            "limits": {
                "max_request_size": 100 * 1024 * 1024,  # 100MB
                "max_connections": 10000,
                "request_timeout": 300
            }
        }
        
        errors = validator.validate(config)
        assert len(errors) == 0
        
        # Test invalid limits
        config["limits"]["max_request_size"] = -1
        errors = validator.validate(config)
        assert len(errors) > 0


class TestConfigurationManager:
    """Test configuration management."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        return ConfigurationManager(
            config_dir=str(temp_config_dir),
            environment="test"
        )
    
    @pytest.mark.asyncio
    async def test_load_default_config(self, config_manager):
        """Test loading default configuration."""
        await config_manager.initialize()
        
        config = config_manager.get_config()
        assert config is not None
        assert "server" in config
        assert config["server"]["port"] == 8080  # Default
    
    @pytest.mark.asyncio
    async def test_load_file_config(self, config_manager, temp_config_dir):
        """Test loading configuration from file."""
        # Create config file
        config_file = temp_config_dir / "config.yaml"
        config_data = {
            "server": {
                "host": "localhost",
                "port": 9090
            }
        }
        
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        
        await config_manager.initialize()
        
        config = config_manager.get_config()
        assert config["server"]["port"] == 9090  # Overridden
    
    @pytest.mark.asyncio
    async def test_environment_specific_config(self, config_manager, temp_config_dir):
        """Test loading environment-specific configuration."""
        # Create base config
        base_config = temp_config_dir / "config.yaml"
        with open(base_config, "w") as f:
            yaml.dump({"server": {"port": 8080}}, f)
        
        # Create test environment config
        test_config = temp_config_dir / "config.test.yaml"
        with open(test_config, "w") as f:
            yaml.dump({"server": {"port": 8888}}, f)
        
        await config_manager.initialize()
        
        config = config_manager.get_config()
        assert config["server"]["port"] == 8888  # Test environment override
    
    @pytest.mark.asyncio
    async def test_environment_variable_override(self, config_manager):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            "MCP_SERVER_PORT": "7777",
            "MCP_DATABASE_URL": "postgresql://custom/db"
        }):
            await config_manager.initialize()
            
            config = config_manager.get_config()
            assert config["server"]["port"] == 7777
            assert config["database"]["url"] == "postgresql://custom/db"
    
    @pytest.mark.asyncio
    async def test_config_validation(self, config_manager, temp_config_dir):
        """Test configuration validation during load."""
        # Create invalid config
        config_file = temp_config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"server": {"port": "invalid"}}, f)
        
        with pytest.raises(ValidationError):
            await config_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_config_reload(self, config_manager, temp_config_dir):
        """Test configuration reloading."""
        await config_manager.initialize()
        
        # Modify config file
        config_file = temp_config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"server": {"port": 9999}}, f)
        
        # Reload
        await config_manager.reload()
        
        config = config_manager.get_config()
        assert config["server"]["port"] == 9999
    
    @pytest.mark.asyncio
    async def test_config_change_notifications(self, config_manager):
        """Test configuration change notifications."""
        notified_configs = []
        
        def on_change(old_config, new_config):
            notified_configs.append((old_config, new_config))
        
        config_manager.on_config_change(on_change)
        
        await config_manager.initialize()
        await config_manager.reload()
        
        assert len(notified_configs) > 0
    
    def test_get_nested_config(self, config_manager):
        """Test getting nested configuration values."""
        config_manager._config = {
            "server": {
                "security": {
                    "tls": {
                        "enabled": True
                    }
                }
            }
        }
        
        assert config_manager.get("server.security.tls.enabled") is True
        assert config_manager.get("server.security.tls.missing", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_config_sources_priority(self, config_manager, temp_config_dir):
        """Test configuration source priority."""
        # Create configs at different levels
        default_config = {"server": {"port": 8080, "host": "0.0.0.0"}}
        file_config = {"server": {"port": 9090}}
        
        config_file = temp_config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(file_config, f)
        
        with patch.dict(os.environ, {"MCP_SERVER_HOST": "localhost"}):
            await config_manager.initialize()
            
            config = config_manager.get_config()
            # Priority: env > file > default
            assert config["server"]["port"] == 9090  # From file
            assert config["server"]["host"] == "localhost"  # From env


class TestDeploymentConfig:
    """Test deployment configuration."""
    
    def test_deployment_config_creation(self):
        """Test creating deployment configuration."""
        config = DeploymentConfig(
            environment=Environment.PRODUCTION,
            target=DeploymentTarget.DOCKER,
            server_port=8080,
            worker_count=8
        )
        
        assert config.environment == Environment.PRODUCTION
        assert config.server_port == 8080
        assert config.ssl_enabled is True  # Default for production
    
    def test_deployment_config_to_env_vars(self):
        """Test converting deployment config to environment variables."""
        config = DeploymentConfig(
            environment=Environment.STAGING,
            target=DeploymentTarget.KUBERNETES,
            database_url="postgresql://db/staging"
        )
        
        env_vars = config.to_env_vars()
        
        assert env_vars["MCP_ENVIRONMENT"] == "staging"
        assert env_vars["MCP_DATABASE_URL"] == "postgresql://db/staging"
        assert "MCP_SERVER_PORT" in env_vars
    
    def test_deployment_config_feature_flags(self):
        """Test feature flags in deployment config."""
        config = DeploymentConfig(
            environment=Environment.DEVELOPMENT,
            target=DeploymentTarget.DOCKER,
            feature_flags={
                "new_search": True,
                "beta_ui": False
            }
        )
        
        env_vars = config.to_env_vars()
        
        assert env_vars["MCP_FEATURE_NEW_SEARCH"] == "true"
        assert env_vars["MCP_FEATURE_BETA_UI"] == "false"


class TestDeploymentBuilder:
    """Test deployment configuration builder."""
    
    def test_build_docker_config(self):
        """Test building Docker deployment configuration."""
        result = DeploymentBuilder.build_docker_config(Environment.PRODUCTION)
        
        assert "config" in result
        assert "dockerfile" in result
        
        config = result["config"]
        assert config.environment == Environment.PRODUCTION
        assert config.worker_count == 8  # Production setting
        
        dockerfile = result["dockerfile"]
        assert "FROM python:3.11-slim" in dockerfile
        assert "HEALTHCHECK" in dockerfile
        assert str(config.server_port) in dockerfile
    
    def test_build_kubernetes_config(self):
        """Test building Kubernetes deployment configuration."""
        result = DeploymentBuilder.build_kubernetes_config(Environment.STAGING)
        
        assert "config" in result
        assert "deployment" in result
        assert "service" in result
        
        deployment = result["deployment"]
        assert deployment["kind"] == "Deployment"
        assert deployment["spec"]["replicas"] == 1  # Staging setting
        
        service = result["service"]
        assert service["kind"] == "Service"
        assert service["spec"]["type"] == "ClusterIP"  # Not production
    
    def test_build_docker_compose_config(self):
        """Test building Docker Compose configuration."""
        result = DeploymentBuilder.build_docker_compose_config(Environment.DEVELOPMENT)
        
        assert "config" in result
        assert "compose" in result
        
        compose = result["compose"]
        assert "mcp-server" in compose["services"]
        assert "postgres" in compose["services"]
        assert "redis" in compose["services"]
        
        # Development shouldn't have monitoring
        assert "prometheus" not in compose["services"]
    
    def test_production_compose_includes_monitoring(self):
        """Test that production compose includes monitoring."""
        result = DeploymentBuilder.build_docker_compose_config(Environment.PRODUCTION)
        
        compose = result["compose"]
        assert "prometheus" in compose["services"]
        assert "grafana" in compose["services"]


class TestDeploymentFileGeneration:
    """Test deployment file generation."""
    
    @pytest.fixture
    def temp_deploy_dir(self):
        """Create temporary deployment directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_generate_docker_files(self, temp_deploy_dir):
        """Test generating Docker deployment files."""
        generate_deployment_files(
            environment=Environment.PRODUCTION,
            target=DeploymentTarget.DOCKER,
            output_dir=str(temp_deploy_dir)
        )
        
        # Check files were created
        assert (temp_deploy_dir / "Dockerfile").exists()
        assert (temp_deploy_dir / ".dockerignore").exists()
        
        # Verify Dockerfile content
        with open(temp_deploy_dir / "Dockerfile") as f:
            content = f.read()
            assert "FROM python:3.11-slim" in content
            assert "HEALTHCHECK" in content
    
    @patch("src.mcp.config.deployment.yaml")
    def test_generate_kubernetes_files(self, mock_yaml, temp_deploy_dir):
        """Test generating Kubernetes deployment files."""
        mock_yaml.dump = Mock()
        
        generate_deployment_files(
            environment=Environment.STAGING,
            target=DeploymentTarget.KUBERNETES,
            output_dir=str(temp_deploy_dir)
        )
        
        # Verify YAML dump was called for both files
        assert mock_yaml.dump.call_count == 2
    
    def test_generate_compose_files(self, temp_deploy_dir):
        """Test generating Docker Compose files."""
        with patch("src.mcp.config.deployment.yaml.dump") as mock_dump:
            generate_deployment_files(
                environment=Environment.DEVELOPMENT,
                target=DeploymentTarget.DOCKER_COMPOSE,
                output_dir=str(temp_deploy_dir)
            )
            
            # Verify docker-compose.yml was created
            mock_dump.assert_called()
            
        # Check .env file
        assert (temp_deploy_dir / ".env").exists()
        with open(temp_deploy_dir / ".env") as f:
            content = f.read()
            assert "MCP_ENVIRONMENT=development" in content