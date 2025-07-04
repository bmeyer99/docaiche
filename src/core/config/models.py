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
    sync_ingestion: bool = Field(
        True, description="Enable synchronous knowledge ingestion"
    )
    sync_ingestion_timeout: int = Field(
        10, ge=1, le=60, description="Synchronous ingestion timeout in seconds"
    )


class Context7TTLConfig(BaseModel):
    """TTL-specific configuration for Context7 documents"""
    
    # Base TTL settings
    default_days: int = Field(
        7, ge=1, le=365, description="Default TTL for Context7 documents in days"
    )
    min_days: int = Field(
        1, ge=1, le=30, description="Minimum TTL allowed in days"
    )
    max_days: int = Field(
        90, ge=1, le=365, description="Maximum TTL allowed in days"
    )
    
    # Technology-specific TTL multipliers
    tech_multipliers: Dict[str, float] = Field(
        default_factory=lambda: {
            "react": 1.5,          # React docs get 1.5x longer TTL
            "vue": 1.5,            # Vue docs get 1.5x longer TTL
            "angular": 1.5,        # Angular docs get 1.5x longer TTL
            "python": 2.0,         # Python docs get 2x longer TTL
            "javascript": 1.2,     # JavaScript docs get 1.2x longer TTL
            "typescript": 1.2,     # TypeScript docs get 1.2x longer TTL
            "docker": 1.8,         # Docker docs get 1.8x longer TTL
            "kubernetes": 2.0,     # Kubernetes docs get 2x longer TTL
            "aws": 1.5,            # AWS docs get 1.5x longer TTL
            "azure": 1.5,          # Azure docs get 1.5x longer TTL
            "gcp": 1.5,            # GCP docs get 1.5x longer TTL
            "node": 1.3,           # Node.js docs get 1.3x longer TTL
        },
        description="Technology-specific TTL multipliers"
    )
    
    # Document type TTL adjustments
    doc_type_adjustments: Dict[str, float] = Field(
        default_factory=lambda: {
            "api": 0.8,            # API docs expire faster (more volatile)
            "tutorial": 1.5,       # Tutorials last longer (more stable)
            "guide": 1.3,          # Guides last longer
            "reference": 2.0,      # Reference docs last much longer
            "changelog": 0.5,      # Changelogs expire quickly
            "blog": 0.6,           # Blog posts expire relatively quickly
            "news": 0.4,           # News expires very quickly
            "documentation": 1.2,  # General documentation gets slight boost
            "example": 1.0,        # Examples get default TTL
        },
        description="Document type-specific TTL adjustments"
    )
    
    # Feature toggles
    enable_tech_multipliers: bool = Field(
        True, description="Enable technology-specific TTL multipliers"
    )
    enable_doc_type_adjustments: bool = Field(
        True, description="Enable document type TTL adjustments"
    )
    enable_freshness_boost: bool = Field(
        True, description="Give recently published content longer TTL"
    )
    enable_popularity_boost: bool = Field(
        True, description="Give popular content longer TTL"
    )
    
    # Freshness-based TTL adjustments
    freshness_boost_days: int = Field(
        30, ge=1, le=180, description="Days considered 'fresh' for TTL boost"
    )
    freshness_boost_multiplier: float = Field(
        1.5, ge=1.0, le=5.0, description="Multiplier for fresh content TTL"
    )
    
    # Popularity-based TTL adjustments
    popularity_threshold: int = Field(
        100, ge=1, description="Minimum views/stars for popularity boost"
    )
    popularity_boost_multiplier: float = Field(
        1.3, ge=1.0, le=3.0, description="Multiplier for popular content TTL"
    )
    
    @field_validator("tech_multipliers")
    @classmethod
    def validate_tech_multipliers(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate technology multipliers are within reasonable bounds"""
        for tech, multiplier in v.items():
            if not (0.1 <= multiplier <= 10.0):
                raise ValueError(f"Technology multiplier for {tech} must be between 0.1 and 10.0")
        return v
    
    @field_validator("doc_type_adjustments")
    @classmethod
    def validate_doc_type_adjustments(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate document type adjustments are within reasonable bounds"""
        for doc_type, adjustment in v.items():
            if not (0.1 <= adjustment <= 10.0):
                raise ValueError(f"Document type adjustment for {doc_type} must be between 0.1 and 10.0")
        return v
    
    @model_validator(mode='after')
    def validate_ttl_bounds(self):
        """Ensure TTL bounds are logical"""
        if self.min_days >= self.max_days:
            raise ValueError("min_days must be less than max_days")
        if self.default_days < self.min_days or self.default_days > self.max_days:
            raise ValueError("default_days must be between min_days and max_days")
        return self


class Context7IngestionConfig(BaseModel):
    """Context7 ingestion and processing configuration"""
    
    # Ingestion settings
    batch_size: int = Field(
        10, ge=1, le=100, description="Number of documents to process in each batch"
    )
    max_concurrent_batches: int = Field(
        3, ge=1, le=10, description="Maximum concurrent batches"
    )
    ingestion_timeout_seconds: int = Field(
        300, ge=30, le=3600, description="Timeout for ingestion operations"
    )
    retry_attempts: int = Field(
        3, ge=0, le=10, description="Number of retry attempts for failed ingestions"
    )
    retry_delay_seconds: int = Field(
        60, ge=1, le=300, description="Delay between retry attempts"
    )
    
    # Sync ingestion settings
    sync_enabled: bool = Field(
        True, description="Enable synchronous ingestion of Context7 results"
    )
    sync_timeout_seconds: int = Field(
        15, ge=5, le=120, description="Timeout for synchronous ingestion"
    )
    sync_batch_size: int = Field(
        5, ge=1, le=20, description="Batch size for synchronous ingestion"
    )
    
    # Pipeline settings
    enable_smart_pipeline: bool = Field(
        True, description="Use SmartIngestionPipeline for Context7 processing"
    )
    enable_content_validation: bool = Field(
        True, description="Validate content before ingestion"
    )
    enable_duplicate_detection: bool = Field(
        True, description="Detect and handle duplicate content"
    )
    
    # Fallback and error handling
    fallback_storage_enabled: bool = Field(
        True, description="Enable fallback storage when SmartIngestionPipeline fails"
    )
    max_fallback_items: int = Field(
        1000, ge=1, description="Maximum items to store in fallback storage"
    )
    fallback_cleanup_days: int = Field(
        7, ge=1, le=30, description="Days to keep items in fallback storage"
    )


class Context7CacheConfig(BaseModel):
    """Context7 cache configuration"""
    
    # Cache behavior
    enabled: bool = Field(True, description="Enable Context7 result caching")
    ttl_multiplier: float = Field(
        1.0, ge=0.1, le=10.0, description="Multiplier for cache TTL (cache_ttl = doc_ttl * multiplier)"
    )
    max_cache_size: int = Field(
        10000, ge=100, description="Maximum number of items in cache"
    )
    
    # Cache eviction
    eviction_policy: Literal["lru", "lfu", "ttl"] = Field(
        "lru", description="Cache eviction policy"
    )
    cleanup_interval_seconds: int = Field(
        300, ge=60, le=3600, description="Interval for cache cleanup"
    )
    
    # Cache warming
    enable_preload: bool = Field(
        False, description="Enable cache preloading at startup"
    )
    preload_popular_items: bool = Field(
        True, description="Preload popular items into cache"
    )
    preload_batch_size: int = Field(
        50, ge=1, le=500, description="Batch size for cache preloading"
    )


class Context7BackgroundJobConfig(BaseModel):
    """Context7 background job configuration"""
    
    # Job scheduling
    ttl_cleanup_enabled: bool = Field(
        True, description="Enable TTL cleanup background job"
    )
    ttl_cleanup_interval_seconds: int = Field(
        3600, ge=300, le=86400, description="Interval for TTL cleanup job"
    )
    ttl_cleanup_batch_size: int = Field(
        100, ge=10, le=1000, description="Batch size for TTL cleanup"
    )
    
    # Metrics collection
    metrics_collection_enabled: bool = Field(
        True, description="Enable metrics collection for Context7"
    )
    metrics_collection_interval_seconds: int = Field(
        300, ge=60, le=3600, description="Interval for metrics collection"
    )
    
    # Health checks
    health_check_enabled: bool = Field(
        True, description="Enable Context7 health checks"
    )
    health_check_interval_seconds: int = Field(
        60, ge=30, le=300, description="Interval for health checks"
    )
    
    # Maintenance
    maintenance_window_enabled: bool = Field(
        False, description="Enable maintenance window for heavy operations"
    )
    maintenance_window_start_hour: int = Field(
        2, ge=0, le=23, description="Start hour for maintenance window (24h format)"
    )
    maintenance_window_duration_hours: int = Field(
        4, ge=1, le=12, description="Duration of maintenance window in hours"
    )


class Context7Config(BaseModel):
    """Comprehensive Context7 documentation ingestion configuration"""
    
    # Core settings
    enabled: bool = Field(True, description="Enable Context7 documentation ingestion")
    
    # TTL configuration
    ttl: Context7TTLConfig = Field(
        default_factory=Context7TTLConfig,
        description="TTL-specific configuration for Context7 documents"
    )
    
    # Ingestion configuration
    ingestion: Context7IngestionConfig = Field(
        default_factory=Context7IngestionConfig,
        description="Ingestion and processing configuration"
    )
    
    # Cache configuration
    cache: Context7CacheConfig = Field(
        default_factory=Context7CacheConfig,
        description="Cache configuration for Context7 results"
    )
    
    # Background job configuration
    background_jobs: Context7BackgroundJobConfig = Field(
        default_factory=Context7BackgroundJobConfig,
        description="Background job configuration"
    )
    
    # Integration settings
    weaviate_ttl_enabled: bool = Field(
        True, description="Apply TTL metadata to Weaviate documents"
    )
    enable_audit_logging: bool = Field(
        True, description="Enable audit logging for Context7 operations"
    )
    
    # Performance settings
    max_memory_usage_mb: int = Field(
        512, ge=128, le=2048, description="Maximum memory usage for Context7 operations"
    )
    enable_performance_monitoring: bool = Field(
        True, description="Enable performance monitoring and metrics"
    )
    
    def get_effective_ttl(self, technology: Optional[str] = None, doc_type: Optional[str] = None, 
                         is_fresh: bool = False, is_popular: bool = False) -> int:
        """
        Calculate effective TTL based on all configured factors
        
        Args:
            technology: Technology identifier (e.g., "react", "python")
            doc_type: Document type (e.g., "api", "tutorial")
            is_fresh: Whether content is considered fresh
            is_popular: Whether content is considered popular
            
        Returns:
            Effective TTL in days
        """
        base_ttl = self.ttl.default_days
        
        # Apply technology multiplier
        if technology and self.ttl.enable_tech_multipliers:
            tech_multiplier = self.ttl.tech_multipliers.get(technology.lower(), 1.0)
            base_ttl = int(base_ttl * tech_multiplier)
        
        # Apply document type adjustment
        if doc_type and self.ttl.enable_doc_type_adjustments:
            doc_adjustment = self.ttl.doc_type_adjustments.get(doc_type.lower(), 1.0)
            base_ttl = int(base_ttl * doc_adjustment)
        
        # Apply freshness boost
        if is_fresh and self.ttl.enable_freshness_boost:
            base_ttl = int(base_ttl * self.ttl.freshness_boost_multiplier)
        
        # Apply popularity boost
        if is_popular and self.ttl.enable_popularity_boost:
            base_ttl = int(base_ttl * self.ttl.popularity_boost_multiplier)
        
        # Ensure within bounds
        return max(self.ttl.min_days, min(base_ttl, self.ttl.max_days))
    
    def get_cache_ttl(self, doc_ttl_days: int) -> int:
        """
        Calculate cache TTL based on document TTL
        
        Args:
            doc_ttl_days: Document TTL in days
            
        Returns:
            Cache TTL in seconds
        """
        if not self.cache.enabled:
            return 0
        
        # Convert days to seconds and apply multiplier
        doc_ttl_seconds = doc_ttl_days * 24 * 3600
        return int(doc_ttl_seconds * self.cache.ttl_multiplier)


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
    context7: Context7Config = Field(default_factory=Context7Config, description="Context7 ingestion configuration")
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP configuration")

    model_config = {
        # Allow population by field name or alias
        "validate_by_name": True,
        # Validate assignment
        "validate_assignment": True,
        # Use enum values in schema
        "use_enum_values": True,
    }
