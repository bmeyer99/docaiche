"""
External Search Provider Implementations
========================================

Concrete implementations of search providers.
"""

from .brave import BraveSearchProvider
from .google import GoogleSearchProvider
from .bing import BingSearchProvider
from .duckduckgo import DuckDuckGoSearchProvider
from .searxng import SearXNGSearchProvider

__all__ = [
    "BraveSearchProvider",
    "GoogleSearchProvider", 
    "BingSearchProvider",
    "DuckDuckGoSearchProvider",
    "SearXNGSearchProvider"
]

# Provider class mapping for dynamic instantiation
PROVIDER_CLASSES = {
    "brave": BraveSearchProvider,
    "google": GoogleSearchProvider,
    "bing": BingSearchProvider,
    "duckduckgo": DuckDuckGoSearchProvider,
    "searxng": SearXNGSearchProvider
}