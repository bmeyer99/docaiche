"""
Unit tests for Weaviate TTL Operations
====================================

Comprehensive tests for Weaviate client TTL functionality including:
- TTL document expiration and cleanup
- TTL metadata operations
- Document TTL updates
- Expiration statistics and monitoring
- Batch cleanup operations
- Error handling for TTL operations

Test Coverage:
- get_expired_documents() functionality
- cleanup_expired_documents() batch processing
- update_document_ttl() operations
- get_document_ttl_info() queries
- get_expiration_statistics() monitoring
- Error handling and edge cases
- Performance characteristics
"""

import pytest
import asyncio
import logging
import json
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.clients.weaviate_client import WeaviateVectorClient
from src.clients.exceptions import WeaviateError, WeaviateConnectionError
from src.core.config.models import WeaviateConfig


class TestWeaviateTTLOperations:
    """Test suite for Weaviate TTL operations"""
    
    @pytest.fixture
    def weaviate_config(self):
        """Mock Weaviate configuration"""
        return WeaviateConfig(
            endpoint="http://localhost:8080",
            api_key="test-api-key",
            timeout=30
        )
    
    @pytest.fixture
    def mock_weaviate_client(self, weaviate_config):
        """Mock Weaviate client"""
        client = WeaviateVectorClient(weaviate_config)
        client.client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_collection(self):
        """Mock Weaviate collection"""
        collection = AsyncMock()
        tenant_collection = AsyncMock()
        collection.with_tenant.return_value = tenant_collection
        return collection, tenant_collection
    
    @pytest.fixture
    def sample_expired_objects(self):
        """Sample expired objects from Weaviate"""
        now = datetime.utcnow()
        past_date = now - timedelta(days=1)
        future_date = now + timedelta(days=30)
        
        class MockObject:
            def __init__(self, uuid_val, properties):
                self.uuid = uuid_val
                self.properties = properties
        
        return [
            MockObject("expired-1", {
                "document_id": "doc-1",
                "document_title": "Expired React Guide",
                "expires_at": past_date,
                "created_at": now - timedelta(days=31),
                "updated_at": now - timedelta(days=1),
                "technology": "react",
                "source_url": "https://example.com/react-guide",
                "source_provider": "context7"
            }),
            MockObject("expired-2", {
                "document_id": "doc-1",  # Same document, different chunk
                "document_title": "Expired React Guide",
                "expires_at": past_date,
                "created_at": now - timedelta(days=31),
                "updated_at": now - timedelta(days=1),
                "technology": "react",
                "source_url": "https://example.com/react-guide",
                "source_provider": "context7"
            }),
            MockObject("expired-3", {
                "document_id": "doc-2",
                "document_title": "Expired Vue Tutorial",
                "expires_at": past_date,
                "created_at": now - timedelta(days=15),
                "updated_at": now - timedelta(days=1),
                "technology": "vue",
                "source_url": "https://example.com/vue-tutorial",
                "source_provider": "context7"
            }),
        ]
    
    @pytest.fixture
    def sample_active_objects(self):
        """Sample active (non-expired) objects from Weaviate"""
        now = datetime.utcnow()
        future_date = now + timedelta(days=30)
        
        class MockObject:
            def __init__(self, uuid_val, properties):
                self.uuid = uuid_val
                self.properties = properties
        
        return [
            MockObject("active-1", {
                "document_id": "doc-3",
                "document_title": "Active TypeScript Guide",
                "expires_at": future_date,
                "created_at": now - timedelta(days=5),
                "updated_at": now - timedelta(days=1),
                "technology": "typescript",
                "source_url": "https://example.com/typescript-guide",
                "source_provider": "context7"
            }),
            MockObject("active-2", {
                "document_id": "doc-4",
                "document_title": "Active Node.js API",
                "expires_at": future_date,
                "created_at": now - timedelta(days=10),
                "updated_at": now - timedelta(days=2),
                "technology": "node.js",
                "source_url": "https://example.com/nodejs-api",
                "source_provider": "context7"
            }),
        ]
    
    @pytest.mark.asyncio
    async def test_get_expired_documents_success(self, mock_weaviate_client, mock_collection, sample_expired_objects):
        """Test successful retrieval of expired documents"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse(sample_expired_objects)
        
        # Test the method
        expired_docs = await mock_weaviate_client.get_expired_documents("test-workspace")
        
        # Verify results
        assert len(expired_docs) == 2, f"Should find 2 documents (doc-1 and doc-2), got {len(expired_docs)}"
        
        # Check document 1 (has 2 chunks)
        doc1 = next((doc for doc in expired_docs if doc["id"] == "doc-1"), None)
        assert doc1 is not None, "Document doc-1 should be found"
        assert doc1["title"] == "Expired React Guide"
        assert doc1["chunks"] == 2
        assert doc1["technology"] == "react"
        assert doc1["source_provider"] == "context7"
        
        # Check document 2 (has 1 chunk)
        doc2 = next((doc for doc in expired_docs if doc["id"] == "doc-2"), None)
        assert doc2 is not None, "Document doc-2 should be found"
        assert doc2["title"] == "Expired Vue Tutorial"
        assert doc2["chunks"] == 1
        assert doc2["technology"] == "vue"
    
    @pytest.mark.asyncio
    async def test_get_expired_documents_no_expired(self, mock_weaviate_client, mock_collection, sample_active_objects):
        """Test retrieval when no documents are expired"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response with only active objects
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse(sample_active_objects)
        
        # Test the method
        expired_docs = await mock_weaviate_client.get_expired_documents("test-workspace")
        
        # Verify no expired documents found
        assert len(expired_docs) == 0, f"Should find no expired documents, got {len(expired_docs)}"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents_success(self, mock_weaviate_client, mock_collection):
        """Test successful cleanup of expired documents"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock get_expired_documents to return test data
        mock_expired_docs = [
            {"id": "doc-1", "title": "Expired Doc 1", "chunks": 3},
            {"id": "doc-2", "title": "Expired Doc 2", "chunks": 2},
        ]
        
        with patch.object(mock_weaviate_client, 'get_expired_documents', return_value=mock_expired_docs):
            with patch.object(mock_weaviate_client, 'delete_document') as mock_delete:
                # Mock successful deletions
                mock_delete.return_value = {"success": True, "deleted_chunks": 3}
                
                # Test cleanup
                result = await mock_weaviate_client.cleanup_expired_documents("test-workspace")
                
                # Verify results
                assert result["deleted_documents"] == 2
                assert result["deleted_chunks"] == 6  # 3 + 3 (mock returns 3 for each)
                assert result["failed_deletions"] == 0
                assert "Successfully cleaned up 2 expired documents" in result["message"]
                assert "duration_seconds" in result
                
                # Verify delete_document was called for each expired document
                assert mock_delete.call_count == 2
                mock_delete.assert_any_call("test-workspace", "doc-1")
                mock_delete.assert_any_call("test-workspace", "doc-2")
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents_no_expired(self, mock_weaviate_client):
        """Test cleanup when no expired documents exist"""
        with patch.object(mock_weaviate_client, 'get_expired_documents', return_value=[]):
            result = await mock_weaviate_client.cleanup_expired_documents("test-workspace")
            
            assert result["deleted_documents"] == 0
            assert result["deleted_chunks"] == 0
            assert result["message"] == "No expired documents found"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents_partial_failures(self, mock_weaviate_client):
        """Test cleanup with some deletion failures"""
        mock_expired_docs = [
            {"id": "doc-1", "title": "Expired Doc 1", "chunks": 3},
            {"id": "doc-2", "title": "Expired Doc 2", "chunks": 2},
            {"id": "doc-3", "title": "Expired Doc 3", "chunks": 1},
        ]
        
        def mock_delete(workspace_slug, doc_id):
            if doc_id == "doc-2":
                return {"success": False}  # Simulate failure
            return {"success": True, "deleted_chunks": 2}
        
        with patch.object(mock_weaviate_client, 'get_expired_documents', return_value=mock_expired_docs):
            with patch.object(mock_weaviate_client, 'delete_document', side_effect=mock_delete):
                result = await mock_weaviate_client.cleanup_expired_documents("test-workspace")
                
                assert result["deleted_documents"] == 2  # doc-1 and doc-3 succeeded
                assert result["failed_deletions"] == 1  # doc-2 failed
                assert "failed_document_ids" in result
                assert "doc-2" in result["failed_document_ids"]
                assert "(1 failed)" in result["message"]
    
    @pytest.mark.asyncio
    async def test_update_document_ttl_success(self, mock_weaviate_client, mock_collection):
        """Test successful TTL update for a document"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response for finding document chunks
        class MockObject:
            def __init__(self, uuid_val):
                self.uuid = uuid_val
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        mock_objects = [MockObject(f"chunk-{i}") for i in range(5)]
        tenant_collection.query.fetch_objects.return_value = MockResponse(mock_objects)
        
        # Mock successful updates
        tenant_collection.data.update.return_value = None
        
        # Test TTL update
        result = await mock_weaviate_client.update_document_ttl("test-workspace", "doc-123", 60)
        
        # Verify results
        assert result["success"] is True
        assert result["document_id"] == "doc-123"
        assert result["workspace_slug"] == "test-workspace"
        assert result["total_chunks"] == 5
        assert result["updated_chunks"] == 5
        assert result["new_ttl_days"] == 60
        assert "new_expires_at" in result
        assert "updated_at" in result
        
        # Verify update was called for each chunk
        assert tenant_collection.data.update.call_count == 5
    
    @pytest.mark.asyncio
    async def test_update_document_ttl_partial_failures(self, mock_weaviate_client, mock_collection):
        """Test TTL update with some chunk update failures"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response
        class MockObject:
            def __init__(self, uuid_val):
                self.uuid = uuid_val
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        mock_objects = [MockObject(f"chunk-{i}") for i in range(3)]
        tenant_collection.query.fetch_objects.return_value = MockResponse(mock_objects)
        
        # Mock update to fail for second chunk
        def mock_update(uuid, properties):
            if uuid == "chunk-1":
                raise Exception("Update failed for chunk-1")
        
        tenant_collection.data.update.side_effect = mock_update
        
        # Test TTL update
        result = await mock_weaviate_client.update_document_ttl("test-workspace", "doc-123", 45)
        
        # Verify partial success
        assert result["success"] is True  # Should still be True if any updates succeeded
        assert result["total_chunks"] == 3
        assert result["updated_chunks"] == 2  # Only 2 succeeded
    
    @pytest.mark.asyncio
    async def test_get_document_ttl_info_success(self, mock_weaviate_client, mock_collection):
        """Test successful retrieval of document TTL information"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response
        now = datetime.utcnow()
        created_at = now - timedelta(days=15)
        expires_at = now + timedelta(days=15)
        
        class MockObject:
            def __init__(self):
                self.properties = {
                    "expires_at": expires_at,
                    "created_at": created_at,
                    "updated_at": now - timedelta(days=1),
                    "source_provider": "context7",
                    "technology": "react",
                    "document_title": "React Hooks Guide"
                }
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse([MockObject()])
        
        # Test TTL info retrieval
        result = await mock_weaviate_client.get_document_ttl_info("test-workspace", "doc-123")
        
        # Verify results
        assert result is not None
        assert result["document_id"] == "doc-123"
        assert result["workspace_slug"] == "test-workspace"
        assert result["ttl_days"] == 30  # 30 days from created to expires
        assert result["expired"] is False
        assert result["time_remaining_seconds"] > 0
        assert result["source_provider"] == "context7"
        assert result["technology"] == "react"
        assert result["title"] == "React Hooks Guide"
    
    @pytest.mark.asyncio
    async def test_get_document_ttl_info_expired(self, mock_weaviate_client, mock_collection):
        """Test TTL info for an expired document"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock expired document
        now = datetime.utcnow()
        created_at = now - timedelta(days=45)
        expires_at = now - timedelta(days=5)  # Expired 5 days ago
        
        class MockObject:
            def __init__(self):
                self.properties = {
                    "expires_at": expires_at,
                    "created_at": created_at,
                    "updated_at": now - timedelta(days=6),
                    "source_provider": "context7",
                    "technology": "vue",
                    "document_title": "Deprecated Vue Component"
                }
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse([MockObject()])
        
        # Test TTL info retrieval
        result = await mock_weaviate_client.get_document_ttl_info("test-workspace", "doc-expired")
        
        # Verify expired document results
        assert result is not None
        assert result["document_id"] == "doc-expired"
        assert result["expired"] is True
        assert result["time_remaining_seconds"] is None  # Should be None for expired docs
        assert result["ttl_days"] == 40  # 40 days from created to expires
    
    @pytest.mark.asyncio
    async def test_get_document_ttl_info_not_found(self, mock_weaviate_client, mock_collection):
        """Test TTL info when document is not found"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock empty response
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse([])
        
        # Test TTL info retrieval
        result = await mock_weaviate_client.get_document_ttl_info("test-workspace", "nonexistent-doc")
        
        # Verify None result
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_expiration_statistics_comprehensive(self, mock_weaviate_client, mock_collection):
        """Test comprehensive expiration statistics generation"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Create mixed objects (expired, expiring soon, long-term)
        now = datetime.utcnow()
        
        class MockObject:
            def __init__(self, uuid_val, properties):
                self.uuid = uuid_val
                self.properties = properties
        
        mock_objects = [
            # Expired documents (2 docs, 3 chunks)
            MockObject("expired-1", {
                "document_id": "doc-1",
                "document_title": "Expired React Guide", 
                "expires_at": now - timedelta(days=5),
                "source_provider": "context7"
            }),
            MockObject("expired-2", {
                "document_id": "doc-1",
                "document_title": "Expired React Guide",
                "expires_at": now - timedelta(days=5),
                "source_provider": "context7"
            }),
            MockObject("expired-3", {
                "document_id": "doc-2",
                "document_title": "Expired Vue Tutorial",
                "expires_at": now - timedelta(days=1),
                "source_provider": "context7"
            }),
            
            # Expiring soon (1 doc, 2 chunks)
            MockObject("expiring-1", {
                "document_id": "doc-3",
                "document_title": "Expiring TypeScript Guide",
                "expires_at": now + timedelta(days=3),
                "source_provider": "context7"
            }),
            MockObject("expiring-2", {
                "document_id": "doc-3",
                "document_title": "Expiring TypeScript Guide",
                "expires_at": now + timedelta(days=3),
                "source_provider": "context7"
            }),
            
            # Long-term (1 doc, 1 chunk)
            MockObject("longterm-1", {
                "document_id": "doc-4",
                "document_title": "Long-term Node.js API",
                "expires_at": now + timedelta(days=60),
                "source_provider": "github"
            }),
        ]
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse(mock_objects)
        
        # Test statistics generation
        stats = await mock_weaviate_client.get_expiration_statistics("test-workspace")
        
        # Verify overall statistics
        assert stats["total_chunks"] == 6
        assert stats["total_documents"] == 4
        assert stats["expired_documents"] == 2
        assert stats["expired_chunks"] == 3
        assert stats["expiring_soon_documents"] == 1
        assert stats["expiring_soon_chunks"] == 2
        
        # Verify provider breakdown
        assert "context7" in stats["providers"]
        assert "github" in stats["providers"]
        assert stats["providers"]["context7"]["documents"] == 3
        assert stats["providers"]["context7"]["chunks"] == 5
        assert stats["providers"]["context7"]["expired_documents"] == 2
        assert stats["providers"]["context7"]["expired_chunks"] == 3
        assert stats["providers"]["github"]["documents"] == 1
        assert stats["providers"]["github"]["chunks"] == 1
        assert stats["providers"]["github"]["expired_documents"] == 0
        
        # Verify document categorization
        assert len(stats["documents_by_expiry"]["expired"]) == 2
        assert len(stats["documents_by_expiry"]["expiring_soon"]) == 1
        assert len(stats["documents_by_expiry"]["long_term"]) == 1
        
        # Verify percentages
        assert "expiration_percentages" in stats
        assert stats["expiration_percentages"]["expired"] == 50.0  # 2/4 = 50%
        assert stats["expiration_percentages"]["expiring_soon"] == 25.0  # 1/4 = 25%
        assert stats["expiration_percentages"]["long_term"] == 25.0  # 1/4 = 25%
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_weaviate_client, mock_collection):
        """Test successful document deletion"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query to find chunks
        class MockObject:
            def __init__(self, uuid_val):
                self.uuid = uuid_val
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        mock_objects = [MockObject(f"chunk-{i}") for i in range(4)]
        tenant_collection.query.fetch_objects.return_value = MockResponse(mock_objects)
        
        # Mock successful deletions
        tenant_collection.data.delete_by_id.return_value = None
        
        # Test document deletion
        result = await mock_weaviate_client.delete_document("test-workspace", "doc-123")
        
        # Verify results
        assert result["success"] is True
        assert result["document_id"] == "doc-123"
        assert result["workspace_slug"] == "test-workspace"
        assert result["total_chunks"] == 4
        assert result["deleted_chunks"] == 4
        assert "deleted_at" in result
        
        # Verify delete was called for each chunk
        assert tenant_collection.data.delete_by_id.call_count == 4
    
    @pytest.mark.asyncio
    async def test_delete_document_partial_failures(self, mock_weaviate_client, mock_collection):
        """Test document deletion with some chunk deletion failures"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock the query response
        class MockObject:
            def __init__(self, uuid_val):
                self.uuid = uuid_val
        
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        mock_objects = [MockObject(f"chunk-{i}") for i in range(3)]
        tenant_collection.query.fetch_objects.return_value = MockResponse(mock_objects)
        
        # Mock deletion to fail for one chunk
        def mock_delete(chunk_id):
            if chunk_id == "chunk-1":
                raise Exception("Deletion failed for chunk-1")
        
        tenant_collection.data.delete_by_id.side_effect = mock_delete
        
        # Test document deletion
        result = await mock_weaviate_client.delete_document("test-workspace", "doc-123")
        
        # Verify partial success
        assert result["success"] is True  # Should be True if any deletions succeeded
        assert result["total_chunks"] == 3
        assert result["deleted_chunks"] == 2  # Only 2 succeeded


class TestWeaviateTTLErrorHandling:
    """Test error handling in Weaviate TTL operations"""
    
    @pytest.fixture
    def weaviate_config(self):
        """Mock Weaviate configuration"""
        return WeaviateConfig(
            endpoint="http://localhost:8080",
            api_key="test-api-key",
            timeout=30
        )
    
    @pytest.fixture
    def mock_weaviate_client(self, weaviate_config):
        """Mock Weaviate client"""
        client = WeaviateVectorClient(weaviate_config)
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_get_expired_documents_connection_error(self, mock_weaviate_client):
        """Test get_expired_documents with connection error"""
        # Mock connection failure
        mock_weaviate_client.client.collections.get.side_effect = Exception("Connection failed")
        
        # Test error handling
        with pytest.raises(WeaviateError, match="Failed to get expired documents"):
            await mock_weaviate_client.get_expired_documents("test-workspace")
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents_error(self, mock_weaviate_client):
        """Test cleanup_expired_documents with error"""
        # Mock get_expired_documents to raise exception
        with patch.object(mock_weaviate_client, 'get_expired_documents', side_effect=Exception("Query failed")):
            with pytest.raises(WeaviateError, match="Failed to cleanup expired documents"):
                await mock_weaviate_client.cleanup_expired_documents("test-workspace")
    
    @pytest.mark.asyncio
    async def test_update_document_ttl_error(self, mock_weaviate_client):
        """Test update_document_ttl with connection error"""
        # Mock collection retrieval failure
        mock_weaviate_client.client.collections.get.side_effect = Exception("Collection not found")
        
        # Test error handling
        result = await mock_weaviate_client.update_document_ttl("test-workspace", "doc-123", 45)
        
        # Should return error result instead of raising exception
        assert result["success"] is False
        assert "error" in result
        assert result["document_id"] == "doc-123"
        assert result["updated_chunks"] == 0
    
    @pytest.mark.asyncio
    async def test_get_document_ttl_info_error(self, mock_weaviate_client):
        """Test get_document_ttl_info with error"""
        # Mock query failure
        mock_weaviate_client.client.collections.get.side_effect = Exception("Query failed")
        
        # Test error handling
        result = await mock_weaviate_client.get_document_ttl_info("test-workspace", "doc-123")
        
        # Should return None on error
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_expiration_statistics_error(self, mock_weaviate_client):
        """Test get_expiration_statistics with error"""
        # Mock collection retrieval failure
        mock_weaviate_client.client.collections.get.side_effect = Exception("Collection access failed")
        
        # Test error handling
        with pytest.raises(WeaviateError, match="Failed to get expiration statistics"):
            await mock_weaviate_client.get_expiration_statistics("test-workspace")
    
    @pytest.mark.asyncio
    async def test_delete_document_error(self, mock_weaviate_client):
        """Test delete_document with error"""
        # Mock collection retrieval failure
        mock_weaviate_client.client.collections.get.side_effect = Exception("Collection not accessible")
        
        # Test error handling
        result = await mock_weaviate_client.delete_document("test-workspace", "doc-123")
        
        # Should return error result
        assert result["success"] is False
        assert "error" in result
        assert result["document_id"] == "doc-123"
        assert result["deleted_chunks"] == 0


class TestWeaviateTTLPerformance:
    """Test performance characteristics of Weaviate TTL operations"""
    
    @pytest.fixture
    def weaviate_config(self):
        """Mock Weaviate configuration"""
        return WeaviateConfig(
            endpoint="http://localhost:8080",
            api_key="test-api-key",
            timeout=30
        )
    
    @pytest.fixture
    def mock_weaviate_client(self, weaviate_config):
        """Mock Weaviate client"""
        client = WeaviateVectorClient(weaviate_config)
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_cleanup_large_batch_performance(self, mock_weaviate_client):
        """Test cleanup performance with large batch of expired documents"""
        import time
        
        # Create large batch of expired documents
        large_batch = []
        for i in range(100):
            large_batch.append({
                "id": f"doc-{i}",
                "title": f"Expired Document {i}",
                "chunks": 3
            })
        
        # Mock fast deletion
        with patch.object(mock_weaviate_client, 'get_expired_documents', return_value=large_batch):
            with patch.object(mock_weaviate_client, 'delete_document') as mock_delete:
                mock_delete.return_value = {"success": True, "deleted_chunks": 3}
                
                start_time = time.time()
                result = await mock_weaviate_client.cleanup_expired_documents("test-workspace", batch_size=20)
                processing_time = time.time() - start_time
                
                # Should complete reasonably quickly
                assert processing_time < 10.0, f"Large batch cleanup took too long: {processing_time}s"
                assert result["deleted_documents"] == 100
                assert result["deleted_chunks"] == 300
    
    @pytest.mark.asyncio
    async def test_batch_size_optimization(self, mock_weaviate_client):
        """Test that batch size affects processing behavior"""
        # Create moderate batch
        batch = [{"id": f"doc-{i}", "title": f"Doc {i}", "chunks": 1} for i in range(10)]
        
        with patch.object(mock_weaviate_client, 'get_expired_documents', return_value=batch):
            with patch.object(mock_weaviate_client, 'delete_document') as mock_delete:
                mock_delete.return_value = {"success": True, "deleted_chunks": 1}
                
                # Test with small batch size
                result_small = await mock_weaviate_client.cleanup_expired_documents("test-workspace", batch_size=2)
                
                # Test with large batch size
                result_large = await mock_weaviate_client.cleanup_expired_documents("test-workspace", batch_size=20)
                
                # Both should achieve same result
                assert result_small["deleted_documents"] == result_large["deleted_documents"] == 10
                assert result_small["deleted_chunks"] == result_large["deleted_chunks"] == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_ttl_operations(self, mock_weaviate_client, mock_collection):
        """Test concurrent TTL operations don't interfere"""
        collection, tenant_collection = mock_collection
        mock_weaviate_client.client.collections.get.return_value = collection
        
        # Mock responses for concurrent operations
        class MockResponse:
            def __init__(self, objects):
                self.objects = objects
        
        tenant_collection.query.fetch_objects.return_value = MockResponse([])
        tenant_collection.data.update.return_value = None
        
        # Run multiple operations concurrently
        tasks = [
            mock_weaviate_client.update_document_ttl("workspace-1", "doc-1", 30),
            mock_weaviate_client.update_document_ttl("workspace-1", "doc-2", 45),
            mock_weaviate_client.get_document_ttl_info("workspace-1", "doc-3"),
            mock_weaviate_client.get_expiration_statistics("workspace-1"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])