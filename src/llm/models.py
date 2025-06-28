"""
Provider Data Models - AI Providers Implementation
Core data models for the multi-provider LLM system
"""

from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ProviderCategory(str, Enum):
    """Provider categories as defined in specification"""
    CLOUD = "cloud"
    LOCAL = "local" 
    GATEWAY = "gateway"
    SPECIALIZED = "specialized"


class ModelType(str, Enum):
    """Types of models supported"""
    TEXT = "text"
    EMBEDDING = "embedding"


class ProviderCapabilities(BaseModel):
    """Capabilities supported by a provider"""
    text_generation: bool = False
    embeddings: bool = False
    streaming: bool = False
    function_calling: bool = False
    local: bool = False
    model_discovery: bool = False
    prompt_caching: bool = False
    system_prompts: bool = False
    json_mode: bool = False
    vision: bool = False


class ModelInfo(BaseModel):
    """Information about a specific model"""
    model_id: str = Field(..., description="Unique model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    model_type: ModelType = Field(..., description="Type of model (text/embedding)")
    context_window: Optional[int] = Field(None, description="Maximum context length")
    max_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    cost_per_token: Optional[float] = Field(None, description="Cost per token in USD")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Model-specific capabilities")
    deprecated: bool = Field(False, description="Whether model is deprecated")


class ModelDiscoveryResult(BaseModel):
    """Result of model discovery operation"""
    text_models: List[ModelInfo] = Field(default_factory=list)
    embedding_models: List[ModelInfo] = Field(default_factory=list)
    discovery_time: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="Source of model information (api/static/cache)")


class ProviderInfo(BaseModel):
    """Basic information about a provider"""
    provider_id: str = Field(..., description="Unique provider identifier")
    display_name: str = Field(..., description="Human-readable provider name")
    description: Optional[str] = Field(None, description="Provider description")
    category: ProviderCategory = Field(..., description="Provider category")
    capabilities: ProviderCapabilities = Field(..., description="Provider capabilities")
    enabled: bool = Field(True, description="Whether provider is enabled")
    config_schema: Dict[str, Any] = Field(..., description="JSON schema for configuration")


class TestResult(BaseModel):
    """Result of provider connection test"""
    success: bool = Field(..., description="Whether test was successful")
    latency_ms: Optional[int] = Field(None, description="Response latency in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    models: Optional[ModelDiscoveryResult] = Field(None, description="Discovered models if successful")
    capabilities: ProviderCapabilities = Field(..., description="Provider capabilities")
    test_timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(str, Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProviderHealth(BaseModel):
    """Provider health information"""
    provider_id: str = Field(..., description="Provider identifier")
    status: HealthStatus = Field(..., description="Current health status")
    last_check: datetime = Field(..., description="Last health check time")
    latency_ms: Optional[int] = Field(None, description="Average latency")
    error_rate: Optional[float] = Field(None, description="Error rate (0.0-1.0)")
    success_rate: Optional[float] = Field(None, description="Success rate (0.0-1.0)")
    error_message: Optional[str] = Field(None, description="Last error message")


class ProviderMetrics(BaseModel):
    """Provider performance metrics"""
    provider_id: str = Field(..., description="Provider identifier")
    requests_total: int = Field(0, description="Total requests made")
    requests_successful: int = Field(0, description="Successful requests")
    requests_failed: int = Field(0, description="Failed requests")
    average_latency_ms: float = Field(0.0, description="Average response latency")
    total_tokens_used: int = Field(0, description="Total tokens consumed")
    total_cost_usd: float = Field(0.0, description="Total cost in USD")
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")


class TextGenerationRequest(BaseModel):
    """Request for text generation"""
    prompt: str = Field(..., description="Input prompt")
    model_id: Optional[str] = Field(None, description="Specific model to use")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    top_p: Optional[float] = Field(None, description="Nucleus sampling parameter")
    stop_sequences: Optional[List[str]] = Field(None, description="Stop sequences")
    streaming: bool = Field(False, description="Enable streaming response")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TextGenerationResponse(BaseModel):
    """Response from text generation"""
    text: str = Field(..., description="Generated text")
    finish_reason: str = Field(..., description="Reason generation stopped")
    tokens_used: int = Field(..., description="Total tokens used")
    latency_ms: int = Field(..., description="Response latency")
    model_id: str = Field(..., description="Model used for generation")
    provider_id: str = Field(..., description="Provider used")
    cost_usd: Optional[float] = Field(None, description="Cost of request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EmbeddingRequest(BaseModel):
    """Request for embeddings generation"""
    texts: List[str] = Field(..., description="Input texts to embed")
    model_id: Optional[str] = Field(None, description="Specific model to use")
    batch_size: Optional[int] = Field(None, description="Batch size for processing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EmbeddingResponse(BaseModel):
    """Response from embedding generation"""
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    tokens_used: int = Field(..., description="Total tokens used")
    latency_ms: int = Field(..., description="Response latency")
    model_id: str = Field(..., description="Model used for embeddings")
    provider_id: str = Field(..., description="Provider used")
    cost_usd: Optional[float] = Field(None, description="Cost of request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProviderConfig(BaseModel):
    """Base configuration for any provider"""
    provider_id: str = Field(..., description="Unique provider identifier")
    enabled: bool = Field(True, description="Whether provider is enabled")
    display_name: Optional[str] = Field(None, description="Custom display name")
    category: ProviderCategory = Field(..., description="Provider category")
    
    # Dynamic configuration based on provider schema
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")
    
    # Model configurations
    text_config: Optional[Dict[str, Any]] = Field(None, description="Text generation configuration")
    embedding_config: Optional[Dict[str, Any]] = Field(None, description="Embedding configuration")
    
    # Performance settings
    max_concurrent_requests: int = Field(5, description="Maximum concurrent requests")
    timeout_seconds: int = Field(30, description="Request timeout")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    
    # Health monitoring
    health_check_interval: int = Field(300, description="Health check interval in seconds")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LEAST_COST = "least_cost"
    RANDOM = "random"
    WEIGHTED = "weighted"


class LoadBalancingConfig(BaseModel):
    """Configuration for load balancing"""
    enabled: bool = Field(False, description="Enable load balancing")
    strategy: LoadBalancingStrategy = Field(LoadBalancingStrategy.ROUND_ROBIN)
    providers: List[str] = Field(default_factory=list, description="Provider IDs for load balancing")
    weights: Dict[str, float] = Field(default_factory=dict, description="Provider weights for weighted strategy")
    health_threshold: float = Field(0.95, description="Minimum health score to include provider")


class FailoverConfig(BaseModel):
    """Configuration for provider failover"""
    enabled: bool = Field(True, description="Enable automatic failover")
    primary_provider: str = Field(..., description="Primary provider ID")
    fallback_providers: List[str] = Field(default_factory=list, description="Ordered list of fallback providers")
    failure_threshold: int = Field(3, description="Consecutive failures before failover")
    recovery_timeout: int = Field(300, description="Seconds before retrying failed provider")


# API Request/Response Models for endpoints

class ProviderTestRequest(BaseModel):
    """Request to test a provider"""
    config: Dict[str, Any] = Field(..., description="Provider configuration to test")
    test_mode: Literal["text", "embedding", "connection"] = Field("connection", description="Type of test to perform")


class ProviderConfigRequest(BaseModel):
    """Request to configure a provider"""
    enabled: bool = Field(True, description="Whether to enable the provider")
    config: Dict[str, Any] = Field(..., description="Provider configuration")
    text_config: Optional[Dict[str, Any]] = Field(None, description="Text generation config")
    embedding_config: Optional[Dict[str, Any]] = Field(None, description="Embedding config")


class ProvidersListResponse(BaseModel):
    """Response for listing providers"""
    providers: List[ProviderInfo] = Field(..., description="Available providers")
    total_count: int = Field(..., description="Total number of providers")
    enabled_count: int = Field(..., description="Number of enabled providers")


class ProviderStatusResponse(BaseModel):
    """Response for provider status"""
    provider_id: str = Field(..., description="Provider identifier")
    health: ProviderHealth = Field(..., description="Current health status")
    metrics: Optional[ProviderMetrics] = Field(None, description="Performance metrics")
    config: ProviderConfig = Field(..., description="Current configuration")


# Additional models for backward compatibility with existing code
class EvaluationResult(BaseModel):
    """Result of an LLM evaluation"""
    score: float = Field(..., ge=0.0, le=1.0, description="Evaluation score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation")
    reasoning: Optional[str] = Field(None, description="Reasoning for evaluation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EnrichmentStrategy(str, Enum):
    """Enrichment strategy types"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    CONTEXTUAL = "contextual"


class QualityAssessment(BaseModel):
    """Quality assessment result"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    clarity_score: float = Field(..., ge=0.0, le=1.0, description="Content clarity score")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Content completeness score")
    accuracy_score: float = Field(..., ge=0.0, le=1.0, description="Content accuracy score")
    usefulness_score: float = Field(..., ge=0.0, le=1.0, description="Content usefulness score")
    assessment_reasoning: Optional[str] = Field(None, description="Reasoning for assessment")


# Provider status tracking
class LLMProviderStatus(str, Enum):
    """LLM provider status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# Exception for backward compatibility
class LLMProviderUnavailableError(Exception):
    """Raised when LLM provider is unavailable"""
    pass


def get_provider_status(provider_name: str) -> LLMProviderStatus:
    """Get status of a provider (placeholder implementation)"""
    return LLMProviderStatus.UNKNOWN