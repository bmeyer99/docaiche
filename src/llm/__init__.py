"""
LLM Provider Package Init - Enhanced Multi-Provider System
Exposes providers and registry system for the multi-provider LLM architecture.
"""

# Core components that don't require external dependencies
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

# Optional provider imports with dependency checking
_providers_available = {}

try:
    from .ollama_provider import OllamaProvider
    _providers_available['OllamaProvider'] = OllamaProvider
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"OllamaProvider not available: {e}")
    OllamaProvider = None

try:
    from .openai_provider import OpenAIProvider
    _providers_available['OpenAIProvider'] = OpenAIProvider
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"OpenAIProvider not available: {e}")
    OpenAIProvider = None

# Import new providers
try:
    from .providers.openrouter_provider import OpenRouterProvider
    _providers_available['OpenRouterProvider'] = OpenRouterProvider
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"OpenRouterProvider not available: {e}")
    OpenRouterProvider = None

try:
    from .providers.anthropic_provider import AnthropicProvider
    _providers_available['AnthropicProvider'] = AnthropicProvider
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"AnthropicProvider not available: {e}")
    AnthropicProvider = None

try:
    from .providers.litellm_provider import LiteLLMProvider
    _providers_available['LiteLLMProvider'] = LiteLLMProvider
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"LiteLLMProvider not available: {e}")
    LiteLLMProvider = None

# Dynamic __all__ based on available providers
__all__ = [
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

# Add available providers to __all__
if OllamaProvider is not None:
    __all__.append("OllamaProvider")
if OpenAIProvider is not None:
    __all__.append("OpenAIProvider")
if OpenRouterProvider is not None:
    __all__.append("OpenRouterProvider")
if AnthropicProvider is not None:
    __all__.append("AnthropicProvider")
if LiteLLMProvider is not None:
    __all__.append("LiteLLMProvider")

def get_available_providers():
    """Get list of available provider classes"""
    return _providers_available

def is_provider_available(provider_name: str) -> bool:
    """Check if a specific provider is available"""
    return provider_name in _providers_available
