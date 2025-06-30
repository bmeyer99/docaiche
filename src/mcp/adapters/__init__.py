"""
MCP Client Adapters for DocaiChe Integration
============================================

This package provides adapter implementations that bridge MCP tools
and resources with the existing DocaiChe FastAPI endpoints.

The adapters handle:
- Protocol translation between MCP and REST APIs
- Data format conversion
- Error mapping and handling
- Authentication and session management
- Rate limiting and retry logic
"""

from .search_adapter import SearchAdapter
from .ingestion_adapter import IngestionAdapter
from .logs_adapter import LogsAdapter
from .health_adapter import HealthAdapter
from .config_adapter import ConfigAdapter

__all__ = [
    'SearchAdapter',
    'IngestionAdapter',
    'LogsAdapter',
    'HealthAdapter',
    'ConfigAdapter'
]