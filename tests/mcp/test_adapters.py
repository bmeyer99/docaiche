"""
Integration tests for MCP Adapters
==================================

Tests for adapter layer that bridges MCP tools/resources with
DocaiChe FastAPI endpoints.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.mcp.adapters.search_adapter import SearchAdapter
from src.mcp.adapters.collections_adapter import CollectionsAdapter
from src.mcp.adapters.ingest_adapter import IngestAdapter
from src.mcp.adapters.health_adapter import HealthAdapter
from src.mcp.schemas import MCPRequest, MCPResponse


class TestSearchAdapter:
    """Test search adapter functionality."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def search_adapter(self, mock_api_client):
        return SearchAdapter(api_client=mock_api_client)
    
    @pytest.mark.asyncio
    async def test_adapt_search_request(self, search_adapter):
        """Test adapting MCP search request to API format."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "query": "machine learning",
                "filters": {
                    "technology": ["pytorch", "tensorflow"],
                    "date_range": "last_30_days"
                },
                "limit": 20
            }
        )
        
        adapted = await search_adapter.adapt_request(mcp_request)
        
        assert adapted["query"] == "machine learning"
        assert adapted["technologies"] == ["pytorch", "tensorflow"]
        assert adapted["limit"] == 20
        assert "date_from" in adapted
    
    @pytest.mark.asyncio
    async def test_adapt_search_response(self, search_adapter):
        """Test adapting API search response to MCP format."""
        api_response = {
            "results": [
                {
                    "doc_id": "123",
                    "title": "PyTorch Tutorial",
                    "content": "Getting started with PyTorch...",
                    "url": "https://example.com/pytorch",
                    "technology": "pytorch",
                    "score": 0.95,
                    "highlights": ["PyTorch", "tutorial"]
                }
            ],
            "total": 1,
            "facets": {
                "technologies": {"pytorch": 10, "tensorflow": 5}
            }
        }
        
        adapted = await search_adapter.adapt_response(api_response)
        
        assert len(adapted["results"]) == 1
        assert adapted["results"][0]["id"] == "123"
        assert adapted["results"][0]["relevance_score"] == 0.95
        assert adapted["total_count"] == 1
        assert "pytorch" in adapted["facets"]["technology"]
    
    @pytest.mark.asyncio
    async def test_search_with_caching(self, search_adapter, mock_api_client):
        """Test search with caching behavior."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "query": "test query",
                "use_cache": True
            }
        )
        
        mock_api_client.post.return_value = {
            "results": [],
            "total": 0,
            "cached": True
        }
        
        response = await search_adapter.search(mcp_request)
        
        assert response.result["cached"] is True
        mock_api_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_adapter, mock_api_client):
        """Test search error handling."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        mock_api_client.post.side_effect = Exception("API Error")
        
        response = await search_adapter.search(mcp_request)
        
        assert response.error is not None
        assert "Search failed" in response.error["message"]


class TestCollectionsAdapter:
    """Test collections adapter functionality."""
    
    @pytest.fixture
    def mock_api_client(self):
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def collections_adapter(self, mock_api_client):
        return CollectionsAdapter(api_client=mock_api_client)
    
    @pytest.mark.asyncio
    async def test_list_collections(self, collections_adapter, mock_api_client):
        """Test listing all collections."""
        mock_api_client.get.return_value = {
            "workspaces": [
                {
                    "id": "ws1",
                    "name": "PyTorch Documentation",
                    "slug": "pytorch-docs",
                    "document_count": 150,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "ws2",
                    "name": "TensorFlow Guide",
                    "slug": "tensorflow-guide",
                    "document_count": 200,
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ]
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/list",
            params={}
        )
        
        response = await collections_adapter.list_collections(mcp_request)
        
        assert len(response.result["collections"]) == 2
        assert response.result["collections"][0]["name"] == "PyTorch Documentation"
        assert response.result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_get_collection_details(self, collections_adapter, mock_api_client):
        """Test getting collection details."""
        mock_api_client.get.return_value = {
            "workspace": {
                "id": "ws1",
                "name": "PyTorch Documentation",
                "slug": "pytorch-docs",
                "document_count": 150,
                "created_at": "2024-01-01T00:00:00Z",
                "settings": {
                    "chat_mode": "query",
                    "llm_model": "gpt-4"
                },
                "documents": [
                    {
                        "id": "doc1",
                        "title": "Getting Started",
                        "url": "https://example.com/start"
                    }
                ]
            }
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/read",
            params={"collection_id": "pytorch-docs"}
        )
        
        response = await collections_adapter.get_collection(mcp_request)
        
        assert response.result["id"] == "ws1"
        assert response.result["name"] == "PyTorch Documentation"
        assert len(response.result["metadata"]["recent_documents"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_within_collection(self, collections_adapter, mock_api_client):
        """Test searching within a specific collection."""
        mock_api_client.post.return_value = {
            "results": [
                {
                    "doc_id": "123",
                    "title": "PyTorch Tensors",
                    "content": "Understanding tensors...",
                    "score": 0.9
                }
            ],
            "total": 1
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/search",
            params={
                "collection_id": "pytorch-docs",
                "query": "tensors"
            }
        )
        
        response = await collections_adapter.search_collection(mcp_request)
        
        assert len(response.result["results"]) == 1
        assert response.result["results"][0]["title"] == "PyTorch Tensors"
        assert response.result["collection_id"] == "pytorch-docs"


class TestIngestAdapter:
    """Test ingest adapter functionality."""
    
    @pytest.fixture
    def mock_api_client(self):
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_consent_manager(self):
        manager = AsyncMock()
        manager.check_consent.return_value = True
        return manager
    
    @pytest.fixture
    def ingest_adapter(self, mock_api_client, mock_consent_manager):
        return IngestAdapter(
            api_client=mock_api_client,
            consent_manager=mock_consent_manager
        )
    
    @pytest.mark.asyncio
    async def test_ingest_url(self, ingest_adapter, mock_api_client):
        """Test ingesting content from URL."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "url": "https://example.com/doc.html",
                "metadata": {
                    "title": "Test Document",
                    "technology": "python"
                },
                "workspace": "python-docs"
            }
        )
        
        mock_api_client.post.return_value = {
            "document_id": "doc123",
            "status": "success",
            "chunks_created": 10
        }
        
        response = await ingest_adapter.ingest_url(mcp_request)
        
        assert response.result["document_id"] == "doc123"
        assert response.result["status"] == "ingested"
        assert response.result["chunks_created"] == 10
    
    @pytest.mark.asyncio
    async def test_ingest_with_consent_check(self, ingest_adapter, mock_consent_manager):
        """Test that consent is checked before ingestion."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "url": "https://example.com/doc.html",
                "user_id": "user123"
            }
        )
        
        # Consent denied
        mock_consent_manager.check_consent.return_value = False
        
        response = await ingest_adapter.ingest_url(mcp_request)
        
        assert response.error is not None
        assert "consent required" in response.error["message"].lower()
        mock_consent_manager.check_consent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_ingest_request(self, ingest_adapter):
        """Test ingest request validation."""
        # Valid request
        valid_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "url": "https://example.com/doc.html",
                "metadata": {"title": "Test"}
            }
        )
        
        errors = await ingest_adapter.validate_request(valid_request)
        assert len(errors) == 0
        
        # Invalid request - missing URL
        invalid_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"metadata": {"title": "Test"}}
        )
        
        errors = await ingest_adapter.validate_request(invalid_request)
        assert len(errors) > 0
        assert any("url" in error.lower() for error in errors)
    
    @pytest.mark.asyncio
    async def test_batch_ingest(self, ingest_adapter, mock_api_client):
        """Test batch content ingestion."""
        mcp_request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "urls": [
                    "https://example.com/doc1.html",
                    "https://example.com/doc2.html"
                ],
                "workspace": "test-workspace"
            }
        )
        
        mock_api_client.post.side_effect = [
            {"document_id": "doc1", "status": "success"},
            {"document_id": "doc2", "status": "success"}
        ]
        
        response = await ingest_adapter.batch_ingest(mcp_request)
        
        assert response.result["total_processed"] == 2
        assert response.result["successful"] == 2
        assert len(response.result["results"]) == 2


class TestHealthAdapter:
    """Test health adapter functionality."""
    
    @pytest.fixture
    def mock_api_client(self):
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def health_adapter(self, mock_api_client):
        return HealthAdapter(api_client=mock_api_client)
    
    @pytest.mark.asyncio
    async def test_health_check(self, health_adapter, mock_api_client):
        """Test system health check."""
        mock_api_client.get.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 3600,
            "components": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 5
                },
                "cache": {
                    "status": "healthy",
                    "response_time_ms": 1
                },
                "search": {
                    "status": "degraded",
                    "response_time_ms": 100,
                    "message": "High latency detected"
                }
            }
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/read",
            params={}
        )
        
        response = await health_adapter.check_health(mcp_request)
        
        assert response.result["status"] == "healthy"
        assert response.result["health_score"] < 100  # Due to degraded search
        assert "database" in response.result["components"]
    
    @pytest.mark.asyncio
    async def test_get_system_stats(self, health_adapter, mock_api_client):
        """Test retrieving system statistics."""
        mock_api_client.get.return_value = {
            "total_requests": 10000,
            "total_documents": 500,
            "total_searches": 2000,
            "active_users": 50,
            "cache_hit_rate": 0.85,
            "average_response_time": 45,
            "cpu_percent": 35.5,
            "memory_mb": 1024
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/read",
            params={"include_history": False}
        )
        
        response = await health_adapter.get_stats(mcp_request)
        
        assert response.result["current_stats"]["total_requests"] == 10000
        assert response.result["current_stats"]["cache_hit_rate"] == 0.85
        assert response.result["resource_usage"]["cpu_percent"] == 35.5
    
    @pytest.mark.asyncio
    async def test_get_analytics(self, health_adapter, mock_api_client):
        """Test retrieving analytics data."""
        mock_api_client.get.return_value = {
            "time_range": "7d",
            "metrics": {
                "requests": {
                    "data_points": [100, 150, 120, 180, 200, 190, 210],
                    "total": 1150,
                    "average": 164.3,
                    "trend": "increasing"
                }
            }
        }
        
        mcp_request = MCPRequest(
            id="test-123",
            method="resource/read",
            params={"time_range": "7d"}
        )
        
        response = await health_adapter.get_analytics(mcp_request)
        
        assert response.result["time_range"] == "7d"
        assert "requests" in response.result["metrics"]
        assert response.result["metrics"]["requests"]["trend"] == "increasing"


# Integration test for adapter error handling
class TestAdapterErrorHandling:
    """Test common error handling across adapters."""
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = asyncio.TimeoutError()
        
        adapter = SearchAdapter(api_client=mock_client)
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "test"}
        )
        
        response = await adapter.search(request)
        
        assert response.error is not None
        assert response.error["code"] == -32603  # Internal error
        assert "timeout" in response.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_api_connection_error(self):
        """Test handling of connection errors."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = ConnectionError("Connection refused")
        
        adapter = IngestAdapter(api_client=mock_client)
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"url": "https://example.com"}
        )
        
        response = await adapter.ingest_url(request)
        
        assert response.error is not None
        assert "connection" in response.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_api_response(self):
        """Test handling of invalid API responses."""
        mock_client = AsyncMock()
        mock_client.get.return_value = "Invalid JSON"  # Not a dict
        
        adapter = CollectionsAdapter(api_client=mock_client)
        request = MCPRequest(
            id="test",
            method="resource/list",
            params={}
        )
        
        response = await adapter.list_collections(request)
        
        assert response.error is not None
        assert "Invalid response" in response.error["message"]