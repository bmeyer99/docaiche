"""
MCP Configuration Management
===========================

Comprehensive configuration management for MCP server operations including:
- Environment variable handling with validation
- OAuth 2.1 and security configuration
- Transport and protocol settings
- Integration with existing DocaiChe configuration

Follows hierarchical configuration loading with proper validation
and security considerations for production deployment.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

# Try to import pydantic, fall back to mock if not available
try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    from .mock_pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecurityLevel(str, Enum):
    """Security enforcement levels."""
    DEVELOPMENT = "development"  # Relaxed security for development
    TESTING = "testing"         # Moderate security for testing
    PRODUCTION = "production"   # Full security enforcement


class MCPTransportConfig(BaseModel):
    """
    MCP transport layer configuration.
    
    Configures transport mechanisms, connection settings, and
    protocol-specific options for MCP communication.
    """
    
    # Primary transport configuration
    transport_type: str = Field("streamable-http", description="Primary transport mechanism")
    bind_host: str = Field("0.0.0.0", description="Server bind address")
    bind_port: int = Field(8001, description="Server bind port")
    
    # HTTP transport settings
    max_connections: int = Field(100, description="Maximum concurrent connections")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    read_timeout: int = Field(60, description="Read timeout in seconds")
    write_timeout: int = Field(60, description="Write timeout in seconds")
    
    # Protocol settings
    max_message_size: int = Field(10485760, description="Maximum message size (10MB)")
    compression_enabled: bool = Field(True, description="Enable response compression")
    
    # Fallback transport
    enable_stdio_fallback: bool = Field(True, description="Enable stdio transport fallback")
    
    @validator('bind_port')
    def validate_port(cls, v):
        """Validate port number range."""
        if not 1024 <= v <= 65535:
            raise ValueError("Port must be between 1024 and 65535")
        return v
    
    @validator('max_connections')
    def validate_max_connections(cls, v):
        """Validate connection limit."""
        if v < 1 or v > 10000:
            raise ValueError("Max connections must be between 1 and 10000")
        return v


class MCPAuthConfig(BaseModel):
    """
    OAuth 2.1 authentication configuration with RFC 8707 Resource Indicators.
    
    Implements 2025 MCP security requirements including scoped authentication,
    consent management, and audit logging configuration.
    """
    
    # OAuth 2.1 core settings
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    authorization_server_url: str = Field(..., description="Authorization server URL")
    
    # RFC 8707 Resource Indicators
    resource_indicator: str = Field("urn:docaiche:mcp", description="Resource indicator")
    default_scope: str = Field("read", description="Default access scope")
    
    # Token configuration
    access_token_ttl: int = Field(3600, description="Access token TTL in seconds")
    refresh_token_ttl: int = Field(86400, description="Refresh token TTL in seconds")
    
    # Security settings
    require_pkce: bool = Field(True, description="Require PKCE for authorization")
    require_consent: bool = Field(True, description="Require explicit user consent")
    
    # Consent management
    consent_ttl: int = Field(3600, description="Consent validity in seconds")
    consent_storage_backend: str = Field("redis", description="Consent storage backend")
    
    @validator('access_token_ttl', 'refresh_token_ttl', 'consent_ttl')
    def validate_ttl(cls, v):
        """Validate TTL values."""
        if v < 60 or v > 604800:  # 1 minute to 1 week
            raise ValueError("TTL must be between 60 and 604800 seconds")
        return v


class MCPSecurityConfig(BaseModel):
    """
    Comprehensive security configuration for MCP operations.
    
    Implements security controls, audit logging, rate limiting,
    and threat mitigation according to 2025 security best practices.
    """
    
    # Security enforcement level
    security_level: SecurityLevel = Field(SecurityLevel.PRODUCTION, description="Security enforcement level")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    default_rate_limit: str = Field("100/minute", description="Default rate limit")
    
    # Tool-specific rate limits
    search_rate_limit: str = Field("30/minute", description="Search tool rate limit")
    ingest_rate_limit: str = Field("10/minute", description="Ingest tool rate limit")
    feedback_rate_limit: str = Field("20/minute", description="Feedback tool rate limit")
    
    # Input validation
    max_query_length: int = Field(500, description="Maximum search query length")
    max_feedback_length: int = Field(1000, description="Maximum feedback comment length")
    allowed_source_domains: List[str] = Field(default=[], description="Allowed ingestion domains")
    
    # Audit logging
    audit_enabled: bool = Field(True, description="Enable audit logging")
    audit_backend: str = Field("loki", description="Audit logging backend")
    audit_retention_days: int = Field(90, description="Audit log retention in days")
    
    # Content security
    content_filtering_enabled: bool = Field(True, description="Enable content filtering")
    malware_scanning_enabled: bool = Field(True, description="Enable malware scanning")
    
    @validator('audit_retention_days')
    def validate_retention(cls, v):
        """Validate audit retention period."""
        if v < 1 or v > 2555:  # 1 day to 7 years
            raise ValueError("Audit retention must be between 1 and 2555 days")
        return v


class MCPIntegrationConfig(BaseModel):
    """
    Integration configuration with existing DocaiChe services.
    
    Configures connections to DocaiChe APIs, databases, and external
    services required for MCP tool and resource operations.
    """
    
    # DocaiChe API integration
    docaiche_api_url: str = Field("http://localhost:8000", description="DocaiChe API base URL")
    docaiche_api_key: Optional[str] = Field(None, description="DocaiChe API key")
    docaiche_api_timeout: int = Field(30, description="API request timeout")
    
    # Database connections
    database_url: str = Field("sqlite:///data/mcp.db", description="MCP database URL")
    redis_url: str = Field("redis://localhost:6379/1", description="Redis cache URL")
    
    # External service integrations
    anythingllm_url: str = Field("http://localhost:3001", description="AnythingLLM API URL")
    anythingllm_api_key: Optional[str] = Field(None, description="AnythingLLM API key")
    
    # LLM provider configuration
    llm_provider: str = Field("openai", description="Primary LLM provider")
    llm_model: str = Field("gpt-4", description="Default LLM model")
    llm_timeout: int = Field(60, description="LLM request timeout")
    
    @validator('docaiche_api_timeout', 'llm_timeout')
    def validate_timeout(cls, v):
        """Validate timeout values."""
        if v < 5 or v > 300:
            raise ValueError("Timeout must be between 5 and 300 seconds")
        return v


class MCPConfig(BaseModel):
    """
    Complete MCP server configuration.
    
    Aggregates all configuration sections with proper validation,
    environment variable integration, and security considerations.
    """
    
    # Basic server settings
    server_name: str = Field("docaiche-mcp", description="MCP server name")
    server_version: str = Field("1.0.0", description="MCP server version")
    environment: str = Field("production", description="Deployment environment")
    
    # Logging configuration
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    log_format: str = Field("json", description="Log format (json|text)")
    
    # Configuration sections
    transport: MCPTransportConfig = Field(default_factory=MCPTransportConfig)
    auth: MCPAuthConfig
    security: MCPSecurityConfig = Field(default_factory=MCPSecurityConfig)
    integration: MCPIntegrationConfig = Field(default_factory=MCPIntegrationConfig)
    
    # Feature flags
    enable_intelligent_discovery: bool = Field(True, description="Enable intelligent content discovery")
    enable_background_ingestion: bool = Field(True, description="Enable background content ingestion")
    enable_analytics: bool = Field(True, description="Enable usage analytics")
    
    class Config:
        env_prefix = "MCP_"
        extra = "forbid"
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ["development", "testing", "staging", "production"]:
            raise ValueError("Environment must be one of: development, testing, staging, production")
        return v


def load_config_from_env() -> MCPConfig:
    """
    Load MCP configuration from environment variables.
    
    Implements hierarchical configuration loading with proper defaults,
    validation, and security considerations for production deployment.
    
    Returns:
        Validated MCP configuration object
        
    Raises:
        ConfigurationError: If configuration is invalid or incomplete
    """
    try:
        # Required OAuth configuration
        auth_config = MCPAuthConfig(
            client_id=os.getenv("MCP_CLIENT_ID", "docaiche-mcp-client"),
            client_secret=os.getenv("MCP_CLIENT_SECRET", "changeme-in-production"),
            authorization_server_url=os.getenv("MCP_AUTH_SERVER_URL", "http://localhost:8000/auth"),
            resource_indicator=os.getenv("MCP_RESOURCE_INDICATOR", "urn:docaiche:mcp"),
            default_scope=os.getenv("MCP_DEFAULT_SCOPE", "read"),
        )
        
        # Transport configuration with environment overrides
        transport_config = MCPTransportConfig(
            transport_type=os.getenv("MCP_TRANSPORT_TYPE", "streamable-http"),
            bind_host=os.getenv("MCP_BIND_HOST", "0.0.0.0"),
            bind_port=int(os.getenv("MCP_BIND_PORT", "8001")),
            max_connections=int(os.getenv("MCP_MAX_CONNECTIONS", "100")),
        )
        
        # Security configuration
        security_config = MCPSecurityConfig(
            security_level=SecurityLevel(os.getenv("MCP_SECURITY_LEVEL", "production")),
            rate_limit_enabled=os.getenv("MCP_RATE_LIMIT_ENABLED", "true").lower() == "true",
            audit_enabled=os.getenv("MCP_AUDIT_ENABLED", "true").lower() == "true",
        )
        
        # Integration configuration
        integration_config = MCPIntegrationConfig(
            docaiche_api_url=os.getenv("DOCAICHE_API_URL", "http://localhost:8000"),
            docaiche_api_key=os.getenv("DOCAICHE_API_KEY"),
            database_url=os.getenv("MCP_DATABASE_URL", "sqlite:///data/mcp.db"),
            redis_url=os.getenv("MCP_REDIS_URL", "redis://localhost:6379/1"),
            anythingllm_url=os.getenv("ANYTHINGLLM_URL", "http://localhost:3001"),
            anythingllm_api_key=os.getenv("ANYTHINGLLM_API_KEY"),
        )
        
        # Create complete configuration
        config = MCPConfig(
            server_name=os.getenv("MCP_SERVER_NAME", "docaiche-mcp"),
            server_version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
            environment=os.getenv("MCP_ENVIRONMENT", "production"),
            log_level=LogLevel(os.getenv("MCP_LOG_LEVEL", "INFO")),
            auth=auth_config,
            transport=transport_config,
            security=security_config,
            integration=integration_config,
            enable_intelligent_discovery=os.getenv("MCP_ENABLE_INTELLIGENT_DISCOVERY", "true").lower() == "true",
            enable_background_ingestion=os.getenv("MCP_ENABLE_BACKGROUND_INGESTION", "true").lower() == "true",
            enable_analytics=os.getenv("MCP_ENABLE_ANALYTICS", "true").lower() == "true",
        )
        
        logger.info(
            f"MCP configuration loaded successfully",
            extra={
                "server_name": config.server_name,
                "environment": config.environment,
                "transport_type": config.transport.transport_type,
                "security_level": config.security.security_level,
            }
        )
        
        return config
        
    except Exception as e:
        from .exceptions import ConfigurationError
        logger.error(f"Failed to load MCP configuration: {str(e)}")
        raise ConfigurationError(
            message=f"Configuration loading failed: {str(e)}",
            error_code="CONFIG_LOAD_FAILED",
            details={"error": str(e)}
        )


def validate_production_config(config: MCPConfig) -> None:
    """
    Validate configuration for production deployment.
    
    Ensures all security requirements are met and configuration
    is appropriate for production use.
    
    Args:
        config: MCP configuration to validate
        
    Raises:
        ConfigurationError: If configuration is not production-ready
    """
    errors = []
    
    # Security validation
    if config.environment == "production":
        if config.auth.client_secret == "changeme-in-production":
            errors.append("Client secret must be changed in production")
            
        if config.security.security_level != SecurityLevel.PRODUCTION:
            errors.append("Security level must be 'production' in production environment")
            
        if not config.security.audit_enabled:
            errors.append("Audit logging must be enabled in production")
            
        if not config.security.rate_limit_enabled:
            errors.append("Rate limiting must be enabled in production")
    
    # Network security validation
    if config.transport.bind_host == "0.0.0.0" and config.environment == "production":
        logger.warning("Binding to 0.0.0.0 in production - ensure proper firewall configuration")
    
    # Integration validation
    if not config.integration.docaiche_api_url:
        errors.append("DocaiChe API URL is required")
    
    if errors:
        from .exceptions import ConfigurationError
        raise ConfigurationError(
            message="Production configuration validation failed",
            error_code="INVALID_PRODUCTION_CONFIG",
            details={"validation_errors": errors}
        )
    
    logger.info("Production configuration validation passed")


# TODO: IMPLEMENTATION ENGINEER - Add configuration sections for:
# 1. Monitoring and observability settings (metrics, tracing)
# 2. Performance tuning parameters (connection pools, timeouts)
# 3. Feature flag management and gradual rollout
# 4. External service circuit breaker configuration
# 5. Content ingestion and processing pipeline settings

def get_config() -> MCPConfig:
    """
    Get validated MCP configuration.
    
    Returns cached configuration instance or loads from environment
    with proper validation for the deployment environment.
    
    Returns:
        Validated MCP configuration
    """
    # In production, implement configuration caching
    config = load_config_from_env()
    
    # Validate production requirements
    if config.environment in ["production", "staging"]:
        validate_production_config(config)
    
    return config


# Additional configuration class for server compatibility
@dataclass
class MCPServerConfig:
    """
    MCP server configuration for compatibility with server.py.
    
    This class provides a simpler interface that matches what the
    server implementation expects.
    """
    
    # Server identification
    server_name: str = "DocaiChe MCP Server"
    server_id: str = "docaiche-mcp-001"
    
    # Transport configuration
    transport_config: MCPTransportConfig = field(default_factory=MCPTransportConfig)
    
    # Security settings
    require_authentication: bool = True
    require_explicit_consent: bool = True
    default_permissions: Set[str] = field(default_factory=lambda: {
        "search:public",
        "resources:read:public", 
        "status:read"
    })
    
    # OAuth configuration
    oauth_client_id: str = "docaiche-mcp-client"
    oauth_client_secret: str = ""
    oauth_auth_endpoint: str = "https://auth.docaiche.com/authorize"
    oauth_token_endpoint: str = "https://auth.docaiche.com/token"
    oauth_introspection_endpoint: str = "https://auth.docaiche.com/introspect"
    oauth_revocation_endpoint: str = "https://auth.docaiche.com/revoke"
    
    # Audit settings
    audit_log_file: str = "logs/mcp_audit.log"
    audit_log_max_size: int = 104857600  # 100MB
    audit_log_retention_days: int = 90
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    
    # Service endpoints
    services: Dict[str, str] = field(default_factory=lambda: {
        "search_service_url": "http://localhost:8000/api/v1/search",
        "ingestion_service_url": "http://localhost:8000/api/v1/ingest",
        "documentation_service_url": "http://localhost:8000/api/v1/docs",
        "collections_service_url": "http://localhost:8000/api/v1/collections",
        "health_service_url": "http://localhost:8000/api/v1/health",
        "feedback_service_url": "http://localhost:8000/api/v1/feedback"
    })
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size_mb: int = 512
    
    # Development settings
    development_mode: bool = False
    enable_debug_endpoints: bool = False
    allow_insecure_transport: bool = False
    
    @classmethod
    def from_mcp_config(cls, config: MCPConfig) -> 'MCPServerConfig':
        """Create MCPServerConfig from MCPConfig."""
        return cls(
            server_name=config.server_name,
            transport_config=config.transport,
            require_authentication=config.security.security_level == SecurityLevel.PRODUCTION,
            require_explicit_consent=config.auth.require_consent,
            oauth_client_id=config.auth.client_id,
            oauth_client_secret=config.auth.client_secret,
            oauth_auth_endpoint=f"{config.auth.authorization_server_url}/authorize",
            oauth_token_endpoint=f"{config.auth.authorization_server_url}/token",
            oauth_introspection_endpoint=f"{config.auth.authorization_server_url}/introspect",
            oauth_revocation_endpoint=f"{config.auth.authorization_server_url}/revoke",
            audit_log_file=config.security.audit_backend,
            rate_limit_enabled=config.security.rate_limit_enabled,
            development_mode=config.environment == "development"
        )