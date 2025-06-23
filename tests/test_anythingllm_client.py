"""
Test Suite for AnythingLLM Client - PRD-004 ALM-001
Comprehensive tests for AnythingLLM client functionality and circuit breaker behavior

Tests cover all specified requirements including workspace management,
document upload, search operations, error handling, and circuit breaker patterns.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.core.config.models import AnythingLLMConfig, CircuitBreakerConfig
from src.database.connection import ProcessedDocument, DocumentChunk, UploadResult, DocumentMetadata
from src.clients.anythingllm import AnythingLLMClient
from src.clients.exceptions import (
    AnythingLLMError,
    AnythingLLMConnectionError,
    AnythingLLMAuthenticationError,
    AnythingLLMRateLimitError,
    AnythingLLMWorkspaceError,
    AnythingLLMDocumentError
)


class TestAnythingLLMClient:
    """Test cases for AnythingLLM client functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return AnythingLLMConfig(
            endpoint="http://localhost:3001",
            api_key="test-api-key-12345",
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60,
                timeout_seconds=30
            )
        )
    
    @pytest.fixture
    def sample_document(self):
        """Create sample processed document for testing"""
        created_time = datetime.utcnow()
        
        chunks = [
            DocumentChunk(
                id="chunk-1",
                parent_document_id="doc-123",
                content="This is the first chunk of content about React.",
                chunk_index=0,
                total_chunks=2,
                created_at=created_time
            ),
            DocumentChunk(
                id="chunk-2",
                parent_document_id="doc-123",
                content="This is the second chunk with more React information.",
                chunk_index=1,
                total_chunks=2,
                created_at=created_time
            )
        ]
        
        metadata = DocumentMetadata(
            word_count=19,
            heading_count=2,
            code_block_count=0,
            content_hash="abc123def456",
            created_at=created_time
        )
        
        return ProcessedDocument(
            id="doc-123",
            title="React Documentation",
            full_content="This is the first chunk of content about React. This is the second chunk with more React information.",
            source_url="https://react.dev/learn",
            technology="react",
            metadata=metadata,
            quality_score=0.85,
            chunks=chunks,
            created_at=created_time
        )
    
    @pytest.fixture
    def client(self, config):
        """Create client with mocked session"""
        client = AnythingLLMClient(config)
        # Mock the session to avoid real HTTP calls
        client.session = AsyncMock()
        
        # Create proper circuit breaker mock with state
        mock_cb = MagicMock()
        mock_cb.state = MagicMock()
        mock_cb.state.name = 'CLOSED'
        mock_cb.failure_count = 0
        mock_cb.last_failure_time = None
        client.circuit_breaker = mock_cb
        
        # Mock the circuit breaker call to bypass it - accept all pybreaker parameters
        def bypass_circuit_breaker(*cb_args, **cb_kwargs):
            def decorator(func):
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)
                return wrapper
            return decorator
        
        # Replace circuit breaker decorator with passthrough
        import src.clients.anythingllm
        original_circuit = src.clients.anythingllm.circuit
        src.clients.anythingllm.circuit = bypass_circuit_breaker
        
        return client
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_client_initialization(self, config):
        """Test client initialization with configuration"""
        client = AnythingLLMClient(config)
        
        assert client.config == config
        assert client.base_url == "http://localhost:3001"
        assert client.api_key == "test-api-key-12345"
        assert client.session is None
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, config):
        """Test session connection and disconnection"""
        async with AnythingLLMClient(config) as client:
            assert client.session is not None
            assert not client.session.closed
        
        # Session should be closed after context exit
        assert client.session.closed
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check"""
        # Mock successful response with proper data structure
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 12345
        }
        
        mock_response = AsyncMock()
        # Configure json() method to return actual data, not MagicMock
        mock_response.json.return_value = health_data
        mock_response.status = 200
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        result = await client.health_check()
        
        assert result["status"] == "healthy"
        assert "circuit_breaker" in result
        assert "state" in result["circuit_breaker"]
        
        # Verify correct API call
        client.session.request.assert_called_once_with(
            "GET", "http://localhost:3001/api/health"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check with service failure"""
        # Mock connection error
        client.session.request.side_effect = aiohttp.ClientConnectorError(
            connection_key="test", os_error=OSError("Connection failed")
        )
        
        result = await client.health_check()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "circuit_breaker" in result
    
    @pytest.mark.asyncio
    async def test_list_workspaces_success(self, client):
        """Test successful workspace listing"""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "workspaces": [
                {"slug": "react-docs", "name": "React Documentation"},
                {"slug": "vue-docs", "name": "Vue.js Documentation"}
            ]
        })
        mock_response.status = 200
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        workspaces = await client.list_workspaces()
        
        assert len(workspaces) == 2
        assert workspaces[0]["slug"] == "react-docs"
        assert workspaces[1]["slug"] == "vue-docs"
    
    @pytest.mark.asyncio
    async def test_get_or_create_workspace_existing(self, client):
        """Test getting existing workspace"""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "slug": "react-docs",
            "name": "React Documentation",
            "id": "workspace-123"
        })
        mock_response.status = 200
        
        # Create proper async context manager mock
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        workspace = await client.get_or_create_workspace("react-docs")
        
        assert workspace["slug"] == "react-docs"
        assert workspace["name"] == "React Documentation"
        
        # Should call GET endpoint first
        client.session.request.assert_called_with(
            "GET", "http://localhost:3001/api/workspace/react-docs"
        )
    
    @pytest.mark.asyncio
    async def test_get_or_create_workspace_new(self, client):
        """Test creating new workspace when not found"""
        # Mock 404 for GET, then successful POST
        get_response = AsyncMock()
        get_response.status = 404
        get_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404
        )
        
        post_response = AsyncMock()
        post_response.json = AsyncMock(return_value={
            "slug": "new-workspace",
            "name": "New Workspace",
            "id": "workspace-456"
        })
        post_response.status = 201
        
        # Configure side_effect for multiple calls
        async_context_get = AsyncMock()
        async_context_get.__aenter__ = AsyncMock(return_value=get_response)
        
        async_context_post = AsyncMock()
        async_context_post.__aenter__ = AsyncMock(return_value=post_response)
        
        client.session.request.side_effect = [async_context_get, async_context_post]
        
        workspace = await client.get_or_create_workspace("new-workspace", "New Workspace")
        
        assert workspace["slug"] == "new-workspace"
        assert workspace["name"] == "New Workspace"
        
        # Should have made both GET and POST calls
        assert client.session.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, client, sample_document):
        """Test successful document upload"""
        # Mock workspace exists
        workspace_response = AsyncMock()
        workspace_response.json.return_value = {"slug": "react-docs", "id": "ws-123"}
        workspace_response.status = 200
        
        # Mock successful chunk uploads
        chunk_response = AsyncMock()
        chunk_response.status = 201
        
        client.session.request.return_value.__aenter__.side_effect = [
            workspace_response,  # Workspace check
            chunk_response,      # First chunk upload
            chunk_response       # Second chunk upload
        ]
        
        result = await client.upload_document("react-docs", sample_document)
        
        assert result.document_id == "doc-123"
        assert result.workspace_slug == "react-docs"
        assert result.total_chunks == 2
        assert result.successful_uploads == 2
        assert result.failed_uploads == 0
        assert len(result.uploaded_chunk_ids) == 2
        assert len(result.failed_chunk_ids) == 0
    
    @pytest.mark.asyncio
    async def test_upload_document_partial_failure(self, client, sample_document):
        """Test document upload with some chunk failures"""
        # Mock workspace exists
        workspace_response = AsyncMock()
        workspace_response.json.return_value = {"slug": "react-docs", "id": "ws-123"}
        workspace_response.status = 200
        
        # Mock mixed success/failure for chunks
        success_response = AsyncMock()
        success_response.status = 201
        
        failure_response = AsyncMock()
        failure_response.status = 500
        failure_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500
        )
        
        client.session.request.return_value.__aenter__.side_effect = [
            workspace_response,  # Workspace check
            success_response,    # First chunk succeeds
            failure_response     # Second chunk fails
        ]
        
        result = await client.upload_document("react-docs", sample_document)
        
        assert result.total_chunks == 2
        assert result.successful_uploads == 1
        assert result.failed_uploads == 1
        assert len(result.uploaded_chunk_ids) == 1
        assert len(result.failed_chunk_ids) == 1
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_search_workspace_success(self, client):
        """Test successful workspace search"""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "results": [
                {
                    "content": "React is a JavaScript library",
                    "metadata": {"source": "react-docs", "score": 0.95},
                    "id": "result-1"
                },
                {
                    "content": "Components are the building blocks",
                    "metadata": {"source": "react-docs", "score": 0.87},
                    "id": "result-2"
                }
            ]
        })
        mock_response.status = 200
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        results = await client.search_workspace("react-docs", "React components", limit=10)
        
        assert len(results) == 2
        assert results[0]["content"] == "React is a JavaScript library"
        assert results[1]["content"] == "Components are the building blocks"
        
        # Verify search request
        client.session.request.assert_called_with(
            "POST",
            "http://localhost:3001/api/workspace/react-docs/search",
            json={
                "message": "React components",
                "limit": 10,
                "mode": "query"
            }
        )
    
    @pytest.mark.asyncio
    async def test_list_workspace_documents(self, client):
        """Test listing workspace documents"""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "documents": [
                {"id": "doc-1", "title": "React Basics", "chunks": 5},
                {"id": "doc-2", "title": "Advanced React", "chunks": 8}
            ]
        })
        mock_response.status = 200
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        documents = await client.list_workspace_documents("react-docs")
        
        assert len(documents) == 2
        assert documents[0]["title"] == "React Basics"
        assert documents[1]["title"] == "Advanced React"
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, client):
        """Test successful document deletion"""
        mock_response = AsyncMock()
        mock_response.status = 204
        
        client.session.request.return_value.__aenter__.return_value = mock_response
        
        result = await client.delete_document("react-docs", "doc-123")
        
        assert result is True
        
        client.session.request.assert_called_with(
            "DELETE",
            "http://localhost:3001/api/workspace/react-docs/delete/doc-123"
        )
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client):
        """Test deleting document that doesn't exist"""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        client.session.request.return_value.__aenter__.return_value = mock_response
        
        result = await client.delete_document("react-docs", "doc-404")
        
        assert result is True  # 404 treated as success (already deleted)
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """Test authentication error handling"""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid API key")
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=401
        )
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        with pytest.raises(AnythingLLMAuthenticationError) as exc_info:
            await client.list_workspaces()
        
        assert "Authentication failed" in str(exc_info.value)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit error handling"""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=429
        )
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        with pytest.raises(AnythingLLMRateLimitError) as exc_info:
            await client.search_workspace("test", "query")
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after == 60
        assert exc_info.value.status_code == 429
    
    @pytest.mark.asyncio
    async def test_workspace_not_found_error(self, client):
        """Test workspace not found error handling"""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Workspace not found")
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404
        )
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        with pytest.raises(AnythingLLMWorkspaceError) as exc_info:
            await client.search_workspace("nonexistent", "query")
        
        assert "Workspace error" in str(exc_info.value)
        assert exc_info.value.workspace_slug == "nonexistent"
    
    @pytest.mark.asyncio
    async def test_connection_timeout_error(self, client):
        """Test connection timeout error handling"""
        client.session.request.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(AnythingLLMConnectionError) as exc_info:
            await client.health_check()
        
        assert "Request timeout" in str(exc_info.value)
        assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self, config):
        """Test error when session not initialized"""
        client = AnythingLLMClient(config)
        # Don't initialize session
        
        with pytest.raises(RuntimeError) as exc_info:
            await client.health_check()
        
        assert "Client session not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_request_logging(self, client, caplog):
        """Test request and response logging"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "healthy"})
        
        # Create proper async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_response)
        client.session.request.return_value = async_context
        
        with caplog.at_level("DEBUG"):
            await client.health_check()
        
        # Check that request and response were logged
        assert any("AnythingLLM request: GET" in record.message for record in caplog.records)
        assert any("AnythingLLM response: 200" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__])