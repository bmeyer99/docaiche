# PRD-003: Configuration Management System

## Overview
Specifies the system's configuration management, including the hierarchical structure of all configuration parameters, validation rules, and loading mechanisms. Provides configuration data to all components.

## Technical Boundaries
- Reads from environment variables, config.yaml, and the system_config table.
- Exposes a singleton configuration object.
- Supports runtime updates without service restart.

## Success Criteria
- Loads a valid, fully populated configuration object on startup.
- Correctly layers configurations from all sources.
- Runtime updates are reflected immediately.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-002: Database & Caching Layer | Stores and retrieves config overrides |
| PRD-001: HTTP API Foundation | API endpoints for config management |
| PRD-013: Operations & Deployment | Loads config for deployment |

## Cross-References
- Uses `DatabaseManager` from PRD-002 for DB overrides.
- Provides config to all major components (PRD-004, PRD-005, PRD-006, etc.).
- Exposes endpoints for config management in PRD-001.

## Configuration Schema

```python
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    version: str = "1.0.0"
    environment: Literal["development", "production", "testing"] = "production"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: str = "/app/data"
    api_host: str = "0.0.0.0"
    api_port: int = Field(8080, ge=1024, le=65535)
    web_port: int = Field(8081, ge=1024, le=65535)
    workers: int = Field(4, ge=1, le=16)

class ContentConfig(BaseModel):
    """Content processing configuration with performance limits"""
    chunk_size_default: int = Field(1000, description="Default chunk size in characters")
    chunk_size_max: int = Field(4000, description="Maximum chunk size in characters")
    chunk_overlap: int = Field(100, description="Character overlap between chunks")
    quality_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum quality score")
    min_content_length: int = Field(50, description="Minimum content length to process")
    max_content_length: int = Field(1000000, description="Maximum content length to process")

class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for API clients"""
    failure_threshold: int = Field(3, description="Failures before opening circuit")
    recovery_timeout: int = Field(60, description="Seconds before attempting recovery")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")

class AnythingLLMConfig(BaseModel):
    endpoint: str = Field(..., description="AnythingLLM API endpoint")
    api_key: str = Field(..., description="API key for authentication")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60, timeout_seconds=30)
    )

class GitHubConfig(BaseModel):
    api_token: str = Field(..., description="GitHub API token")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300, timeout_seconds=30)
    )

class ScrapingConfig(BaseModel):
    user_agent: str = Field("DocaicheBot/1.0", description="User agent for web requests")
    rate_limit_delay: float = Field(1.0, description="Delay between requests in seconds")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120, timeout_seconds=15)
    )

class RedisConfig(BaseModel):
    host: str = Field("redis", description="Redis host")
    port: int = Field(6379, description="Redis port")
    password: Optional[str] = Field(None, description="Redis password (recommended for production)")
    db: int = Field(0, description="Redis database number")
    
    # Connection pool settings
    max_connections: int = Field(20, ge=1, description="Maximum connections in pool")
    connection_timeout: int = Field(5, ge=1, description="Connection timeout in seconds")
    socket_timeout: int = Field(5, ge=1, description="Socket operation timeout in seconds")
    
    # Memory and persistence settings (align with docker-compose)
    maxmemory: str = Field("512mb", description="Maximum memory usage")
    maxmemory_policy: str = Field("allkeys-lru", description="Memory eviction policy")
    appendonly: bool = Field(True, description="Enable append-only file persistence")
    
    # Security settings
    ssl: bool = Field(False, description="Enable SSL/TLS encryption")
    ssl_cert_reqs: Optional[str] = Field(None, description="SSL certificate requirements")

class OllamaConfig(BaseModel):
    """Ollama LLM provider configuration"""
    endpoint: str = Field("http://localhost:11434", description="Ollama API endpoint")
    model: str = Field("llama2", description="Default model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(60, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60, timeout_seconds=30)
    )

class OpenAIConfig(BaseModel):
    """OpenAI LLM provider configuration"""
    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field("gpt-3.5-turbo", description="Default model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(30, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300, timeout_seconds=30)
    )

class AIConfig(BaseModel):
    """AI provider configuration with failover support"""
    primary_provider: Literal["ollama", "openai"] = Field("ollama", description="Primary LLM provider")
    fallback_provider: Optional[Literal["ollama", "openai"]] = Field("openai", description="Fallback LLM provider")
    enable_failover: bool = Field(True, description="Enable automatic failover")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig
    cache_ttl_seconds: int = Field(3600, ge=0, description="Cache TTL for LLM responses")

class SystemConfiguration(BaseModel):
    """Top-level configuration object combining all config sections"""
    app: AppConfig
    content: ContentConfig
    anythingllm: AnythingLLMConfig
    github: GitHubConfig
    scraping: ScrapingConfig
    redis: RedisConfig
    ai: AIConfig
```

## Redis Environment Variable Mapping

The following environment variables map to RedisConfig fields for containerized deployments:

| Environment Variable | RedisConfig Field | Default Value | Description |
|---------------------|-------------------|---------------|-------------|
| `REDIS_HOST` | `host` | `"redis"` | Redis container hostname |
| `REDIS_PORT` | `port` | `6379` | Redis service port |
| `REDIS_PASSWORD` | `password` | `None` | Redis authentication password |
| `REDIS_DB` | `db` | `0` | Redis database number |
| `REDIS_MAX_CONNECTIONS` | `max_connections` | `20` | Connection pool size |
| `REDIS_CONNECTION_TIMEOUT` | `connection_timeout` | `5` | Connection timeout (seconds) |
| `REDIS_SOCKET_TIMEOUT` | `socket_timeout` | `5` | Socket operation timeout (seconds) |
| `REDIS_MAXMEMORY` | `maxmemory` | `"512mb"` | Maximum memory usage |
| `REDIS_MAXMEMORY_POLICY` | `maxmemory_policy` | `"allkeys-lru"` | Memory eviction policy |
| `REDIS_APPENDONLY` | `appendonly` | `true` | Enable append-only persistence |
| `REDIS_SSL` | `ssl` | `false` | Enable SSL/TLS encryption |
| `REDIS_SSL_CERT_REQS` | `ssl_cert_reqs` | `None` | SSL certificate requirements |

**Note:** In containerized environments, Redis configuration parameters (`maxmemory`, `maxmemory_policy`, `appendonly`) must align with the Redis service configuration in [`docker-compose.yml`](PRDs/PRD-013_operations_and_deployment.md:104). The application configuration validates against but does not override Docker-level Redis settings.

**Password Handling:** For production deployments, set `REDIS_PASSWORD` in the `.env` file and ensure the Redis container is configured with the same password using Redis AUTH command or configuration file.

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| CFG-001 | Implement all Pydantic models for configuration schema |
| CFG-002 | Implement ConfigurationManager class |
| CFG-003 | Implement load_configuration with correct priority order |
| CFG-004 | Parse environment variables with nested keys |
| CFG-005 | Implement update_in_db and get_from_db methods |
| CFG-006 | Provide ConfigurationManager as singleton dependency |
| CFG-007 | Write unit tests for loading priority |
| CFG-008 | Create default config.yaml file |
| CFG-009 | Implement /api/v1/config POST and GET endpoints |
| CFG-010 | Implement hot-reloading mechanism for config.yaml |
| CFG-011 | Implement Redis configuration validation against docker-compose.yml settings |

## Integration Contracts
- Reads from environment, YAML file, and database.
- Provides validated SystemConfiguration Pydantic object.
- Fails to start if config validation fails.
- **Redis Configuration Validation:** Validates RedisConfig parameters against [`docker-compose.yml`](PRDs/PRD-013_operations_and_deployment.md:97-105) Redis service configuration to ensure compatibility.
- **Production Password Handling:** For production deployments, RedisConfig validates that password authentication is properly configured when Redis service requires AUTH.

## Summary Tables

### Configuration Models

| Model Name           | Description                        | Used By                  |
|----------------------|------------------------------------|--------------------------|
| AppConfig            | App-level settings                 | All components           |
| AnythingLLMConfig    | AnythingLLM client config          | PRD-004                  |
| RedisConfig          | Redis cache config                 | PRD-002, PRD-005, etc.   |
| GitHubConfig         | GitHub API config                  | PRD-006                  |
| OllamaConfig         | Ollama LLM config                  | PRD-005                  |
| OpenAIConfig         | OpenAI LLM config                  | PRD-005                  |
| AIConfig             | AI provider config                 | PRD-005                  |
| ScrapingConfig       | Web scraping config                | PRD-007                  |
| ContentConfig        | Content processing config          | PRD-008                  |
| SystemConfiguration  | Top-level config object            | All components           |

### Implementation Tasks Table
(see Implementation Tasks above)

---