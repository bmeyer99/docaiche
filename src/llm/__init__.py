"""
LLM Provider Integration Layer - PRD-005
Unified client for interacting with multiple Large Language Model providers

Exports all LLM components for easy integration with other system components.
"""

from .models import (
    EvaluationResult,
    RepositoryTarget,
    EnrichmentStrategy,
    QualityAssessment
)

from .json_parser import (
    JSONParser,
    JSONParsingError,
    JSONValidationError,
    parse_llm_response
)

from .base_provider import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError
)

from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

from .client import (
    LLMProviderClient,
    ProviderStatus,
    create_llm_client
)

from .prompt_manager import (
    PromptManager,
    PromptTemplateError,
    get_prompt_manager,
    format_template
)

__all__ = [
    # Data models
    "EvaluationResult",
    "RepositoryTarget",
    "EnrichmentStrategy",
    "QualityAssessment",
    
    # JSON parsing
    "JSONParser",
    "JSONParsingError",
    "JSONValidationError",
    "parse_llm_response",
    
    # Base provider
    "BaseLLMProvider",
    "LLMProviderError",
    "LLMProviderTimeoutError",
    "LLMProviderUnavailableError",
    
    # Provider implementations
    "OllamaProvider",
    "OpenAIProvider",
    
    # Main client
    "LLMProviderClient",
    "ProviderStatus",
    "create_llm_client",
    
    # Prompt management
    "PromptManager",
    "PromptTemplateError",
    "get_prompt_manager",
    "format_template"
]