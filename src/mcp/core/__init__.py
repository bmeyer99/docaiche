"""
MCP Core Infrastructure
=======================

Core components for the MCP search system including:
- Search orchestration
- Configuration management
- Queue management interfaces
- Error handling framework
- Data models
"""

from .configuration import SearchConfiguration
from .orchestrator import SearchOrchestrator
from .queue import QueueManager, PriorityQueue
from .exceptions import (
    MCPSearchError,
    QueueOverflowError,
    RateLimitExceededError,
    SearchTimeoutError,
    ProviderError,
    TextAIError,
    ConfigurationError
)
from .models import (
    NormalizedQuery,
    SearchRequest,
    VectorSearchResults,
    EvaluationResult,
    SearchResponse,
    UserContext,
    QueueStats
)

__all__ = [
    # Configuration
    "SearchConfiguration",
    
    # Orchestration
    "SearchOrchestrator",
    
    # Queue Management
    "QueueManager",
    "PriorityQueue",
    
    # Exceptions
    "MCPSearchError",
    "QueueOverflowError",
    "RateLimitExceededError",
    "SearchTimeoutError",
    "ProviderError",
    "TextAIError",
    "ConfigurationError",
    
    # Data Models
    "NormalizedQuery",
    "SearchRequest",
    "VectorSearchResults",
    "EvaluationResult",
    "SearchResponse",
    "UserContext",
    "QueueStats"
]