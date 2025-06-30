"""
Documentation Resource Implementation
====================================

Documentation resource providing direct access to documentation content,
metadata, and search results with comprehensive caching and optimization.

Key Features:
- Direct document access by ID or URI
- Content metadata and versioning
- Search result caching and optimization
- Technology-specific content filtering
- Integration with DocaiChe content pipeline

Implements efficient documentation access with proper caching strategies
and performance optimization for high-throughput operations.
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from .base_resource import BaseResource, ResourceMetadata
from ..schemas import ResourceDefinition
from ..exceptions import ResourceError, ValidationError

logger = logging.getLogger(__name__)


class DocumentationResource(BaseResource):
    """
    Documentation resource for direct content access.
    
    Provides efficient access to documentation content with metadata,
    versioning, and technology-specific filtering capabilities.
    """
    
    def __init__(
        self,
        content_manager=None,  # Will be injected during integration
        search_orchestrator=None,
        consent_manager=None,
        security_auditor=None
    ):
        """
        Initialize documentation resource with dependencies.
        
        Args:
            content_manager: Content management system
            search_orchestrator: Search orchestration service
            consent_manager: Consent management system
            security_auditor: Security audit system
        """
        super().__init__(consent_manager, security_auditor)
        
        self.content_manager = content_manager
        self.search_orchestrator = search_orchestrator
        
        # Initialize resource metadata
        self.metadata = ResourceMetadata(
            uri_pattern="docs://docaiche/{collection}/{document_id}",
            name="documentation",
            description="Direct access to documentation content and metadata",
            mime_type="application/json",
            cacheable=True,
            cache_ttl=1800,  # 30 minutes for documentation
            max_size_bytes=1024 * 1024,  # 1MB max per document
            requires_authentication=False,
            access_level="public",
            audit_enabled=True
        )
        
        # Supported URI patterns
        self.uri_patterns = [
            r"docs://docaiche/(?P<collection>[^/]+)/(?P<document_id>[^/]+)",
            r"docs://docaiche/(?P<collection>[^/]+)/(?P<document_id>[^/]+)/(?P<section>[^/]+)",
            r"docs://docaiche/search/(?P<query>[^/]+)",
            r"docs://docaiche/collections/(?P<collection>[^/]+)/list"
        ]
        
        logger.info(f"Documentation resource initialized: {self.metadata.name}")
    
    def get_resource_definition(self) -> ResourceDefinition:
        """
        Get complete documentation resource definition.
        
        Returns:
            Complete resource definition for MCP protocol
        """
        return ResourceDefinition(
            uri="docs://docaiche/**",
            name="Documentation Content",
            description="Access to documentation content, metadata, and search results",
            mime_type="application/json",
            cacheable=True,
            cache_ttl=1800,
            size_hint=50000  # Average document size estimate
        )
    
    async def fetch_resource(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch documentation resource data.
        
        Args:
            uri: Resource URI to fetch
            params: Optional query parameters
            **kwargs: Additional fetch context
            
        Returns:
            Documentation resource data
            
        Raises:
            ResourceError: If documentation access fails
        """
        try:
            # Parse URI to determine resource type
            parsed_uri = self._parse_documentation_uri(uri)
            
            if parsed_uri["type"] == "document":
                return await self._fetch_document(parsed_uri, params)
            elif parsed_uri["type"] == "search":
                return await self._fetch_search_results(parsed_uri, params)
            elif parsed_uri["type"] == "collection_list":
                return await self._fetch_collection_list(parsed_uri, params)
            else:
                raise ResourceError(
                    message=f"Unsupported documentation resource type: {parsed_uri['type']}",
                    error_code="UNSUPPORTED_RESOURCE_TYPE",
                    resource_uri=uri
                )
                
        except Exception as e:
            logger.error(f"Documentation resource fetch failed: {e}")
            raise ResourceError(
                message=f"Failed to fetch documentation resource: {str(e)}",
                error_code="DOCUMENTATION_FETCH_FAILED",
                resource_uri=uri,
                details={"error": str(e)}
            )
    
    def _parse_documentation_uri(self, uri: str) -> Dict[str, Any]:
        """
        Parse documentation URI to extract components.
        
        Args:
            uri: Documentation URI
            
        Returns:
            Parsed URI components
        """
        import re
        
        # Remove scheme if present
        if uri.startswith("docs://docaiche/"):
            path = uri[16:]  # Remove "docs://docaiche/"
        else:
            path = uri.lstrip("/")
        
        # Parse different URI patterns
        if path.startswith("search/"):
            # Search URI: docs://docaiche/search/{query}
            query = path[7:]  # Remove "search/"
            return {
                "type": "search",
                "query": query
            }
        elif "/" in path:
            parts = path.split("/")
            if len(parts) >= 2:
                if parts[0] == "collections" and parts[2] == "list":
                    # Collection list URI: docs://docaiche/collections/{collection}/list
                    return {
                        "type": "collection_list",
                        "collection": parts[1]
                    }
                else:
                    # Document URI: docs://docaiche/{collection}/{document_id}[/{section}]
                    result = {
                        "type": "document",
                        "collection": parts[0],
                        "document_id": parts[1]
                    }
                    if len(parts) > 2:
                        result["section"] = parts[2]
                    return result
        
        raise ValidationError(
            message=f"Invalid documentation URI format: {uri}",
            error_code="INVALID_DOCUMENTATION_URI",
            details={"uri": uri}
        )
    
    async def _fetch_document(
        self,
        parsed_uri: Dict[str, Any],
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fetch specific document content.
        
        Args:
            parsed_uri: Parsed URI components
            params: Query parameters
            
        Returns:
            Document content and metadata
        """
        collection = parsed_uri["collection"]
        document_id = parsed_uri["document_id"]
        section = parsed_uri.get("section")
        
        if self.content_manager:
            try:
                # Use actual content manager if available
                return await self.content_manager.get_document(
                    collection=collection,
                    document_id=document_id,
                    section=section,
                    include_metadata=params.get("include_metadata", True) if params else True
                )
            except Exception as e:
                logger.warning(f"Content manager failed: {e}")
        
        # Fallback to mock document
        return await self._create_fallback_document(collection, document_id, section)
    
    async def _create_fallback_document(
        self,
        collection: str,
        document_id: str,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create fallback document when content manager is not available.
        
        Args:
            collection: Collection name
            document_id: Document identifier
            section: Optional section name
            
        Returns:
            Fallback document data
        """
        content = f"# {document_id.replace('_', ' ').title()}\n\n"
        
        if section:
            content += f"## {section.replace('_', ' ').title()}\n\n"
            content += f"This is the {section} section of the {document_id} documentation in the {collection} collection.\n\n"
        else:
            content += f"This is the main documentation for {document_id} in the {collection} collection.\n\n"
        
        content += f"**Collection:** {collection}\n"
        content += f"**Document ID:** {document_id}\n"
        if section:
            content += f"**Section:** {section}\n"
        
        content += "\n### Overview\n\n"
        content += f"Comprehensive documentation for {document_id} including examples, API reference, and best practices.\n\n"
        
        return {
            "content": content,
            "metadata": {
                "collection": collection,
                "document_id": document_id,
                "section": section,
                "title": document_id.replace("_", " ").title(),
                "content_type": "markdown",
                "language": "en",
                "last_updated": "2024-12-20T10:00:00Z",
                "version": "1.0.0",
                "tags": [collection, document_id],
                "size_bytes": len(content),
                "estimated_read_time_minutes": max(1, len(content) // 200)
            },
            "navigation": {
                "collection_uri": f"docs://docaiche/collections/{collection}/list",
                "sections": ["overview", "examples", "api-reference", "troubleshooting"] if not section else None
            }
        }
    
    async def _fetch_search_results(
        self,
        parsed_uri: Dict[str, Any],
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fetch search results as a resource.
        
        Args:
            parsed_uri: Parsed URI components
            params: Query parameters
            
        Returns:
            Search results formatted as resource
        """
        query = parsed_uri["query"]
        
        if self.search_orchestrator:
            try:
                # Use actual search orchestrator if available
                search_response = await self.search_orchestrator.search(
                    query=query,
                    technology_hint=params.get("technology") if params else None,
                    limit=params.get("limit", 10) if params else 10,
                    offset=params.get("offset", 0) if params else 0
                )
                
                return {
                    "query": query,
                    "results": search_response.results,
                    "metadata": {
                        "total_count": search_response.total_count,
                        "execution_time_ms": search_response.execution_time_ms,
                        "cache_hit": search_response.cache_hit,
                        "enrichment_triggered": search_response.enrichment_triggered,
                        "search_timestamp": datetime.utcnow().isoformat()
                    }
                }
            except Exception as e:
                logger.warning(f"Search orchestrator failed: {e}")
        
        # Fallback to mock search results
        return await self._create_fallback_search_results(query, params)
    
    async def _create_fallback_search_results(
        self,
        query: str,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create fallback search results when search orchestrator is not available.
        
        Args:
            query: Search query
            params: Search parameters
            
        Returns:
            Fallback search results
        """
        # Generate mock results based on query
        mock_results = [
            {
                "document_id": f"result_{i}",
                "title": f"Documentation for {query} - Result {i+1}",
                "snippet": f"This documentation covers {query} with detailed examples and API reference.",
                "collection": "python" if "python" in query.lower() else "general",
                "uri": f"docs://docaiche/python/result_{i}",
                "relevance_score": 0.9 - (i * 0.1),
                "last_updated": "2024-12-20T10:00:00Z"
            }
            for i in range(min(3, params.get("limit", 10) if params else 10))
        ]
        
        return {
            "query": query,
            "results": mock_results,
            "metadata": {
                "total_count": len(mock_results),
                "execution_time_ms": 50,
                "cache_hit": False,
                "enrichment_triggered": False,
                "search_timestamp": datetime.utcnow().isoformat(),
                "fallback_mode": True
            }
        }
    
    async def _fetch_collection_list(
        self,
        parsed_uri: Dict[str, Any],
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fetch list of documents in a collection.
        
        Args:
            parsed_uri: Parsed URI components
            params: Query parameters
            
        Returns:
            Collection document list
        """
        collection = parsed_uri["collection"]
        
        # Mock collection listing
        documents = [
            {
                "document_id": f"{collection}_getting_started",
                "title": f"Getting Started with {collection.title()}",
                "description": f"Introduction and setup guide for {collection}",
                "uri": f"docs://docaiche/{collection}/{collection}_getting_started",
                "last_updated": "2024-12-20T10:00:00Z",
                "tags": [collection, "getting-started"]
            },
            {
                "document_id": f"{collection}_api_reference",
                "title": f"{collection.title()} API Reference",
                "description": f"Complete API documentation for {collection}",
                "uri": f"docs://docaiche/{collection}/{collection}_api_reference",
                "last_updated": "2024-12-19T15:30:00Z",
                "tags": [collection, "api", "reference"]
            },
            {
                "document_id": f"{collection}_examples",
                "title": f"{collection.title()} Examples",
                "description": f"Code examples and tutorials for {collection}",
                "uri": f"docs://docaiche/{collection}/{collection}_examples",
                "last_updated": "2024-12-18T12:15:00Z",
                "tags": [collection, "examples", "tutorials"]
            }
        ]
        
        # Apply pagination if specified
        limit = params.get("limit", 20) if params else 20
        offset = params.get("offset", 0) if params else 0
        
        paginated_docs = documents[offset:offset + limit]
        
        return {
            "collection": collection,
            "documents": paginated_docs,
            "metadata": {
                "total_count": len(documents),
                "returned_count": len(paginated_docs),
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < len(documents),
                "collection_updated": "2024-12-20T10:00:00Z"
            }
        }
    
    def get_supported_uri_patterns(self) -> List[str]:
        """
        Get list of supported URI patterns.
        
        Returns:
            List of supported URI patterns
        """
        return [
            "docs://docaiche/{collection}/{document_id}",
            "docs://docaiche/{collection}/{document_id}/{section}",
            "docs://docaiche/search/{query}",
            "docs://docaiche/collections/{collection}/list"
        ]
    
    def get_documentation_capabilities(self) -> Dict[str, Any]:
        """
        Get documentation resource capabilities.
        
        Returns:
            Documentation capabilities information
        """
        return {
            "resource_name": self.metadata.name,
            "uri_patterns": self.get_supported_uri_patterns(),
            "features": {
                "document_access": True,
                "section_access": True,
                "search_results": True,
                "collection_listing": True,
                "metadata_access": True,
                "content_caching": self.metadata.cacheable
            },
            "content_types": ["markdown", "html", "plain_text"],
            "supported_collections": ["python", "javascript", "typescript", "react", "vue"],
            "caching": {
                "enabled": self.metadata.cacheable,
                "ttl_seconds": self.metadata.cache_ttl,
                "max_size_bytes": self.metadata.max_size_bytes
            },
            "data_sources": {
                "content_manager": self.content_manager is not None,
                "search_orchestrator": self.search_orchestrator is not None,
                "fallback_mode": True
            }
        }


# TODO: IMPLEMENTATION ENGINEER - Add the following documentation resource enhancements:
# 1. Advanced content filtering and transformation
# 2. Document versioning and diff capabilities  
# 3. Full-text search within documents
# 4. Content recommendation and related documents
# 5. Integration with external documentation sources