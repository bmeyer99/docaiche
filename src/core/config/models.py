"""
Configuration Models for AI Documentation Cache System - PRD-003
Complete Pydantic configuration schema implementing all requirements from CFG-001

All models follow exact specifications from the task requirements with proper validation,
type hints, and field descriptions for comprehensive configuration management.
"""

import logging
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for API clients"""
    failure_threshold: int = Field(3, description="Failures before opening circuit")
    recovery_timeout: int = Field(60, description="Seconds before attempting recovery")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")


class AppConfig(BaseModel):
    """Application configuration with core system settings"""
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


class AnythingLLMConfig(BaseModel):
    """AnythingLLM service configuration"""
    endpoint: str = Field(..., description="AnythingLLM API endpoint")
    api_key: str = Field(..., description="API key for authentication")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60, timeout_seconds=30)
    )
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URLs"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must start with http:// or https://')
        return v.rstrip('/')
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v or len(v.strip()) < 8:
            raise ValueError('API key must be at least 8 characters')
        return v.strip()


class GitHubConfig(BaseModel):
    """GitHub API configuration"""
    api_token: str = Field(..., description="GitHub API token")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300, timeout_seconds=30)
    )


class ScrapingConfig(BaseModel):
    """Web scraping configuration"""
    user_agent: str = Field("DocaicheBot/1.0", description="User agent for web requests")
    rate_limit_delay: float = Field(1.0, description="Delay between requests in seconds")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120, timeout_seconds=15)
    )
    
    @field_validator('user_agent')
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Validate user agent string"""
        if not re.match(r'^[a-zA-Z0-9\-_/\.\s]+$', v):
            raise ValueError('Invalid user agent format')
        return v


class RedisConfig(BaseModel):
    """Redis caching configuration"""
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
    
    @field_validator('maxmemory')
    @classmethod
    def validate_redis_memory(cls, v: str) -> str:
        """Validate Redis memory configuration"""
        if not re.match(r'^\d+[kmgKMG]?[bB]?$', v):
            raise ValueError('Invalid memory format. Use format like "512mb", "1gb", etc.')
        return v.lower()


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
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URLs"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must start with http:// or https://')
        return v.rstrip('/')


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
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v or len(v.strip()) < 8:
            raise ValueError('API key must be at least 8 characters')
        return v.strip()


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
    
    model_config = {
        # Allow population by field name or alias
        "validate_by_name": True,
        # Validate assignment
        "validate_assignment": True,
        # Use enum values in schema
        "use_enum_values": True
    }