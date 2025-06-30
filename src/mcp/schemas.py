"""
MCP Protocol Schemas and Data Models
====================================

Complete implementation of MCP 2025 specification schemas including:
- Core protocol messages and responses
- Tool and resource definitions with annotations
- Authentication and authorization schemas
- Validation and error handling schemas

Follows MCP specification 2025-03-26 with OAuth 2.1 and RFC 8707 compliance.
"""

from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime
from enum import Enum
import logging

# Try to import pydantic, fall back to mock if not available
try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    try:
        from .mock_pydantic import BaseModel, Field, validator
    except ImportError:
        # Handle direct execution without package context
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mock_pydantic import BaseModel, Field, validator
    logger = logging.getLogger(__name__)
    logger.warning("pydantic not available, using mock implementation")

logger = logging.getLogger(__name__)


# Core MCP Protocol Types
class MCPVersion(str, Enum):
    """Supported MCP protocol versions."""
    V2025_03_26 = "2025-03-26"
    V2024_11_05 = "2024-11-05"  # Fallback compatibility


class TransportType(str, Enum):
    """Supported MCP transport mechanisms."""
    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"
    HTTP_SSE = "http-sse"  # Legacy support


class ContentType(str, Enum):
    """Supported content types in MCP messages."""
    TEXT = "text"
    IMAGE = "image" 
    AUDIO = "audio"  # 2025 specification addition


class ErrorCode(Enum):
    """JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    AUTHENTICATION_REQUIRED = -32000
    AUTHORIZATION_FAILED = -32001
    RESOURCE_NOT_FOUND = -32002
    RATE_LIMIT_EXCEEDED = -32003
    INVALID_PROTOCOL_VERSION = -32004


# Core MCP Message Schemas
class MCPRequest(BaseModel):
    """
    Base MCP request message following 2025 specification.
    
    All MCP requests inherit from this base to ensure consistent
    structure, validation, and correlation tracking.
    """
    
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(..., description="Request identifier")
    method: str = Field(..., description="MCP method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")
    
    # 2025 specification extensions
    mcp_version: MCPVersion = Field(MCPVersion.V2025_03_26, description="MCP protocol version")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    client_info: Optional[Dict[str, str]] = Field(None, description="Client identification")
    
    class Config:
        extra = "forbid"  # Strict validation
        

class MCPResponse(BaseModel):
    """
    Base MCP response message with error handling and metadata.
    
    Provides structured response format with optional result data,
    error information, and performance metadata.
    """
    
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(..., description="Request identifier")
    result: Optional[Dict[str, Any]] = Field(None, description="Success result data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    
    # Response metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    
    @validator('result', 'error')
    def validate_result_or_error(cls, v, values):
        """Ensure exactly one of result or error is present."""
        result = values.get('result')
        error = values.get('error')
        
        if result is not None and error is not None:
            raise ValueError("Cannot have both result and error")
        if result is None and error is None:
            raise ValueError("Must have either result or error")
            
        return v


class MCPError(BaseModel):
    """
    RFC 7807 compliant error structure for MCP responses.
    
    Provides structured error information with proper error codes,
    human-readable messages, and debugging context.
    """
    
    code: int = Field(..., description="JSON-RPC error code")
    message: str = Field(..., description="Human-readable error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")
    
    # RFC 7807 Problem Details extensions
    type: Optional[str] = Field(None, description="Problem type URI")
    title: Optional[str] = Field(None, description="Problem title")
    detail: Optional[str] = Field(None, description="Problem detail")
    instance: Optional[str] = Field(None, description="Problem instance URI")
    

# Tool Definition Schemas
class ToolAnnotation(BaseModel):
    """
    Tool behavior annotations following 2025 specification.
    
    Provides semantic information about tool behavior including
    safety characteristics, data sources, and execution requirements.
    """
    
    audience: List[str] = Field(default=["general"], description="Target audience")
    read_only: bool = Field(True, description="Tool only reads data")
    destructive: bool = Field(False, description="Tool may destroy/modify data")
    requires_consent: bool = Field(False, description="Tool requires explicit user consent")
    rate_limited: bool = Field(True, description="Tool is subject to rate limiting")
    data_sources: List[str] = Field(default=[], description="Data sources accessed")
    security_level: Literal["public", "internal", "confidential"] = Field("public", description="Required security level")


class ToolDefinition(BaseModel):
    """
    Complete MCP tool definition with 2025 annotations.
    
    Defines tool interface, behavior characteristics, and validation
    schemas for proper MCP client integration.
    """
    
    name: str = Field(..., description="Unique tool identifier", regex=r'^[a-z0-9_]+$')
    description: str = Field(..., description="Human-readable tool description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for tool input")
    
    # 2025 specification additions
    annotations: ToolAnnotation = Field(default_factory=ToolAnnotation, description="Tool behavior annotations")
    version: str = Field("1.0.0", description="Tool version")
    category: Optional[str] = Field(None, description="Tool category")
    examples: List[Dict[str, Any]] = Field(default=[], description="Usage examples")
    
    class Config:
        extra = "forbid"


# Resource Definition Schemas  
class ResourceDefinition(BaseModel):
    """
    MCP resource definition for data access patterns.
    
    Defines resource URI patterns, access methods, and caching
    characteristics for efficient data retrieval.
    """
    
    uri: str = Field(..., description="Resource URI pattern")
    name: str = Field(..., description="Human-readable resource name")
    description: str = Field(..., description="Resource description")
    mime_type: str = Field(..., description="Resource MIME type")
    
    # Resource characteristics
    cacheable: bool = Field(True, description="Resource can be cached")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")
    size_hint: Optional[int] = Field(None, description="Expected resource size")
    
    class Config:
        extra = "forbid"


# Prompt Definition Schemas
class PromptDefinition(BaseModel):
    """
    MCP prompt template definition for guided interactions.
    
    Provides pre-defined prompt templates that help users
    effectively utilize MCP tools and resources.
    """
    
    name: str = Field(..., description="Unique prompt identifier")
    description: str = Field(..., description="Prompt description")
    template: str = Field(..., description="Prompt template with placeholders")
    
    # Template metadata
    parameters: List[Dict[str, Any]] = Field(default=[], description="Template parameters")
    category: Optional[str] = Field(None, description="Prompt category")
    examples: List[str] = Field(default=[], description="Example usages")
    
    class Config:
        extra = "forbid"


# Authentication and Authorization Schemas
class AuthRequest(BaseModel):
    """
    OAuth 2.1 authentication request with Resource Indicators (RFC 8707).
    
    Implements 2025 MCP security requirements for scoped authentication
    with explicit resource targeting and consent management.
    """
    
    grant_type: Literal["authorization_code", "client_credentials"] = Field(..., description="OAuth grant type")
    client_id: str = Field(..., description="Client identifier")
    client_secret: Optional[str] = Field(None, description="Client secret")
    
    # RFC 8707 Resource Indicators
    resource: str = Field(..., description="Target resource indicator")
    scope: str = Field(..., description="Requested access scope")
    
    # Additional request context
    redirect_uri: Optional[str] = Field(None, description="Redirect URI")
    state: Optional[str] = Field(None, description="CSRF protection state")
    code_challenge: Optional[str] = Field(None, description="PKCE code challenge")
    code_challenge_method: Optional[Literal["S256"]] = Field(None, description="PKCE challenge method")
    
    class Config:
        extra = "forbid"


class AuthResponse(BaseModel):
    """
    OAuth 2.1 authentication response with scoped tokens.
    
    Returns access tokens scoped to specific resources and operations
    with proper expiration and refresh token handling.
    """
    
    access_token: str = Field(..., description="Access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    scope: str = Field(..., description="Granted scope")
    
    # RFC 8707 Resource Indicators response
    resource: str = Field(..., description="Target resource")
    
    # Optional refresh token
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    
    class Config:
        extra = "forbid"


class ResourceIndicator(BaseModel):
    """
    RFC 8707 Resource Indicator for OAuth 2.1.
    
    Specifies target resources for scoped access control.
    """
    
    resource: str = Field(..., description="Resource URI")
    scopes: List[str] = Field(default=[], description="Allowed scopes for resource")
    metadata: Dict[str, Any] = Field(default={}, description="Resource metadata")
    
    class Config:
        extra = "forbid"


class ConsentRequest(BaseModel):
    """
    User consent request for sensitive operations.
    
    Implements explicit consent requirements for operations that
    may access sensitive data or perform potentially risky actions.
    """
    
    operation: str = Field(..., description="Operation requiring consent")
    description: str = Field(..., description="Human-readable operation description")
    required_permissions: List[str] = Field(..., description="Required permissions")
    
    # Consent context
    client_id: str = Field(..., description="Requesting client")
    expires_in: int = Field(3600, description="Consent validity in seconds")
    data_sources: List[str] = Field(default=[], description="Data sources to be accessed")
    
    class Config:
        extra = "forbid"


# Content and Message Schemas
class ContentBlock(BaseModel):
    """
    MCP content block supporting multiple media types.
    
    Implements 2025 specification support for text, image, and audio
    content with proper metadata and validation.
    """
    
    type: ContentType = Field(..., description="Content type")
    
    # Text content
    text: Optional[str] = Field(None, description="Text content")
    
    # Media content
    data: Optional[str] = Field(None, description="Base64 encoded media data")
    mime_type: Optional[str] = Field(None, description="Media MIME type")
    
    # Content metadata
    annotations: Optional[Dict[str, Any]] = Field(None, description="Content annotations")
    source: Optional[str] = Field(None, description="Content source")
    
    @validator('text', 'data')
    def validate_content(cls, v, values):
        """Ensure appropriate content is provided for content type."""
        content_type = values.get('type')
        
        if content_type == ContentType.TEXT and not v and not values.get('text'):
            raise ValueError("Text content required for text type")
        elif content_type in [ContentType.IMAGE, ContentType.AUDIO] and not v and not values.get('data'):
            raise ValueError("Data required for media content types")
            
        return v


# Tool-Specific Schemas
class SearchToolRequest(BaseModel):
    """
    Request schema for docaiche_search tool.
    
    Implements intelligent documentation search with technology filtering,
    scope control, and result limiting for optimal user experience.
    """
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    technology: Optional[str] = Field(None, description="Technology filter")
    scope: Literal["cached", "live", "deep"] = Field("cached", description="Search scope")
    max_results: int = Field(10, ge=1, le=50, description="Maximum results")
    include_metadata: bool = Field(True, description="Include result metadata")
    
    class Config:
        extra = "forbid"


class IngestToolRequest(BaseModel):
    """
    Request schema for docaiche_ingest tool.
    
    Implements content ingestion with proper validation, consent
    requirements, and priority management.
    """
    
    source_url: str = Field(..., description="URL to ingest")
    source_type: Literal["github", "web", "api"] = Field(..., description="Source type")
    technology: Optional[str] = Field(None, description="Technology tag")
    priority: Literal["low", "normal", "high"] = Field("normal", description="Ingestion priority")
    workspace: Optional[str] = Field(None, description="Target workspace")
    
    # Ingestion options
    force_refresh: bool = Field(False, description="Force re-ingestion")
    include_metadata: bool = Field(True, description="Extract metadata")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum crawling depth for web sources")
    
    class Config:
        extra = "forbid"


class FeedbackToolRequest(BaseModel):
    """
    Request schema for docaiche_feedback tool.
    
    Implements comprehensive user feedback collection with proper categorization,
    privacy protection, and analytics integration for continuous improvement.
    """
    
    feedback_type: Literal["rating", "text", "bug", "feature", "search_quality", "content_accuracy"] = Field(..., description="Type of feedback")
    subject: Optional[str] = Field(None, max_length=200, description="Brief subject/title")
    content: str = Field(..., max_length=5000, description="Detailed feedback content")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Numeric rating (1-5)")
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Field("medium", description="Feedback severity")
    
    # Context information
    context: Optional[Dict[str, Any]] = Field(None, description="Context information")
    tags: Optional[List[str]] = Field(None, description="Feedback tags")
    anonymous: bool = Field(False, description="Submit anonymously")
    contact_info: Optional[Dict[str, str]] = Field(None, description="Contact information")
    
    class Config:
        extra = "forbid"


class StatusToolRequest(BaseModel):
    """
    Request schema for docaiche_status tool.
    
    Implements system health monitoring and status reporting with
    configurable detail levels and component-specific checks.
    """
    
    check_type: Literal["quick", "detailed", "component", "metrics"] = Field("quick", description="Type of status check")
    component: Optional[Literal["database", "search_engine", "cache", "authentication", "transport", "analytics", "storage", "external_api"]] = Field(None, description="Specific component to check")
    include_metrics: bool = Field(False, description="Include performance metrics")
    include_dependencies: bool = Field(False, description="Include dependency checks")
    time_range: Literal["1h", "6h", "24h", "7d"] = Field("1h", description="Time range for metrics")
    
    class Config:
        extra = "forbid"


class CollectionsToolRequest(BaseModel):
    """
    Request schema for docaiche_collections tool.
    
    Implements collection and workspace management with filtering,
    pagination, and detailed metadata access capabilities.
    """
    
    action: Literal["list", "get", "search", "stats"] = Field("list", description="Action to perform")
    collection_id: Optional[str] = Field(None, max_length=100, description="Specific collection ID")
    collection_type: Optional[Literal["workspace", "technology", "project", "user_defined", "system"]] = Field(None, description="Filter by collection type")
    access_level: Optional[Literal["public", "internal", "restricted", "private"]] = Field(None, description="Filter by access level")
    status: Optional[Literal["active", "archived", "maintenance", "deprecated"]] = Field(None, description="Filter by status")
    technology: Optional[str] = Field(None, max_length=50, description="Filter by technology")
    
    # Response options
    include_statistics: bool = Field(True, description="Include collection statistics")
    include_metadata: bool = Field(False, description="Include detailed metadata")
    
    # Pagination
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Pagination offset")
    
    class Config:
        extra = "forbid"


# TODO: IMPLEMENTATION ENGINEER - Complete remaining schemas:
# 1. Resource-specific request/response schemas
# 2. Prompt parameter validation schemas  
# 3. Batch operation schemas for bulk requests
# 4. WebSocket streaming message schemas
# 5. Advanced analytics and monitoring schemas

# Initialize Protocol Schemas
class InitializeRequest(BaseModel):
    """Initialize request parameters."""
    protocolVersion: str = Field(..., description="Protocol version")
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    clientInfo: Dict[str, Any] = Field(default_factory=dict)


class InitializeResponse(BaseModel):
    """Initialize response data."""
    protocolVersion: str = Field(..., description="Protocol version")
    capabilities: Dict[str, Any] = Field(..., description="Server capabilities")
    serverInfo: Dict[str, Any] = Field(..., description="Server information")
    sessionId: Optional[str] = Field(None, description="Session identifier")


class InitializedNotification(BaseModel):
    """Initialized notification (no response expected)."""
    initialized: bool = Field(True, description="Client initialized")


# Validation helpers
def validate_mcp_request(request_data: Dict[str, Any]) -> MCPRequest:
    """
    Validate incoming MCP request data.
    
    Args:
        request_data: Raw request data
        
    Returns:
        Validated MCPRequest object
        
    Raises:
        ValidationError: If request data is invalid
    """
    try:
        return MCPRequest(**request_data)
    except Exception as e:
        from .exceptions import ValidationError
        raise ValidationError(
            message=f"Invalid MCP request format: {str(e)}",
            error_code="INVALID_REQUEST_FORMAT",
            details={"validation_errors": str(e)}
        )


def create_success_response(
    request_id: Union[str, int],
    result: Dict[str, Any],
    execution_time_ms: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> MCPResponse:
    """
    Create successful MCP response.
    
    Args:
        request_id: Original request ID
        result: Response result data
        execution_time_ms: Optional execution time
        correlation_id: Optional correlation ID
        
    Returns:
        Structured MCP response
    """
    return MCPResponse(
        id=request_id,
        result=result,
        execution_time_ms=execution_time_ms,
        correlation_id=correlation_id
    )


def create_error_response(
    request_id: Union[str, int],
    error_code: int,
    error_message: str,
    error_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> MCPResponse:
    """
    Create error MCP response.
    
    Args:
        request_id: Original request ID
        error_code: JSON-RPC error code
        error_message: Human-readable error message
        error_data: Optional additional error data
        correlation_id: Optional correlation ID
        
    Returns:
        Structured MCP error response
    """
    return MCPResponse(
        id=request_id,
        error=MCPError(
            code=error_code,
            message=error_message,
            data=error_data
        ).dict(),
        correlation_id=correlation_id
    )