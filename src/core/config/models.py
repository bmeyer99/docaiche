"""
Configuration Models for AI Documentation Cache System - PRD-003
Complete Pydantic configuration schema implementing all requirements from CFG-001

All models follow exact specifications from the task requirements with proper validation,
type hints, and field descriptions for comprehensive configuration management.
"""

import logging
import re
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator

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
    data_dir: str = "./data"
    api_host: str = "0.0.0.0"
    api_port: int = Field(8080, ge=1024, le=65535)
    web_port: int = Field(8081, ge=1024, le=65535)
    workers: int = Field(4, ge=1, le=16)


class ContentConfig(BaseModel):
    """Content processing configuration with performance limits"""

    chunk_size_default: int = Field(
        1000, description="Default chunk size in characters"
    )
    chunk_size_max: int = Field(4000, description="Maximum chunk size in characters")
    chunk_overlap: int = Field(100, description="Character overlap between chunks")
    quality_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum quality score"
    )
    min_content_length: int = Field(50, description="Minimum content length to process")
    max_content_length: int = Field(
        1000000, description="Maximum content length to process"
    )


class WeaviateConfig(BaseModel):
    """Weaviate vector database configuration"""

    endpoint: str = Field(
        "http://weaviate:8080", description="Weaviate API endpoint"
    )
    api_key: str = Field("development-key", description="API key for authentication")
    grpc_port: int = Field(50051, description="gRPC port for Weaviate")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=60, timeout_seconds=30
        )
    )

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URLs"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v or len(v.strip()) < 8:
            raise ValueError("API key must be at least 8 characters")
        return v.strip()


class GitHubConfig(BaseModel):
    """GitHub API configuration"""

    api_token: str = Field("development-token", description="GitHub API token")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=300, timeout_seconds=30
        )
    )


class ScrapingConfig(BaseModel):
    """Web scraping configuration"""

    user_agent: str = Field(
        "DocaicheBot/1.0", description="User agent for web requests"
    )
    rate_limit_delay: float = Field(
        1.0, description="Delay between requests in seconds"
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=120, timeout_seconds=15
        )
    )

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Validate user agent string"""
        if not re.match(r"^[a-zA-Z0-9\-_/\.\s]+$", v):
            raise ValueError("Invalid user agent format")
        return v


class RedisConfig(BaseModel):
    """Redis caching configuration"""

    host: str = Field("redis", description="Redis host")
    port: int = Field(6379, description="Redis port")
    password: Optional[str] = Field(
        None, description="Redis password (recommended for production)"
    )
    db: int = Field(0, description="Redis database number")

    # Connection pool settings
    max_connections: int = Field(20, ge=1, description="Maximum connections in pool")
    connection_timeout: int = Field(
        5, ge=1, description="Connection timeout in seconds"
    )
    socket_timeout: int = Field(
        5, ge=1, description="Socket operation timeout in seconds"
    )

    # Memory and persistence settings (align with docker-compose)
    maxmemory: str = Field("512mb", description="Maximum memory usage")
    maxmemory_policy: str = Field("allkeys-lru", description="Memory eviction policy")
    appendonly: bool = Field(True, description="Enable append-only file persistence")

    # Security settings
    ssl: bool = Field(False, description="Enable SSL/TLS encryption")
    ssl_cert_reqs: Optional[str] = Field(
        None, description="SSL certificate requirements"
    )

    @field_validator("maxmemory")
    @classmethod
    def validate_redis_memory(cls, v: str) -> str:
        """Validate Redis memory configuration"""
        if not re.match(r"^\d+[kmgKMG][bB]?$", v):
            raise ValueError(
                'Invalid memory format. Use format like "512mb", "1gb", etc.'
            )
        return v.lower()


class OllamaConfig(BaseModel):
    """Ollama LLM provider configuration"""

    endpoint: str = Field("http://localhost:11434", description="Ollama API endpoint")
    model: str = Field("llama2", description="Default model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(60, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=60, timeout_seconds=30
        )
    )

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URLs"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v.rstrip("/")


class OpenAIConfig(BaseModel):
    """OpenAI LLM provider configuration"""

    api_key: str = Field("development-key", description="OpenAI API key")
    model: str = Field("gpt-3.5-turbo", description="Default model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens in response")
    timeout_seconds: int = Field(30, ge=1, description="Request timeout")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=300, timeout_seconds=30
        )
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format"""
        if not v or len(v.strip()) < 8:
            raise ValueError("API key must be at least 8 characters")
        return v.strip()


class ProviderConfig(BaseModel):
    """Individual provider configuration"""
    
    enabled: bool = Field(True, description="Whether provider is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")
    display_name: Optional[str] = Field(None, description="Custom display name")
    priority: int = Field(0, description="Provider priority (higher = preferred)")
    
    # Performance settings
    max_concurrent_requests: int = Field(5, ge=1, description="Maximum concurrent requests")
    timeout_seconds: int = Field(30, ge=1, description="Request timeout")
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")
    
    # Model configurations
    text_config: Optional[Dict[str, Any]] = Field(None, description="Text generation configuration")
    embedding_config: Optional[Dict[str, Any]] = Field(None, description="Embedding configuration")


class AIConfig(BaseModel):
    """Enhanced AI provider configuration with multi-provider support"""

    # Legacy fields for backward compatibility
    primary_provider: str = Field("ollama", description="Primary LLM provider ID")
    fallback_provider: Optional[str] = Field("openai", description="Fallback LLM provider ID")
    enable_failover: bool = Field(True, description="Enable automatic failover")
    
    # Legacy provider configs (for backward compatibility)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: Optional[OpenAIConfig] = None
    
    # New multi-provider system
    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, 
        description="Dynamic provider configurations"
    )
    
    # Global settings
    cache_ttl_seconds: int = Field(3600, ge=0, description="Cache TTL for LLM responses")
    load_balancing_enabled: bool = Field(False, description="Enable load balancing")
    health_check_interval: int = Field(300, ge=30, description="Health check interval in seconds")
    
    @model_validator(mode='after')
    def ensure_legacy_providers_in_providers(self):
        """Ensure legacy providers are included in the providers dict"""
        # Add ollama to providers if not already present
        if 'ollama' not in self.providers:
            self.providers['ollama'] = ProviderConfig(
                enabled=True,
                config={
                    'endpoint': self.ollama.endpoint,
                    'model': self.ollama.model,
                    'temperature': self.ollama.temperature,
                    'max_tokens': self.ollama.max_tokens,
                    'timeout_seconds': self.ollama.timeout_seconds
                },
                priority=10 if self.primary_provider == 'ollama' else 5
            )
        
        # Add openai to providers if configured
        if self.openai and 'openai' not in self.providers:
            self.providers['openai'] = ProviderConfig(
                enabled=True,
                config={
                    'api_key': self.openai.api_key,
                    'model': self.openai.model,
                    'temperature': self.openai.temperature,
                    'max_tokens': self.openai.max_tokens,
                    'timeout_seconds': self.openai.timeout_seconds
                },
                priority=10 if self.primary_provider == 'openai' else 5
            )
        
        return self
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider IDs"""
        return [pid for pid, config in self.providers.items() if config.enabled]
    
    def get_provider_config(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider"""
        return self.providers.get(provider_id)
    
    def add_provider(self, provider_id: str, config: ProviderConfig):
        """Add or update a provider configuration"""
        self.providers[provider_id] = config
    
    def remove_provider(self, provider_id: str) -> bool:
        """Remove a provider configuration"""
        if provider_id in self.providers:
            del self.providers[provider_id]
            return True
        return False


class EnrichmentConfig(BaseModel):
    """Knowledge enrichment system configuration"""

    max_concurrent_tasks: int = Field(
        5, ge=1, le=20, description="Maximum concurrent enrichment tasks"
    )
    task_timeout_seconds: int = Field(300, ge=30, description="Task timeout in seconds")
    retry_delay_seconds: int = Field(60, ge=1, description="Delay between retries")
    queue_poll_interval: int = Field(
        10, ge=1, description="Queue polling interval in seconds"
    )
    batch_size: int = Field(10, ge=1, le=100, description="Batch processing size")
    enable_relationship_mapping: bool = Field(
        True, description="Enable relationship mapping"
    )
    enable_tag_generation: bool = Field(
        True, description="Enable automatic tag generation"
    )
    enable_quality_assessment: bool = Field(
        True, description="Enable quality assessment"
    )
    min_confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class MCPProviderConfig(BaseModel):
    """MCP external search provider configuration"""
    
    enabled: bool = Field(True, description="Whether provider is enabled")
    api_key: Optional[str] = Field(None, description="API key if required")
    priority: int = Field(100, description="Provider priority (lower = higher priority)")
    max_requests_per_minute: int = Field(60, description="Rate limit")
    timeout_seconds: float = Field(5.0, description="Request timeout")
    search_engine_id: Optional[str] = Field(None, description="Google search engine ID")


class MCPExternalSearchConfig(BaseModel):
    """MCP external search configuration"""
    
    enabled: bool = Field(True, description="Enable external search providers")
    providers: Dict[str, MCPProviderConfig] = Field(
        default_factory=dict,
        description="External search provider configurations"
    )


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration"""
    
    external_search: MCPExternalSearchConfig = Field(
        default_factory=MCPExternalSearchConfig,
        description="External search provider configuration"
    )


class SystemConfiguration(BaseModel):
    """Top-level configuration object combining all config sections"""

    app: AppConfig
    content: ContentConfig
    weaviate: WeaviateConfig
    github: GitHubConfig
    scraping: ScrapingConfig
    redis: RedisConfig
    ai: AIConfig
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP configuration")

    model_config = {
        # Allow population by field name or alias
        "validate_by_name": True,
        # Validate assignment
        "validate_assignment": True,
        # Use enum values in schema
        "use_enum_values": True,
    }
