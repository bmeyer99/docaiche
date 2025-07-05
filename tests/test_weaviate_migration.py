#!/usr/bin/env python3
"""
Test script to validate Weaviate migration
Ensures all functionality works correctly after migration from AnythingLLM
"""

import asyncio
import os
import sys
import logging
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.weaviate_client import WeaviateVectorClient
from src.core.config.models import WeaviateConfig
from src.database.connection import ProcessedDocument, DocumentChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection():
    """Test basic connection to Weaviate"""
    logger.info("Testing Weaviate connection...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        health = await client.health_check()
        logger.info(f"Health check result: {health}")
        assert health.get("status") == "healthy", "Weaviate is not healthy"
        assert health.get("ready") is True, "Weaviate is not ready"
    
    logger.info("✅ Connection test passed")


async def test_workspace_operations():
    """Test workspace (tenant) operations"""
    logger.info("Testing workspace operations...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        # List workspaces
        workspaces = await client.list_workspaces()
        logger.info(f"Current workspaces: {len(workspaces)}")
        
        # Create or get test workspace
        test_workspace = await client.get_or_create_workspace("test-workspace", "Test Workspace")
        logger.info(f"Test workspace: {test_workspace}")
        assert test_workspace["slug"] == "test-workspace"
        
        # List again to verify
        workspaces_after = await client.list_workspaces()
        workspace_slugs = [ws["slug"] for ws in workspaces_after]
        assert "test-workspace" in workspace_slugs
    
    logger.info("✅ Workspace operations test passed")


async def test_document_upload():
    """Test document upload functionality"""
    logger.info("Testing document upload...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        # Create test document
        test_chunks = [
            DocumentChunk(
                id="test-chunk-1",
                content="Weaviate is a vector database that supports multi-tenancy.",
                chunk_index=0,
                total_chunks=2,
                metadata={"test": True}
            ),
            DocumentChunk(
                id="test-chunk-2",
                content="It provides excellent performance for vector search operations.",
                chunk_index=1,
                total_chunks=2,
                metadata={"test": True}
            )
        ]
        
        test_doc = ProcessedDocument(
            id="test-doc-1",
            title="Test Document",
            source_url="https://example.com/test",
            technology="testing",
            chunks=test_chunks
        )
        
        # Upload document
        result = await client.upload_document("test-workspace", test_doc)
        logger.info(f"Upload result: {result}")
        
        assert result.successful_uploads > 0, "No chunks were uploaded"
        assert result.failed_uploads == 0, "Some chunks failed to upload"
    
    logger.info("✅ Document upload test passed")


async def test_search():
    """Test search functionality"""
    logger.info("Testing search...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        # Search in test workspace
        results = await client.search_workspace("test-workspace", "vector database", limit=5)
        logger.info(f"Search results: {len(results)} found")
        
        # Verify results
        assert isinstance(results, list), "Results should be a list"
        if results:
            result = results[0]
            assert "content" in result, "Result should have content"
            assert "metadata" in result, "Result should have metadata"
            logger.info(f"First result: {result['content'][:100]}...")
    
    logger.info("✅ Search test passed")


async def test_list_documents():
    """Test listing documents in workspace"""
    logger.info("Testing document listing...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        # List documents in test workspace
        documents = await client.list_workspace_documents("test-workspace")
        logger.info(f"Documents in workspace: {len(documents)}")
        
        # Verify structure
        if documents:
            doc = documents[0]
            assert "id" in doc, "Document should have id"
            assert "title" in doc, "Document should have title"
            assert "chunks" in doc, "Document should have chunk count"
            logger.info(f"First document: {doc}")
    
    logger.info("✅ Document listing test passed")


async def test_delete_document():
    """Test document deletion"""
    logger.info("Testing document deletion...")
    
    config = WeaviateConfig(
        endpoint=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    )
    
    async with WeaviateVectorClient(config) as client:
        # Delete test document
        success = await client.delete_document("test-workspace", "test-doc-1")
        logger.info(f"Delete result: {success}")
        assert success is True, "Document deletion failed"
        
        # Verify deletion
        documents = await client.list_workspace_documents("test-workspace")
        doc_ids = [doc["id"] for doc in documents]
        assert "test-doc-1" not in doc_ids, "Document still exists after deletion"
    
    logger.info("✅ Document deletion test passed")


async def run_all_tests():
    """Run all tests in sequence"""
    logger.info("Starting Weaviate migration tests...")
    
    try:
        await test_connection()
        await test_workspace_operations()
        await test_document_upload()
        await test_search()
        await test_list_documents()
        await test_delete_document()
        
        logger.info("\n🎉 All tests passed! Weaviate migration is working correctly.")
        
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())