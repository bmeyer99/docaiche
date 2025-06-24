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
- AI/LLM configuration interface provided by [Configuration Web UI](PRD-012_configuration_web_ui.md) with dynamic provider management and endpoint testing.

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
    """Ollama LLM provider configuration - OPTIONAL, user-configurable"""
    enabled: bool = Field(False, description="Enable Ollama provider")
    endpoint: Optional[str] = Field(None, description="Ollama API endpoint (e.g., http://localhost:11434)")
    model: Optional[str] = Field(None, description="Default model to use when enabled")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(60, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60, timeout_seconds=30)
    )

class OpenAIConfig(BaseModel):
    """OpenAI-compatible LLM provider configuration - OPTIONAL, user-configurable"""
    enabled: bool = Field(False, description="Enable OpenAI-compatible provider")
    api_key: Optional[str] = Field(None, description="API key (required when enabled)")
    base_url: Optional[str] = Field(None, description="Custom API endpoint (defaults to OpenAI if not set)")
    model: Optional[str] = Field(None, description="Default model to use when enabled")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(30, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300, timeout_seconds=30)
    )

class AIConfig(BaseModel):
    """AI provider configuration with optional providers and user-driven selection"""
    primary_provider: Optional[Literal["ollama", "openai"]] = Field(None, description="Primary LLM provider (set when user configures)")
    fallback_provider: Optional[Literal["ollama", "openai"]] = Field(None, description="Fallback LLM provider")
    enable_failover: bool = Field(True, description="Enable automatic failover when both providers configured")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig, description="Ollama provider configuration")
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig, description="OpenAI-compatible provider configuration")
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

**Note:** In containerized environments, Redis configuration parameters (`maxmemory`, `maxmemory_policy`, `appendonly`) must align with the Redis service configuration in [`docker-compose.yml`](PRD-013_operations_and_deployment.md:104). The application configuration validates against but does not override Docker-level Redis settings.

**Password Handling:** For production deployments, set `REDIS_PASSWORD` in the `.env` file and ensure the Redis container is configured with the same password using Redis AUTH command or configuration file.

## LLM Provider Configuration Architecture

**CRITICAL ARCHITECTURAL PRINCIPLE:** LLM providers are optional, user-configurable components, NOT required system dependencies.

### Provider Activation Model
- **System Startup**: No LLM providers required for basic operation
- **User Configuration**: Providers activated only when user configures them
- **Runtime Validation**: API keys and endpoints validated only when provider is enabled
- **Graceful Degradation**: System functions without LLM providers configured

### Environment Variable Mapping for LLM Providers

| Environment Variable | Config Field | Required | Description |
|---------------------|--------------|----------|-------------|
| `OLLAMA_ENABLED` | `ai.ollama.enabled` | No | Enable Ollama provider (default: false) |
| `OLLAMA_ENDPOINT` | `ai.ollama.endpoint` | When enabled | Ollama API endpoint |
| `OLLAMA_MODEL` | `ai.ollama.model` | When enabled | Default Ollama model |
| `OPENAI_ENABLED` | `ai.openai.enabled` | No | Enable OpenAI provider (default: false) |
| `OPENAI_API_KEY` | `ai.openai.api_key` | When enabled | API key for OpenAI-compatible endpoint |
| `OPENAI_BASE_URL` | `ai.openai.base_url` | No | Custom API endpoint (defaults to OpenAI) |
| `OPENAI_MODEL` | `ai.openai.model` | When enabled | Default model name |

### Configuration Validation Rules

```python
def validate_ai_config(ai_config: AIConfig) -> None:
    """Validate AI configuration based on enabled providers"""
    
    # Validate Ollama when enabled
    if ai_config.ollama.enabled:
        if not ai_config.ollama.endpoint:
            raise ValueError("Ollama endpoint required when Ollama is enabled")
        if not ai_config.ollama.model:
            raise ValueError("Ollama model required when Ollama is enabled")
    
    # Validate OpenAI when enabled
    if ai_config.openai.enabled:
        if not ai_config.openai.api_key:
            raise ValueError("OpenAI API key required when OpenAI is enabled")
        if not ai_config.openai.model:
            raise ValueError("OpenAI model required when OpenAI is enabled")
    
    # Validate primary provider selection
    if ai_config.primary_provider:
        provider_config = getattr(ai_config, ai_config.primary_provider)
        if not provider_config.enabled:
            raise ValueError(f"Primary provider {ai_config.primary_provider} must be enabled")
    
    # No validation required when no providers are enabled - system should work
```

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
| CFG-012 | Implement optional LLM provider validation (only when enabled) |
| CFG-013 | Add user configuration UI for LLM provider setup |

## Integration Contracts
- Reads from environment, YAML file, and database.
- Provides validated SystemConfiguration Pydantic object.
- **MUST NOT** fail to start if LLM provider configuration is missing.
- **MUST** validate LLM provider configuration only when provider is enabled.
- **Redis Configuration Validation:** Validates RedisConfig parameters against [`docker-compose.yml`](PRD-013_operations_and_deployment.md:97-105) Redis service configuration to ensure compatibility.
- **Production Password Handling:** For production deployments, RedisConfig validates that password authentication is properly configured when Redis service requires AUTH.

## Summary Tables

### Configuration Models

| Model Name           | Description                        | Used By                  |
|----------------------|------------------------------------|--------------------------|
| AppConfig            | App-level settings                 | All components           |
| AnythingLLMConfig    | AnythingLLM client config          | PRD-004                  |
| RedisConfig          | Redis cache config                 | PRD-002, PRD-005, etc.   |
| GitHubConfig         | GitHub API config                  | PRD-006                  |
| OllamaConfig         | Ollama LLM config (optional)       | PRD-005                  |
| OpenAIConfig         | OpenAI LLM config (optional)       | PRD-005                  |
| AIConfig             | AI provider config                 | PRD-005                  |
| ScrapingConfig       | Web scraping config                | PRD-007                  |
| ContentConfig        | Content processing config          | PRD-008                  |
| SystemConfiguration  | Top-level config object            | All components           |

### Implementation Tasks Table
(see Implementation Tasks above)

---