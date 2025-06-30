# Task: CFG-001 - Implement All Pydantic Configuration Models

**PRD Reference**: [PRD-003: Configuration Management System](../PRDs/PRD-003_Config_Mgmt_System.md#configuration-schema)

## Overview
Implement all Pydantic configuration models as defined in PRD-003, establishing the complete hierarchical configuration structure for the AI Documentation Cache System.

## Detailed Requirements

### 1. Base Configuration Models

#### AppConfig
```python
from typing import Literal
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
```

#### CircuitBreakerConfig
```python
class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for API clients"""
    failure_threshold: int = Field(3, description="Failures before opening circuit")
    recovery_timeout: int = Field(60, description="Seconds before attempting recovery")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
```

### 2. Content Processing Configuration

#### ContentConfig
```python
class ContentConfig(BaseModel):
    """Content processing configuration with performance limits"""
    chunk_size_default: int = Field(1000, description="Default chunk size in characters")
    chunk_size_max: int = Field(4000, description="Maximum chunk size in characters")
    chunk_overlap: int = Field(100, description="Character overlap between chunks")
    quality_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum quality score")
    min_content_length: int = Field(50, description="Minimum content length to process")
    max_content_length: int = Field(1000000, description="Maximum content length to process")
```

### 3. External Service Configurations

#### AnythingLLMConfig
```python
class AnythingLLMConfig(BaseModel):
    endpoint: str = Field(..., description="AnythingLLM API endpoint")
    api_key: str = Field(..., description="API key for authentication")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60, timeout_seconds=30)
    )
```

#### GitHubConfig
```python
class GitHubConfig(BaseModel):
    api_token: str = Field(..., description="GitHub API token")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300, timeout_seconds=30)
    )
```

#### ScrapingConfig
```python
class ScrapingConfig(BaseModel):
    user_agent: str = Field("DocaicheBot/1.0", description="User agent for web requests")
    rate_limit_delay: float = Field(1.0, description="Delay between requests in seconds")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120, timeout_seconds=15)
    )
```

### 4. Database and Caching Configuration

#### RedisConfig
```python
from typing import Optional

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
```

### 5. AI Provider Configurations

#### OllamaConfig
```python
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
```

#### OpenAIConfig
```python
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
```

#### AIConfig
```python
class AIConfig(BaseModel):
    """AI provider configuration with failover support"""
    primary_provider: Literal["ollama", "openai"] = Field("ollama", description="Primary LLM provider")
    fallback_provider: Optional[Literal["ollama", "openai"]] = Field("openai", description="Fallback LLM provider")
    enable_failover: bool = Field(True, description="Enable automatic failover")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig
    cache_ttl_seconds: int = Field(3600, ge=0, description="Cache TTL for LLM responses")
```

### 6. Top-Level Configuration

#### SystemConfiguration
```python
class SystemConfiguration(BaseModel):
    """Top-level configuration object combining all config sections"""
    app: AppConfig
    content: ContentConfig
    anythingllm: AnythingLLMConfig
    github: GitHubConfig
    scraping: ScrapingConfig
    redis: RedisConfig
    ai: AIConfig
    
    class Config:
        # Allow population by field name or alias
        allow_population_by_field_name = True
        # Validate assignment
        validate_assignment = True
        # Use enum values in schema
        use_enum_values = True
```

## Implementation Details

### File Structure
```
src/core/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── models.py          # All configuration Pydantic models
│   ├── validation.py      # Custom validators
│   └── defaults.py        # Default configuration values
```

### Custom Validators

#### File: `src/core/config/validation.py`
```python
from pydantic import validator
from typing import Any
import re

class ConfigurationValidators:
    """Custom validators for configuration models"""
    
    @staticmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URLs"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must start with http:// or https://')
        return v.rstrip('/')
    
    @staticmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v or len(v.strip()) < 8:
            raise ValueError('API key must be at least 8 characters')
        return v.strip()
    
    @staticmethod
    def validate_user_agent(cls, v: str) -> str:
        """Validate user agent string"""
        if not re.match(r'^[a-zA-Z0-9\-_/\.\s]+$', v):
            raise ValueError('Invalid user agent format')
        return v
    
    @staticmethod
    def validate_redis_memory(cls, v: str) -> str:
        """Validate Redis memory configuration"""
        if not re.match(r'^\d+[kmgKMG]?[bB]?$', v):
            raise ValueError('Invalid memory format. Use format like "512mb", "1gb", etc.')
        return v.lower()

# Apply validators to models
AnythingLLMConfig.add_validator('endpoint', ConfigurationValidators.validate_endpoint_url)
AnythingLLMConfig.add_validator('api_key', ConfigurationValidators.validate_api_key)
OllamaConfig.add_validator('endpoint', ConfigurationValidators.validate_endpoint_url)
OpenAIConfig.add_validator('api_key', ConfigurationValidators.validate_api_key)
ScrapingConfig.add_validator('user_agent', ConfigurationValidators.validate_user_agent)
RedisConfig.add_validator('maxmemory', ConfigurationValidators.validate_redis_memory)
```

### Environment Variable Mapping

#### File: `src/core/config/defaults.py`
```python
import os
from typing import Dict, Any

def get_environment_overrides() -> Dict[str, Any]:
    """
    Map environment variables to configuration fields.
    Follows the naming convention: COMPONENT_FIELD_NAME
    """
    env_mappings = {
        # App configuration
        "app.environment": os.getenv("APP_ENVIRONMENT", "production"),
        "app.debug": os.getenv("APP_DEBUG", "false").lower() == "true",
        "app.log_level": os.getenv("APP_LOG_LEVEL", "INFO"),
        "app.api_port": int(os.getenv("APP_API_PORT", "8080")),
        "app.web_port": int(os.getenv("APP_WEB_PORT", "8081")),
        "app.workers": int(os.getenv("APP_WORKERS", "4")),
        
        # Redis configuration
        "redis.host": os.getenv("REDIS_HOST", "redis"),
        "redis.port": int(os.getenv("REDIS_PORT", "6379")),
        "redis.password": os.getenv("REDIS_PASSWORD"),
        "redis.db": int(os.getenv("REDIS_DB", "0")),
        "redis.max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        "redis.maxmemory": os.getenv("REDIS_MAXMEMORY", "512mb"),
        "redis.ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
        
        # AnythingLLM configuration
        "anythingllm.endpoint": os.getenv("ANYTHINGLLM_ENDPOINT", "http://anythingllm:3001"),
        "anythingllm.api_key": os.getenv("ANYTHINGLLM_API_KEY"),
        
        # GitHub configuration
        "github.api_token": os.getenv("GITHUB_API_TOKEN"),
        
        # AI configuration
        "ai.primary_provider": os.getenv("AI_PRIMARY_PROVIDER", "ollama"),
        "ai.enable_failover": os.getenv("AI_ENABLE_FAILOVER", "true").lower() == "true",
        
        # Ollama configuration
        "ai.ollama.endpoint": os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434"),
        "ai.ollama.model": os.getenv("OLLAMA_MODEL", "llama2"),
        "ai.ollama.temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
        
        # OpenAI configuration
        "ai.openai.api_key": os.getenv("OPENAI_API_KEY"),
        "ai.openai.model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "ai.openai.temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        
        # Content processing configuration
        "content.chunk_size_default": int(os.getenv("CONTENT_CHUNK_SIZE_DEFAULT", "1000")),
        "content.chunk_size_max": int(os.getenv("CONTENT_CHUNK_SIZE_MAX", "4000")),
        "content.quality_threshold": float(os.getenv("CONTENT_QUALITY_THRESHOLD", "0.3")),
    }
    
    # Filter out None values
    return {k: v for k, v in env_mappings.items() if v is not None}

def apply_nested_override(config_dict: Dict[str, Any], key: str, value: Any) -> None:
    """Apply a nested configuration override using dot notation"""
    keys = key.split('.')
    current = config_dict
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value
```

### Production Secrets Management

#### File: `src/core/config/secrets.py`
```python
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SecretsManager:
    """Manage sensitive configuration values"""
    
    @staticmethod
    def get_required_secret(env_var: str, description: str) -> str:
        """Get a required secret from environment"""
        value = os.getenv(env_var)
        if not value:
            raise ValueError(f"Required secret {env_var} not found in environment: {description}")
        return value
    
    @staticmethod
    def get_optional_secret(env_var: str, default: Optional[str] = None) -> Optional[str]:
        """Get an optional secret from environment"""
        return os.getenv(env_var, default)
    
    @staticmethod
    def validate_production_secrets(config: SystemConfiguration) -> None:
        """Validate that production environment has required secrets"""
        if config.app.environment == "production":
            required_secrets = []
            
            # Check AnythingLLM API key
            if not config.anythingllm.api_key:
                required_secrets.append("ANYTHINGLLM_API_KEY")
            
            # Check GitHub API token
            if not config.github.api_token:
                required_secrets.append("GITHUB_API_TOKEN")
            
            # Check OpenAI API key if OpenAI is configured
            if (config.ai.primary_provider == "openai" or 
                config.ai.fallback_provider == "openai"):
                if not config.ai.openai.api_key:
                    required_secrets.append("OPENAI_API_KEY")
            
            # Check Redis password in production
            if not config.redis.password:
                logger.warning("Redis password not set in production environment")
            
            if required_secrets:
                raise ValueError(f"Missing required secrets for production: {', '.join(required_secrets)}")
```

## Acceptance Criteria
- [ ] All configuration models implemented exactly as specified in PRD-003
- [ ] Proper field validation with constraints and types
- [ ] Custom validators for endpoint URLs, API keys, and formats
- [ ] Environment variable mapping for all configurable values
- [ ] Secrets management for sensitive configuration
- [ ] Production environment validation
- [ ] Nested configuration override support
- [ ] Type hints for all fields and methods
- [ ] Comprehensive field descriptions for documentation
- [ ] Default factory functions for complex nested objects

## Dependencies
- pydantic >= 2.0.0
- typing_extensions (for Python < 3.10)

## Files to Create/Modify
- `src/core/config/__init__.py` (create)
- `src/core/config/models.py` (create)
- `src/core/config/validation.py` (create)
- `src/core/config/defaults.py` (create)
- `src/core/config/secrets.py` (create)

## Testing
- Validate all field constraints work correctly
- Test custom validators with valid/invalid inputs
- Test environment variable overrides
- Test production secrets validation
- Verify nested configuration updates
- Test default value generation

## Integration Notes
- These models will be used by ConfigurationManager in CFG-002
- Environment variable mapping supports Docker deployment (PRD-013)
- Circuit breaker configs are used by all external service clients
- Redis configuration must align with docker-compose.yml settings
- Secrets management integrates with production deployment procedures