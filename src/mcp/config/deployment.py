"""
Deployment Configuration and Integration
=======================================

Deployment-specific configuration management for different environments
and container orchestration platforms.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DeploymentTarget(Enum):
    """Supported deployment targets."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    DOCKER_COMPOSE = "docker-compose"
    BARE_METAL = "bare-metal"
    CLOUD_RUN = "cloud-run"
    ECS = "ecs"


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DeploymentConfig:
    """Deployment configuration for MCP server."""
    
    # Environment settings
    environment: Environment
    target: DeploymentTarget
    
    # Server configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8080
    worker_count: int = 4
    max_connections: int = 1000
    
    # Security settings
    ssl_enabled: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Database configuration
    database_url: str = "postgresql://localhost/docaiche"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    # Monitoring
    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = True
    tracing_endpoint: Optional[str] = None
    
    # Resource limits
    memory_limit_mb: int = 1024
    cpu_limit: float = 2.0
    
    # Health checks
    health_check_path: str = "/health"
    health_check_interval: int = 30
    health_check_timeout: int = 10
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    
    def to_env_vars(self) -> Dict[str, str]:
        """Convert configuration to environment variables."""
        env_vars = {
            "MCP_ENVIRONMENT": self.environment.value,
            "MCP_SERVER_HOST": self.server_host,
            "MCP_SERVER_PORT": str(self.server_port),
            "MCP_WORKER_COUNT": str(self.worker_count),
            "MCP_MAX_CONNECTIONS": str(self.max_connections),
            "MCP_SSL_ENABLED": str(self.ssl_enabled).lower(),
            "MCP_DATABASE_URL": self.database_url,
            "MCP_REDIS_URL": self.redis_url,
            "MCP_LOG_LEVEL": self.log_level,
            "MCP_LOG_FORMAT": self.log_format,
            "MCP_METRICS_ENABLED": str(self.metrics_enabled).lower(),
            "MCP_METRICS_PORT": str(self.metrics_port),
        }
        
        if self.ssl_cert_path:
            env_vars["MCP_SSL_CERT_PATH"] = self.ssl_cert_path
        if self.ssl_key_path:
            env_vars["MCP_SSL_KEY_PATH"] = self.ssl_key_path
        if self.log_file:
            env_vars["MCP_LOG_FILE"] = self.log_file
        if self.tracing_endpoint:
            env_vars["MCP_TRACING_ENDPOINT"] = self.tracing_endpoint
        
        # Add feature flags
        for flag, enabled in self.feature_flags.items():
            env_vars[f"MCP_FEATURE_{flag.upper()}"] = str(enabled).lower()
        
        return env_vars


class DeploymentBuilder:
    """Builder for creating deployment configurations."""
    
    @staticmethod
    def build_docker_config(environment: Environment) -> Dict[str, Any]:
        """Build Docker deployment configuration."""
        config = DeploymentConfig(
            environment=environment,
            target=DeploymentTarget.DOCKER
        )
        
        # Environment-specific settings
        if environment == Environment.PRODUCTION:
            config.ssl_enabled = True
            config.worker_count = 8
            config.memory_limit_mb = 4096
            config.cpu_limit = 4.0
            config.log_level = "WARNING"
        elif environment == Environment.STAGING:
            config.ssl_enabled = True
            config.worker_count = 4
            config.memory_limit_mb = 2048
            config.cpu_limit = 2.0
            config.log_level = "INFO"
        else:  # Development
            config.ssl_enabled = False
            config.worker_count = 2
            config.memory_limit_mb = 1024
            config.cpu_limit = 1.0
            config.log_level = "DEBUG"
        
        # Generate Dockerfile content
        dockerfile = f"""
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1
{chr(10).join(f'ENV {k}={v}' for k, v in config.to_env_vars().items())}

# Health check
HEALTHCHECK --interval={config.health_check_interval}s \\
    --timeout={config.health_check_timeout}s \\
    --start-period=30s \\
    --retries=3 \\
    CMD curl -f http://localhost:{config.server_port}{config.health_check_path} || exit 1

# Expose ports
EXPOSE {config.server_port}
{f'EXPOSE {config.metrics_port}' if config.metrics_enabled else ''}

# Run server
CMD ["python", "-m", "mcp.server"]
"""
        
        return {
            "config": config,
            "dockerfile": dockerfile.strip()
        }
    
    @staticmethod
    def build_kubernetes_config(environment: Environment) -> Dict[str, Any]:
        """Build Kubernetes deployment configuration."""
        config = DeploymentConfig(
            environment=environment,
            target=DeploymentTarget.KUBERNETES
        )
        
        # Environment-specific settings
        if environment == Environment.PRODUCTION:
            replicas = 3
            config.memory_limit_mb = 4096
            config.cpu_limit = 4.0
        else:
            replicas = 1
            config.memory_limit_mb = 2048
            config.cpu_limit = 2.0
        
        # Generate Kubernetes manifests
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "mcp-server",
                "labels": {
                    "app": "mcp-server",
                    "environment": environment.value
                }
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": "mcp-server"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "mcp-server"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "mcp-server",
                            "image": "mcp-server:latest",
                            "ports": [
                                {
                                    "containerPort": config.server_port,
                                    "name": "http"
                                }
                            ],
                            "env": [
                                {"name": k, "value": v}
                                for k, v in config.to_env_vars().items()
                            ],
                            "resources": {
                                "limits": {
                                    "memory": f"{config.memory_limit_mb}Mi",
                                    "cpu": str(config.cpu_limit)
                                },
                                "requests": {
                                    "memory": f"{config.memory_limit_mb // 2}Mi",
                                    "cpu": str(config.cpu_limit / 2)
                                }
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": config.health_check_path,
                                    "port": "http"
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": config.health_check_interval
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": config.health_check_path,
                                    "port": "http"
                                },
                                "initialDelaySeconds": 10,
                                "periodSeconds": 10
                            }
                        }]
                    }
                }
            }
        }
        
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "mcp-server",
                "labels": {
                    "app": "mcp-server"
                }
            },
            "spec": {
                "selector": {
                    "app": "mcp-server"
                },
                "ports": [
                    {
                        "port": 80,
                        "targetPort": config.server_port,
                        "name": "http"
                    }
                ],
                "type": "LoadBalancer" if environment == Environment.PRODUCTION else "ClusterIP"
            }
        }
        
        return {
            "config": config,
            "deployment": deployment,
            "service": service
        }
    
    @staticmethod
    def build_docker_compose_config(environment: Environment) -> Dict[str, Any]:
        """Build Docker Compose configuration."""
        config = DeploymentConfig(
            environment=environment,
            target=DeploymentTarget.DOCKER_COMPOSE
        )
        
        compose = {
            "version": "3.8",
            "services": {
                "mcp-server": {
                    "build": ".",
                    "ports": [
                        f"{config.server_port}:{config.server_port}"
                    ],
                    "environment": config.to_env_vars(),
                    "depends_on": [
                        "postgres",
                        "redis"
                    ],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": f"curl -f http://localhost:{config.server_port}{config.health_check_path}",
                        "interval": f"{config.health_check_interval}s",
                        "timeout": f"{config.health_check_timeout}s",
                        "retries": 3
                    }
                },
                "postgres": {
                    "image": "postgres:15-alpine",
                    "environment": {
                        "POSTGRES_DB": "docaiche",
                        "POSTGRES_USER": "docaiche",
                        "POSTGRES_PASSWORD": "changeme"
                    },
                    "volumes": [
                        "postgres_data:/var/lib/postgresql/data"
                    ],
                    "restart": "unless-stopped"
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "restart": "unless-stopped",
                    "volumes": [
                        "redis_data:/data"
                    ]
                }
            },
            "volumes": {
                "postgres_data": {},
                "redis_data": {}
            }
        }
        
        # Add monitoring in production
        if environment == Environment.PRODUCTION:
            compose["services"]["prometheus"] = {
                "image": "prom/prometheus:latest",
                "ports": ["9090:9090"],
                "volumes": [
                    "./prometheus.yml:/etc/prometheus/prometheus.yml"
                ],
                "restart": "unless-stopped"
            }
            
            compose["services"]["grafana"] = {
                "image": "grafana/grafana:latest",
                "ports": ["3000:3000"],
                "environment": {
                    "GF_SECURITY_ADMIN_PASSWORD": "changeme"
                },
                "restart": "unless-stopped"
            }
        
        return {
            "config": config,
            "compose": compose
        }


def generate_deployment_files(
    environment: Environment,
    target: DeploymentTarget,
    output_dir: str = "deployment"
) -> None:
    """
    Generate deployment configuration files.
    
    Args:
        environment: Target environment
        target: Deployment target
        output_dir: Output directory for files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if target == DeploymentTarget.DOCKER:
        config = DeploymentBuilder.build_docker_config(environment)
        
        # Write Dockerfile
        with open(output_path / "Dockerfile", "w") as f:
            f.write(config["dockerfile"])
        
        # Write .dockerignore
        with open(output_path / ".dockerignore", "w") as f:
            f.write("""
__pycache__
*.pyc
.env
.git
.pytest_cache
logs/
*.log
""")
        
    elif target == DeploymentTarget.KUBERNETES:
        config = DeploymentBuilder.build_kubernetes_config(environment)
        
        # Write deployment manifest
        with open(output_path / "deployment.yaml", "w") as f:
            import yaml
            yaml.dump(config["deployment"], f)
        
        # Write service manifest
        with open(output_path / "service.yaml", "w") as f:
            yaml.dump(config["service"], f)
        
    elif target == DeploymentTarget.DOCKER_COMPOSE:
        config = DeploymentBuilder.build_docker_compose_config(environment)
        
        # Write docker-compose.yml
        with open(output_path / "docker-compose.yml", "w") as f:
            import yaml
            yaml.dump(config["compose"], f)
        
        # Write .env file
        with open(output_path / ".env", "w") as f:
            for k, v in config["config"].to_env_vars().items():
                f.write(f"{k}={v}\n")
    
    logger.info(f"Generated {target.value} deployment files for {environment.value} in {output_path}")