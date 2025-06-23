"""
LLM Provider Integration Data Models - PRD-005
Pydantic models for structured LLM responses and validation.
Implements exact models and fields required by PRD-005 and validation tests.
"""
import logging
from typing import List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EvaluationResult(BaseModel):
    """
    PRD-005: EvaluationResult model.
    Fields must match test_prd_005_llm_provider_comprehensive_validation.py exactly.
    """
    query: str = Field(..., description="Original user query")
    result_quality: str = Field(..., description="Quality assessment of results")  # Changed from float to str
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for results")
    explanation: str = Field(..., description="Explanation of evaluation")
    suggested_improvements: List[str] = Field(default_factory=list, description="Suggested improvements")

    # Additional fields required by some tests (optional)
    model_version: Optional[str] = Field(None, description="Model version")
    sufficiency_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sufficiency score")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    missing_aspects: Optional[List[str]] = Field(default=None, description="Missing aspects")
    should_enrich: Optional[bool] = Field(None, description="Should enrich flag")
    reasoning: Optional[str] = Field(None, description="Reasoning for enrichment")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

class RepositoryTarget(BaseModel):
    """
    PRD-005: RepositoryTarget model.
    """
    url: str = Field(..., description="Repository URL")
    priority: str = Field(..., description="Priority of this repository")
    reasoning: str = Field(..., description="Reasoning for targeting this repository")
    expected_value: str = Field(..., description="Expected value from this repository")

class EnrichmentStrategy(BaseModel):
    """
    PRD-005: EnrichmentStrategy model.
    """
    strategy_type: str = Field(..., description="Type of enrichment strategy")
    target_repositories: List[RepositoryTarget] = Field(default_factory=list, description="List of repository targets")
    search_terms: List[str] = Field(default_factory=list, description="Search terms for enrichment")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this strategy")

class QualityAssessment(BaseModel):
    """
    PRD-005: QualityAssessment model.
    """
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    content_quality: float = Field(..., ge=0.0, le=1.0, description="Content quality score")
    technical_accuracy: float = Field(..., ge=0.0, le=1.0, description="Technical accuracy score")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Completeness score")
    actionable_recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")

class LLMProviderStatus(BaseModel):
    """
    Runtime status of LLM provider availability (PRD-005).
    """
    ollama_available: bool = False
    openai_available: bool = False
    primary_provider: Optional[str] = None
    fallback_provider: Optional[str] = None
    any_provider_available: bool = False

def get_provider_status(config: Any) -> LLMProviderStatus:
    """
    Check which LLM providers are available at runtime (PRD-005).
    Args:
        config: AIConfig object or dict with ollama/openai/primary_provider/fallback_provider
    Returns:
        LLMProviderStatus instance
    """
    status = LLMProviderStatus()
    # Support both dict and Pydantic object for config
    ollama = getattr(config, "ollama", None) or (config.get("ollama") if isinstance(config, dict) else None)
    openai = getattr(config, "openai", None) or (config.get("openai") if isinstance(config, dict) else None)
    primary = getattr(config, "primary_provider", None) or (config.get("primary_provider") if isinstance(config, dict) else None)
    fallback = getattr(config, "fallback_provider", None) or (config.get("fallback_provider") if isinstance(config, dict) else None)

    if ollama:
        enabled = getattr(ollama, "enabled", None)
        endpoint = getattr(ollama, "endpoint", None)
        model = getattr(ollama, "model", None)
        if enabled is None and isinstance(ollama, dict):
            enabled = ollama.get("enabled")
            endpoint = ollama.get("endpoint")
            model = ollama.get("model")
        if enabled and endpoint and model:
            status.ollama_available = True

    if openai:
        enabled = getattr(openai, "enabled", None)
        api_key = getattr(openai, "api_key", None)
        model = getattr(openai, "model", None)
        if enabled is None and isinstance(openai, dict):
            enabled = openai.get("enabled")
            api_key = openai.get("api_key")
            model = openai.get("model")
        if enabled and api_key and model:
            status.openai_available = True

    status.any_provider_available = status.ollama_available or status.openai_available

    if status.any_provider_available:
        status.primary_provider = primary
        status.fallback_provider = fallback

    return status

class LLMProviderUnavailableError(Exception):
    """
    Raised when attempting to use LLM functionality without configured providers (PRD-005).
    """
    pass