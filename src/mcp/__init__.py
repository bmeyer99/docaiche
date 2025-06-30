"""
Model Context Protocol (MCP) Implementation for DocAIche
========================================================

This package implements a production-ready MCP server that integrates with the
DocAIche AI Documentation Cache System, following the 2025 MCP specification
including OAuth 2.1, Resource Indicators (RFC 8707), and Streamable HTTP transport.

Key Components:
- MCP Server: Main server implementation with OAuth 2.1 compliance
- Authentication: OAuth 2.1 handlers with Resource Indicators
- Transport: Streamable HTTP transport with fallback mechanisms
- Tools: MCP tool implementations (search, ingest, feedback)
- Resources: MCP resource handlers (collections, status, metrics)
- Security: Comprehensive security framework with audit logging

Architecture follows the AI Stitching Programming Technique with:
- Scaffolding Phase: Complete structural foundation
- Implementation Phase: Business logic within established scaffolding  
- Integration Phase: Cohesive system assembly

Compliance:
- MCP Specification 2025-03-26
- OAuth 2.1 (RFC 9068)
- Resource Indicators (RFC 8707)
- Security Best Practices (June 2025 updates)
"""

__version__ = "1.0.0"
__author__ = "DocAIche Development Team"
__license__ = "MIT"

# Core MCP components
from .server import MCPServer
from .auth import AuthenticationManager, ConsentManager
from .transport import StreamableHTTPTransport, StdioTransport
from .tools import (
    SearchTool,
    IngestTool, 
    FeedbackTool,
    StatusTool,
    CollectionsTool
)
from .resources import (
    DocumentationResource,
    MetricsResource,
    WorkspacesResource
)
from .security import SecurityValidator, AuditLogger

# MCP protocol types and schemas
from .schemas import (
    MCPRequest,
    MCPResponse,
    MCPError,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition
)

# Configuration and exceptions
from .config import MCPConfig
from .exceptions import MCPException, AuthenticationError, ValidationError

__all__ = [
    # Core components
    'MCPServer',
    'AuthenticationManager',
    'ConsentManager',
    'StreamableHTTPTransport', 
    'StdioTransport',
    
    # Tools
    'SearchTool',
    'IngestTool',
    'FeedbackTool', 
    'StatusTool',
    'CollectionsTool',
    
    # Resources
    'DocumentationResource',
    'MetricsResource',
    'WorkspacesResource',
    
    # Security
    'SecurityValidator',
    'AuditLogger',
    
    # Schemas
    'MCPRequest',
    'MCPResponse', 
    'MCPError',
    'ToolDefinition',
    'ResourceDefinition',
    'PromptDefinition',
    
    # Configuration
    'MCPConfig',
    
    # Exceptions
    'MCPException',
    'AuthenticationError',
    'ValidationError'
]