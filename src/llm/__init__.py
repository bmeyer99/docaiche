"""
LLM Provider Package Init - Enhanced Multi-Provider System
Exposes providers and registry system for the multi-provider LLM architecture.
"""

from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .base_provider import BaseLLMProvider
from .provider_registry import (
    ProviderRegistry, 
    get_provider_registry, 
    register_provider,
    register_builtin_providers,
    discover_providers_in_module
)
from .models import (
    ProviderCapabilities, ProviderCategory, ProviderInfo,
    TextGenerationRequest, TextGenerationResponse,
    EmbeddingRequest, EmbeddingResponse,
    TestResult, ProviderHealth, HealthStatus
)

__all__ = [
    # Legacy providers
    "OllamaProvider",
    "OpenAIProvider",
    
    # Base provider interface
    "BaseLLMProvider",
    
    # Provider registry system
    "ProviderRegistry",
    "get_provider_registry",
    "register_provider",
    "register_builtin_providers",
    "discover_providers_in_module",
    
    # Data models
    "ProviderCapabilities",
    "ProviderCategory", 
    "ProviderInfo",
    "TextGenerationRequest",
    "TextGenerationResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "TestResult",
    "ProviderHealth",
    "HealthStatus",
]
