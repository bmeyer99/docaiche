"""
API Models for Search Configuration
====================================

Pydantic models for all search configuration API endpoints.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# Base models for common structures

class APIResponse(BaseModel):
    """Base API response model."""
    success: bool = Field(description="Whether the operation succeeded")
    message: Optional[str] = Field(default=None, description="Success or error message")
    data: Optional[Any] = Field(default=None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConfigChangeLog(BaseModel):
    """Configuration change history entry."""
    id: str = Field(description="Change ID")
    timestamp: datetime = Field(description="When the change was made")
    user: str = Field(description="User who made the change")
    section: str = Field(description="Configuration section changed")
    changes: Dict[str, Any] = Field(description="What was changed")
    previous_values: Dict[str, Any] = Field(description="Previous values")
    comment: Optional[str] = Field(default=None, description="Change comment")


# Configuration management models

class SearchConfigRequest(BaseModel):
    """Request to update search configuration."""
    queue_management: Optional[Dict[str, Any]] = None
    timeouts: Optional[Dict[str, Any]] = None
    performance_thresholds: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None
    feature_toggles: Optional[Dict[str, Any]] = None
    advanced_settings: Optional[Dict[str, Any]] = None
    comment: Optional[str] = Field(default=None, description="Change comment for audit")


class SearchConfigResponse(BaseModel):
    """Complete search configuration response."""
    queue_management: Dict[str, Any]
    timeouts: Dict[str, Any]
    performance_thresholds: Dict[str, Any]
    resource_limits: Dict[str, Any]
    feature_toggles: Dict[str, Any]
    advanced_settings: Dict[str, Any]
    last_updated: datetime
    version: str


class ConfigValidationRequest(BaseModel):
    """Request to validate configuration without saving."""
    config: SearchConfigRequest
    check_dependencies: bool = Field(default=True, description="Check for dependency conflicts")


class ConfigValidationResponse(BaseModel):
    """Configuration validation result."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ConfigExportRequest(BaseModel):
    """Request to export configuration."""
    format: str = Field(default="json", pattern="^(json|yaml)$")
    include_secrets: bool = Field(default=False)
    sections: Optional[List[str]] = Field(default=None, description="Specific sections to export")


class ConfigImportRequest(BaseModel):
    """Request to import configuration."""
    format: str = Field(default="json", pattern="^(json|yaml)$")
    data: str = Field(description="Configuration data to import")
    validate_only: bool = Field(default=False, description="Only validate, don't apply")
    merge: bool = Field(default=False, description="Merge with existing config")


# Vector search models

class VectorConnectionConfig(BaseModel):
    """AnythingLLM connection configuration."""
    base_url: str = Field(description="AnythingLLM API base URL")
    api_key: Optional[str] = Field(default=None, description="API key if required")
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    verify_ssl: bool = Field(default=True)


class VectorConnectionStatus(BaseModel):
    """Vector search connection status."""
    connected: bool
    endpoint: str
    version: Optional[str] = None
    workspaces_count: int = 0
    last_check: datetime
    error: Optional[str] = None


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""
    id: Optional[str] = Field(default=None, description="Workspace ID")
    name: str = Field(description="Workspace name")
    slug: str = Field(description="URL-friendly identifier")
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list, description="Associated technologies")
    tags: List[str] = Field(default_factory=list, description="Workspace tags")
    priority: int = Field(default=100, ge=0, le=1000)
    active: bool = Field(default=True)
    search_settings: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceListResponse(BaseModel):
    """List of workspaces."""
    workspaces: List[WorkspaceConfig]
    total: int
    page: int = 1
    per_page: int = 50


class VectorTestRequest(BaseModel):
    """Request to test vector search."""
    query: str = Field(description="Test query")
    workspace_slug: Optional[str] = Field(default=None, description="Specific workspace to test")
    limit: int = Field(default=5, ge=1, le=20)


class VectorTestResponse(BaseModel):
    """Vector search test results."""
    success: bool
    execution_time_ms: int
    results_count: int
    sample_results: List[Dict[str, Any]]
    error: Optional[str] = None


# Text AI models

class TextAIModelConfig(BaseModel):
    """Text AI model configuration."""
    provider: str = Field(description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Custom API endpoint")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)


class TextAIStatus(BaseModel):
    """Text AI service status."""
    connected: bool
    provider: str
    model: str
    available: bool
    last_check: datetime
    error: Optional[str] = None
    usage_today: Optional[Dict[str, int]] = None


class PromptTemplate(BaseModel):
    """Prompt template configuration."""
    id: str
    name: str
    type: str
    version: str
    template: str
    variables: List[str]
    active: bool
    performance_metrics: Optional[Dict[str, float]] = None
    last_updated: datetime


class PromptListResponse(BaseModel):
    """List of prompt templates."""
    prompts: List[PromptTemplate]
    total: int


class PromptUpdateRequest(BaseModel):
    """Request to update a prompt template."""
    template: str
    variables: Optional[List[str]] = None
    active: bool = Field(default=True, description="Whether this version is active")
    notes: Optional[str] = Field(default=None, description="Notes about this version")
    performance_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Performance metrics to track")


class PromptTestRequest(BaseModel):
    """Request to test a prompt."""
    prompt_id: str
    test_data: Dict[str, Any] = Field(description="Variable values for testing")
    compare_versions: Optional[List[str]] = Field(default=None, description="Versions to compare")


class PromptEnhanceRequest(BaseModel):
    """Request to enhance a prompt with AI."""
    prompt_id: str
    optimization_goal: str = Field(description="What to optimize for (clarity, accuracy, etc.)")
    examples: Optional[List[Dict[str, Any]]] = None


# Provider models

class ProviderConfig(BaseModel):
    """Provider configuration."""
    id: Optional[str] = None
    type: str = Field(description="Provider type (brave, google, etc.)")
    name: str
    enabled: bool = True
    priority: int = Field(default=100, ge=0)
    config: Dict[str, Any] = Field(description="Provider-specific configuration")
    rate_limits: Optional[Dict[str, Any]] = None
    cost_limits: Optional[Dict[str, Any]] = None


class ProviderStatus(BaseModel):
    """Provider health status."""
    id: str
    name: str
    type: str
    enabled: bool
    health: str = Field(description="Health status (healthy, degraded, unhealthy)")
    latency_ms: Optional[int] = None
    error_rate: float = 0.0
    last_check: datetime
    circuit_breaker_state: str = "closed"
    rate_limit_remaining: Optional[int] = None


class ProviderListResponse(BaseModel):
    """List of providers with status."""
    providers: List[ProviderStatus]
    total_healthy: int
    total_enabled: int


class ProviderTestRequest(BaseModel):
    """Request to test a provider."""
    provider_id: str
    test_query: str = Field(default="test", description="Query to test with")
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)


class ProviderPriorityUpdate(BaseModel):
    """Update provider priorities."""
    priorities: Dict[str, int] = Field(description="Map of provider_id to priority")


# Monitoring models

class SearchMetrics(BaseModel):
    """Search performance metrics."""
    time_range: str = Field(description="Metrics time range")
    total_searches: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cache_hit_rate: float
    error_rate: float
    searches_by_hour: List[Dict[str, Any]]
    top_queries: List[Dict[str, Any]]


class ProviderMetrics(BaseModel):
    """Provider usage metrics."""
    provider_id: str
    provider_name: str
    time_range: str
    total_requests: int
    success_rate: float
    avg_latency_ms: float
    total_cost: Optional[float] = None
    requests_by_hour: List[Dict[str, Any]]


class QueueMetrics(BaseModel):
    """Queue depth and performance metrics."""
    current_depth: int
    max_depth: int
    avg_wait_time_ms: float
    overflow_count: int
    processing_rate: float
    depth_history: List[Dict[str, Any]]


class LogQuery(BaseModel):
    """Log search query."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[str] = Field(default=None, pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    component: Optional[str] = None
    search_text: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)


class AlertConfig(BaseModel):
    """Alert configuration."""
    id: Optional[str] = None
    name: str
    type: str = Field(description="Alert type (threshold, anomaly, etc.)")
    condition: Dict[str, Any]
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    enabled: bool = True
    notification_channels: List[str]
    cooldown_minutes: int = Field(default=15, ge=1)


class ActiveAlert(BaseModel):
    """Active alert instance."""
    id: str
    alert_config_id: str
    name: str
    severity: str
    triggered_at: datetime
    details: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None