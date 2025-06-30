"""
MCP Resources Implementation
============================

Complete implementation of MCP resource handlers following 2025 specification
with proper caching, access patterns, and integration with DocaiChe services.

Key Resources:
- DocumentationResource: Direct document access and metadata
- MetricsResource: System performance and usage metrics
- WorkspacesResource: Workspace enumeration and information
- StatusResource: System health and dependency status
- CollectionsResource: Collection metadata and organization

Each resource implements proper caching strategies, access control,
and comprehensive error handling for production deployment.
"""

from .base_resource import BaseResource, ResourceMetadata
from .documentation_resource import DocumentationResource
from .metrics_resource import MetricsResource
from .workspaces_resource import WorkspacesResource
from .status_resource import StatusResource
from .collections_resource import CollectionsResource

__all__ = [
    'BaseResource',
    'ResourceMetadata',
    'DocumentationResource',
    'MetricsResource',
    'WorkspacesResource',
    'StatusResource',
    'CollectionsResource'
]