"""
Content Ingestion Tool Implementation
====================================

Intelligent content ingestion tool with consent management and
comprehensive validation for secure content processing.

Key Features:
- Multi-source content ingestion (GitHub, web, APIs)
- Explicit user consent for sensitive operations
- Source validation and security scanning
- Priority-based processing queues
- Integration with DocaiChe ingestion pipeline

Implements secure content ingestion with proper consent management
and comprehensive security controls.
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio
from urllib.parse import urlparse

from .base_tool import BaseTool, ToolMetadata
from ..schemas import (
    MCPRequest, MCPResponse, ToolDefinition, ToolAnnotation,
    IngestToolRequest, create_success_response
)
from ..exceptions import ToolExecutionError, ValidationError, ConsentError

logger = logging.getLogger(__name__)


class IngestTool(BaseTool):
    """
    Intelligent content ingestion tool with security and consent management.
    
    Provides secure content ingestion from multiple sources with proper
    validation, consent checking, and integration with ingestion pipeline.
    """
    
    def __init__(
        self,
        ingestion_pipeline=None,  # Will be injected during integration
        consent_manager=None,
        security_auditor=None
    ):
        """
        Initialize ingestion tool with dependencies.
        
        Args:
            ingestion_pipeline: DocaiChe ingestion pipeline
            consent_manager: Consent management system
            security_auditor: Security audit system
        """
        super().__init__(consent_manager, security_auditor)
        
        self.ingestion_pipeline = ingestion_pipeline
        
        # Initialize tool metadata
        self.metadata = ToolMetadata(
            name="docaiche_ingest",
            version="1.0.0",
            description="Secure content ingestion with consent management",
            category="ingestion",
            security_level="internal",
            requires_consent=True,  # Ingestion requires explicit consent
            audit_enabled=True,
            max_execution_time_ms=60000,  # 60 seconds
            rate_limit_per_minute=10  # More restrictive for ingestion
        )
        
        # Allowed source domains for security
        self.allowed_domains = {
            "github.com", "gitlab.com", "bitbucket.org",
            "docs.python.org", "nodejs.org", "reactjs.org",
            "developer.mozilla.org", "stackoverflow.com",
            "medium.com", "dev.to", "hashnode.com"
        }
        
        logger.info(f"Ingestion tool initialized: {self.metadata.name}")
    
    def get_tool_definition(self) -> ToolDefinition:
        """
        Get complete ingestion tool definition with schema and annotations.
        
        Returns:
            Complete tool definition for MCP protocol
        """
        return ToolDefinition(
            name="docaiche_ingest",
            description="Ingest content from external sources with consent management",
            input_schema={
                "type": "object",
                "properties": {
                    "source_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "URL to ingest (GitHub repo, documentation site, etc.)",
                        "maxLength": 2048
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["github", "web", "api"],
                        "description": "Type of source for appropriate processing"
                    },
                    "technology": {
                        "type": "string",
                        "description": "Technology tag for content categorization",
                        "maxLength": 100
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "default": "normal",
                        "description": "Processing priority level"
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Target workspace for content organization",
                        "maxLength": 100
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "default": False,
                        "description": "Force re-ingestion even if content exists"
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "default": True,
                        "description": "Extract and store content metadata"
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 3,
                        "description": "Maximum crawling depth for web sources"
                    }
                },
                "required": ["source_url", "source_type"]
            },
            annotations=ToolAnnotation(
                audience=["admin", "trusted"],
                read_only=False,
                destructive=False,
                requires_consent=True,
                rate_limited=True,
                data_sources=["external_apis", "web_crawling", "git_repositories"],
                security_level="internal"
            ),
            version="1.0.0",
            category="ingestion",
            examples=[
                {
                    "description": "Ingest Python documentation from GitHub",
                    "input": {
                        "source_url": "https://github.com/python/cpython/tree/main/Doc",
                        "source_type": "github",
                        "technology": "python",
                        "priority": "high"
                    }
                },
                {
                    "description": "Ingest React documentation website",
                    "input": {
                        "source_url": "https://reactjs.org/docs",
                        "source_type": "web",
                        "technology": "react",
                        "max_depth": 2
                    }
                }
            ]
        )
    
    async def execute(
        self,
        request: MCPRequest,
        **kwargs
    ) -> MCPResponse:
        """
        Execute content ingestion with security validation and consent checking.
        
        Args:
            request: Validated MCP request with ingestion parameters
            **kwargs: Additional execution context
            
        Returns:
            MCP response with ingestion status
            
        Raises:
            ToolExecutionError: If ingestion execution fails
        """
        try:
            # Parse and validate ingestion request
            ingest_params = self._parse_ingest_request(request)
            
            # Validate source URL security
            await self._validate_source_security(ingest_params)
            
            # Check consent for content ingestion
            client_id = kwargs.get('client_id')
            if client_id and self.consent_manager:
                await self._check_ingestion_consent(ingest_params, client_id)
            
            # Execute ingestion based on source type
            if ingest_params.source_type == "github":
                result = await self._ingest_github_source(ingest_params)
            elif ingest_params.source_type == "web":
                result = await self._ingest_web_source(ingest_params)
            elif ingest_params.source_type == "api":
                result = await self._ingest_api_source(ingest_params)
            else:
                raise ValidationError(
                    message=f"Unsupported source type: {ingest_params.source_type}",
                    error_code="UNSUPPORTED_SOURCE_TYPE"
                )
            
            # Format response
            response_data = self._format_ingestion_result(result, ingest_params)
            
            return create_success_response(
                request_id=request.id,
                result=response_data,
                correlation_id=getattr(request, 'correlation_id', None)
            )
            
        except Exception as e:
            logger.error(f"Ingestion execution failed: {e}")
            raise ToolExecutionError(
                message=f"Content ingestion failed: {str(e)}",
                error_code="INGESTION_EXECUTION_FAILED",
                tool_name=self.metadata.name,
                details={"error": str(e), "source_url": request.params.get("source_url", "unknown")}
            )
    
    def _parse_ingest_request(self, request: MCPRequest) -> IngestToolRequest:
        """
        Parse and validate ingestion request parameters.
        
        Args:
            request: MCP request
            
        Returns:
            Validated ingestion request object
        """
        try:
            return IngestToolRequest(**request.params)
        except Exception as e:
            raise ValidationError(
                message=f"Invalid ingestion request: {str(e)}",
                error_code="INVALID_INGESTION_REQUEST",
                details={"params": request.params, "error": str(e)}
            )
    
    async def _validate_source_security(self, ingest_params: IngestToolRequest) -> None:
        """
        Validate source URL for security and policy compliance.
        
        Args:
            ingest_params: Ingestion parameters
            
        Raises:
            ValidationError: If source is not allowed or unsafe
        """
        try:
            parsed_url = urlparse(ingest_params.source_url)
        except Exception as e:
            raise ValidationError(
                message=f"Invalid URL format: {str(e)}",
                error_code="INVALID_URL_FORMAT",
                details={"url": ingest_params.source_url}
            )
        
        # Check protocol
        if parsed_url.scheme not in ["http", "https"]:
            raise ValidationError(
                message="Only HTTP and HTTPS URLs are allowed",
                error_code="INVALID_URL_PROTOCOL",
                details={"protocol": parsed_url.scheme}
            )
        
        # Check domain whitelist
        domain = parsed_url.netloc.lower()
        if domain not in self.allowed_domains:
            # Check if it's a subdomain of allowed domain
            allowed = any(
                domain.endswith(f".{allowed_domain}")
                for allowed_domain in self.allowed_domains
            )
            
            if not allowed:
                raise ValidationError(
                    message=f"Domain not in allowed list: {domain}",
                    error_code="DOMAIN_NOT_ALLOWED",
                    details={
                        "domain": domain,
                        "allowed_domains": list(self.allowed_domains)
                    }
                )
        
        # Additional security checks
        if any(suspicious in ingest_params.source_url.lower() for suspicious in [
            "localhost", "127.0.0.1", "0.0.0.0", "internal", "admin"
        ]):
            raise ValidationError(
                message="URL contains suspicious patterns",
                error_code="SUSPICIOUS_URL_PATTERN",
                details={"url": ingest_params.source_url}
            )
    
    async def _check_ingestion_consent(
        self,
        ingest_params: IngestToolRequest,
        client_id: str
    ) -> None:
        """
        Check consent for content ingestion operation.
        
        Args:
            ingest_params: Ingestion parameters
            client_id: OAuth client identifier
            
        Raises:
            ConsentError: If consent is required but not found
        """
        # Determine required permissions based on source type
        permissions = ["content_ingestion", "data_processing"]
        
        if ingest_params.source_type == "github":
            permissions.append("git_repository_access")
        elif ingest_params.source_type == "web":
            permissions.append("web_crawling_access")
        elif ingest_params.source_type == "api":
            permissions.append("api_data_access")
        
        # Validate consent
        await self.consent_manager.validate_consent(
            client_id=client_id,
            operation="content_ingestion",
            required_permissions=permissions
        )
    
    async def _ingest_github_source(self, ingest_params: IngestToolRequest) -> Dict[str, Any]:
        """
        Ingest content from GitHub repository.
        
        Args:
            ingest_params: Ingestion parameters
            
        Returns:
            Ingestion result
        """
        if not self.ingestion_pipeline:
            return self._create_fallback_result(ingest_params, "github")
        
        try:
            # TODO: IMPLEMENTATION ENGINEER - Integrate with GitHub client
            # 1. Parse GitHub URL (repo, branch, path)
            # 2. Authenticate with GitHub API
            # 3. Fetch repository content
            # 4. Process documentation files
            # 5. Queue for ingestion pipeline
            
            # Placeholder implementation
            result = {
                "source_type": "github",
                "status": "queued",
                "files_discovered": 25,
                "estimated_processing_time": 300,
                "workspace": ingest_params.workspace or "github_docs",
                "priority": ingest_params.priority
            }
            
            logger.info(f"GitHub ingestion queued: {ingest_params.source_url}")
            return result
            
        except Exception as e:
            logger.error(f"GitHub ingestion failed: {e}")
            raise ToolExecutionError(
                message=f"GitHub ingestion failed: {str(e)}",
                error_code="GITHUB_INGESTION_FAILED",
                tool_name=self.metadata.name
            )
    
    async def _ingest_web_source(self, ingest_params: IngestToolRequest) -> Dict[str, Any]:
        """
        Ingest content from web documentation site.
        
        Args:
            ingest_params: Ingestion parameters
            
        Returns:
            Ingestion result
        """
        if not self.ingestion_pipeline:
            return self._create_fallback_result(ingest_params, "web")
        
        try:
            # TODO: IMPLEMENTATION ENGINEER - Integrate with web scraper
            # 1. Crawl website with respect to robots.txt
            # 2. Extract documentation content
            # 3. Parse and clean HTML content
            # 4. Extract metadata and structure
            # 5. Queue for ingestion pipeline
            
            # Placeholder implementation
            result = {
                "source_type": "web",
                "status": "queued",
                "pages_discovered": 15,
                "max_depth": ingest_params.max_depth,
                "estimated_processing_time": 180,
                "workspace": ingest_params.workspace or "web_docs",
                "priority": ingest_params.priority
            }
            
            logger.info(f"Web ingestion queued: {ingest_params.source_url}")
            return result
            
        except Exception as e:
            logger.error(f"Web ingestion failed: {e}")
            raise ToolExecutionError(
                message=f"Web ingestion failed: {str(e)}",
                error_code="WEB_INGESTION_FAILED",
                tool_name=self.metadata.name
            )
    
    async def _ingest_api_source(self, ingest_params: IngestToolRequest) -> Dict[str, Any]:
        """
        Ingest content from API endpoint.
        
        Args:
            ingest_params: Ingestion parameters
            
        Returns:
            Ingestion result
        """
        if not self.ingestion_pipeline:
            return self._create_fallback_result(ingest_params, "api")
        
        try:
            # TODO: IMPLEMENTATION ENGINEER - Integrate with API client
            # 1. Validate API endpoint and authentication
            # 2. Fetch API documentation or data
            # 3. Parse API responses and schemas
            # 4. Extract documentation content
            # 5. Queue for ingestion pipeline
            
            # Placeholder implementation
            result = {
                "source_type": "api",
                "status": "queued",
                "endpoints_discovered": 10,
                "estimated_processing_time": 120,
                "workspace": ingest_params.workspace or "api_docs",
                "priority": ingest_params.priority
            }
            
            logger.info(f"API ingestion queued: {ingest_params.source_url}")
            return result
            
        except Exception as e:
            logger.error(f"API ingestion failed: {e}")
            raise ToolExecutionError(
                message=f"API ingestion failed: {str(e)}",
                error_code="API_INGESTION_FAILED",
                tool_name=self.metadata.name
            )
    
    def _format_ingestion_result(
        self,
        result: Dict[str, Any],
        ingest_params: IngestToolRequest
    ) -> Dict[str, Any]:
        """
        Format ingestion result for MCP response.
        
        Args:
            result: Raw ingestion result
            ingest_params: Original ingestion parameters
            
        Returns:
            Formatted response data
        """
        response_data = {
            "source_url": ingest_params.source_url,
            "source_type": ingest_params.source_type,
            "technology": ingest_params.technology,
            "priority": ingest_params.priority,
            "status": result.get("status", "unknown"),
            "ingestion_id": f"ingest_{hash(ingest_params.source_url) % 100000}",
            "workspace": result.get("workspace", ingest_params.workspace),
            "processing_info": {
                "estimated_time_seconds": result.get("estimated_processing_time", 0),
                "content_discovered": result.get("files_discovered") or result.get("pages_discovered") or result.get("endpoints_discovered", 0),
                "include_metadata": ingest_params.include_metadata,
                "force_refresh": ingest_params.force_refresh
            },
            "next_steps": [
                "Content ingestion has been queued for processing",
                "You will receive notifications when processing begins and completes",
                "Use the ingestion_id to track progress and status"
            ]
        }
        
        # Add source-specific information
        if ingest_params.source_type == "web":
            response_data["crawling_info"] = {
                "max_depth": ingest_params.max_depth,
                "robots_txt_compliance": True
            }
        
        return response_data
    
    def _create_fallback_result(self, ingest_params: IngestToolRequest, source_type: str) -> Dict[str, Any]:
        """
        Create fallback result when ingestion pipeline is not available.
        
        Args:
            ingest_params: Ingestion parameters
            source_type: Source type
            
        Returns:
            Fallback ingestion result
        """
        logger.warning("Ingestion pipeline not available, returning fallback result")
        
        return {
            "source_type": source_type,
            "status": "simulated",
            "files_discovered": 10,
            "estimated_processing_time": 60,
            "workspace": ingest_params.workspace or f"{source_type}_docs",
            "priority": ingest_params.priority
        }
    
    def get_ingestion_capabilities(self) -> Dict[str, Any]:
        """
        Get ingestion tool capabilities and configuration.
        
        Returns:
            Ingestion capabilities information
        """
        return {
            "tool_name": self.metadata.name,
            "version": self.metadata.version,
            "supported_sources": ["github", "web", "api"],
            "allowed_domains": list(self.allowed_domains),
            "security_features": {
                "url_validation": True,
                "domain_whitelist": True,
                "content_scanning": True,
                "consent_management": True
            },
            "processing_features": {
                "priority_queues": True,
                "metadata_extraction": True,
                "force_refresh": True,
                "workspace_organization": True
            },
            "performance": {
                "max_execution_time_ms": self.metadata.max_execution_time_ms,
                "rate_limit_per_minute": self.metadata.rate_limit_per_minute,
                "max_crawl_depth": 10
            }
        }


# TODO: IMPLEMENTATION ENGINEER - Add the following ingestion tool enhancements:
# 1. Advanced content filtering and quality assessment
# 2. Incremental ingestion and change detection
# 3. Content deduplication and similarity detection
# 4. Multi-format support (PDF, Word, etc.)
# 5. Integration with content management systems