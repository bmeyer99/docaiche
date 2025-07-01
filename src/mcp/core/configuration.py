"""
Search Configuration Schema
===========================

Comprehensive configuration for the MCP search system with all parameters
from PLAN.md. All parameters are configurable via admin UI.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class QueueManagementConfig(BaseModel):
    """Queue management configuration parameters."""
    
    max_concurrent_searches: int = Field(
        default=20,
        description="Maximum number of concurrent search operations allowed",
        ge=1,
        le=100
    )
    
    max_queue_depth: int = Field(
        default=100,
        description="Maximum number of queued search requests before overflow",
        ge=10,
        le=1000
    )
    
    queue_overflow_response_code: int = Field(
        default=503,
        description="HTTP response code when queue is full (503 Service Unavailable)",
        ge=400,
        le=599
    )
    
    priority_queue_enabled: bool = Field(
        default=True,
        description="Enable priority-based queue ordering"
    )
    
    queue_timeout_seconds: int = Field(
        default=300,
        description="Maximum time a request can wait in queue before timeout",
        ge=10,
        le=3600
    )


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration parameters."""
    
    per_user_rate_limit: int = Field(
        default=60,
        description="Maximum requests per user per minute",
        ge=1,
        le=1000
    )
    
    per_workspace_rate_limit: int = Field(
        default=300,
        description="Maximum requests per workspace per minute",
        ge=10,
        le=5000
    )
    
    global_rate_limit: int = Field(
        default=1000,
        description="Maximum total requests per minute across all users",
        ge=100,
        le=10000
    )
    
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Time window for rate limit calculations",
        ge=1,
        le=300
    )
    
    rate_limit_burst_allowance: float = Field(
        default=1.2,
        description="Burst allowance multiplier for temporary spikes",
        ge=1.0,
        le=2.0
    )


class TimeoutConfig(BaseModel):
    """Timeout configuration for various operations."""
    
    total_search_timeout_seconds: float = Field(
        default=30.0,
        description="Maximum time for entire search operation",
        ge=5.0,
        le=120.0
    )
    
    workspace_search_timeout_seconds: float = Field(
        default=2.0,
        description="Maximum time for individual workspace search",
        ge=0.5,
        le=10.0
    )
    
    external_search_timeout_seconds: float = Field(
        default=5.0,
        description="Maximum time for external provider search",
        ge=1.0,
        le=30.0
    )
    
    ai_decision_timeout_seconds: float = Field(
        default=3.0,
        description="Maximum time for AI decision-making operations",
        ge=0.5,
        le=15.0
    )
    
    cache_operation_timeout_seconds: float = Field(
        default=0.5,
        description="Maximum time for cache read/write operations",
        ge=0.1,
        le=2.0
    )


class PerformanceThresholds(BaseModel):
    """Performance thresholds and circuit breaker settings."""
    
    cache_circuit_breaker_threshold: int = Field(
        default=3,
        description="Number of consecutive cache failures before circuit opens",
        ge=1,
        le=10
    )
    
    cache_circuit_breaker_recovery_seconds: float = Field(
        default=30.0,
        description="Time before attempting to close circuit after failure",
        ge=5.0,
        le=300.0
    )
    
    minimum_relevance_score: float = Field(
        default=0.3,
        description="Minimum relevance score for including search results",
        ge=0.0,
        le=1.0
    )
    
    external_search_trigger_threshold: float = Field(
        default=0.5,
        description="Quality score threshold below which external search is triggered",
        ge=0.0,
        le=1.0
    )
    
    workspace_health_check_interval_seconds: int = Field(
        default=60,
        description="Interval between workspace health checks",
        ge=10,
        le=600
    )


class ResourceLimits(BaseModel):
    """Resource limits for search operations."""
    
    max_results_per_search: int = Field(
        default=50,
        description="Maximum number of results to return per search",
        ge=10,
        le=200
    )
    
    max_workspaces_per_search: int = Field(
        default=5,
        description="Maximum number of workspaces to search in parallel",
        ge=1,
        le=20
    )
    
    max_tokens_per_ai_request: int = Field(
        default=4000,
        description="Maximum tokens for AI decision requests",
        ge=500,
        le=8000
    )
    
    max_external_results: int = Field(
        default=20,
        description="Maximum results to fetch from external providers",
        ge=5,
        le=100
    )
    
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live for cached search results",
        ge=60,
        le=86400
    )


class SearchConfiguration(BaseModel):
    """
    Comprehensive search configuration with all parameters from PLAN.md.
    All parameters are exposed for configuration via the admin UI.
    """
    
    # Sub-configurations
    queue_management: QueueManagementConfig = Field(
        default_factory=QueueManagementConfig,
        description="Queue management and overflow settings"
    )
    
    
    timeouts: TimeoutConfig = Field(
        default_factory=TimeoutConfig,
        description="Timeout settings for various operations"
    )
    
    performance_thresholds: PerformanceThresholds = Field(
        default_factory=PerformanceThresholds,
        description="Performance thresholds and circuit breaker settings"
    )
    
    resource_limits: ResourceLimits = Field(
        default_factory=ResourceLimits,
        description="Resource limits for search operations"
    )
    
    # Feature toggles
    enable_external_search: bool = Field(
        default=True,
        description="Enable fallback to external search providers"
    )
    
    enable_ai_evaluation: bool = Field(
        default=True,
        description="Enable AI-powered result evaluation"
    )
    
    enable_query_refinement: bool = Field(
        default=True,
        description="Enable AI-powered query refinement"
    )
    
    enable_knowledge_ingestion: bool = Field(
        default=True,
        description="Enable learning loop for knowledge base updates"
    )
    
    enable_result_caching: bool = Field(
        default=True,
        description="Enable caching of search results"
    )
    
    # Advanced settings
    workspace_selection_strategy: str = Field(
        default="ai_driven",
        description="Strategy for workspace selection: 'ai_driven', 'all', 'manual'",
        pattern="^(ai_driven|all|manual)$"
    )
    
    result_ranking_algorithm: str = Field(
        default="hybrid",
        description="Result ranking algorithm: 'relevance', 'recency', 'hybrid'",
        pattern="^(relevance|recency|hybrid)$"
    )
    
    external_provider_priority: List[str] = Field(
        default=["brave", "google", "bing", "duckduckgo", "searxng"],
        description="Priority order for external search providers"
    )
    
    @validator('external_provider_priority')
    def validate_providers(cls, v):
        """Ensure provider list contains valid provider names."""
        valid_providers = {"brave", "google", "bing", "duckduckgo", "searxng"}
        for provider in v:
            if provider not in valid_providers:
                raise ValueError(f"Invalid provider: {provider}")
        return v
    
    def get_dependency_warnings(self) -> List[str]:
        """
        Check for configuration dependencies and return warnings.
        
        Returns:
            List of warning messages for conflicting or dependent settings
        """
        warnings = []
        
        # Check timeout dependencies
        if self.timeouts.workspace_search_timeout_seconds > self.timeouts.total_search_timeout_seconds / 2:
            warnings.append(
                "Workspace timeout is more than half of total timeout - may cause issues with multiple workspaces"
            )
        
        # Check rate limit consistency
        if self.rate_limiting.per_user_rate_limit > self.rate_limiting.global_rate_limit:
            warnings.append(
                "Per-user rate limit exceeds global rate limit - effectively limited by global"
            )
        
        # Check queue vs concurrent limits
        if self.queue_management.max_queue_depth < self.queue_management.max_concurrent_searches:
            warnings.append(
                "Queue depth is less than concurrent searches - may cause immediate overflow"
            )
        
        # Check cache dependency
        if not self.enable_result_caching and self.performance_thresholds.cache_circuit_breaker_threshold > 0:
            warnings.append(
                "Cache circuit breaker configured but caching is disabled"
            )
        
        # Check AI dependencies
        if not self.enable_ai_evaluation and self.enable_query_refinement:
            warnings.append(
                "Query refinement requires AI evaluation to be enabled"
            )
        
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary with flattened structure for UI."""
        return {
            "queue_management": self.queue_management.dict(),
            "rate_limiting": self.rate_limiting.dict(),
            "timeouts": self.timeouts.dict(),
            "performance_thresholds": self.performance_thresholds.dict(),
            "resource_limits": self.resource_limits.dict(),
            "feature_toggles": {
                "enable_external_search": self.enable_external_search,
                "enable_ai_evaluation": self.enable_ai_evaluation,
                "enable_query_refinement": self.enable_query_refinement,
                "enable_knowledge_ingestion": self.enable_knowledge_ingestion,
                "enable_result_caching": self.enable_result_caching,
            },
            "advanced_settings": {
                "workspace_selection_strategy": self.workspace_selection_strategy,
                "result_ranking_algorithm": self.result_ranking_algorithm,
                "external_provider_priority": self.external_provider_priority,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchConfiguration":
        """Create configuration from dictionary (e.g., from database or UI)."""
        # Handle nested structure
        config_data = {}
        
        if "queue_management" in data:
            config_data["queue_management"] = QueueManagementConfig(**data["queue_management"])
        
        if "rate_limiting" in data:
            config_data["rate_limiting"] = RateLimitingConfig(**data["rate_limiting"])
        
        if "timeouts" in data:
            config_data["timeouts"] = TimeoutConfig(**data["timeouts"])
        
        if "performance_thresholds" in data:
            config_data["performance_thresholds"] = PerformanceThresholds(**data["performance_thresholds"])
        
        if "resource_limits" in data:
            config_data["resource_limits"] = ResourceLimits(**data["resource_limits"])
        
        # Handle feature toggles
        if "feature_toggles" in data:
            config_data.update(data["feature_toggles"])
        
        # Handle advanced settings
        if "advanced_settings" in data:
            config_data.update(data["advanced_settings"])
        
        # Add any top-level fields
        for key, value in data.items():
            if key not in ["queue_management", "rate_limiting", "timeouts", 
                          "performance_thresholds", "resource_limits", 
                          "feature_toggles", "advanced_settings"]:
                config_data[key] = value
        
        return cls(**config_data)