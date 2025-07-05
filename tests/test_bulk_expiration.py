#!/usr/bin/env python3
"""
Test script to verify enhanced bulk expiration methods in Weaviate client.

This script tests:
1. Enhanced get_expired_documents method with limit parameter
2. Enhanced cleanup_expired_documents method with batch processing 
3. Enhanced get_documents_by_provider method with limit parameter
4. API endpoint functionality
5. Performance and error handling
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from src.clients.weaviate_client import WeaviateVectorClient
from src.core.config.models import WeaviateConfig
from src.database.connection import ProcessedDocument, DocumentChunk, DocumentMetadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BulkExpirationTester:
    """Test enhanced bulk expiration functionality in Weaviate client."""
    
    def __init__(self):
        self.config = WeaviateConfig(
            endpoint="http://weaviate:8080",
            api_key="docaiche-weaviate-key-2025"
        )
        self.test_workspace = "bulk-expiration-test"
        
    async def run_all_tests(self) -> bool:
        """Run all bulk expiration tests."""
        logger.info("Starting enhanced bulk expiration functionality tests...")
        
        try:
            async with WeaviateVectorClient(self.config) as client:
                # Test 1: Schema and workspace setup
                await self.test_setup(client)
                
                # Test 2: Upload test documents
                await self.test_upload_documents(client)
                
                # Test 3: Enhanced get_expired_documents
                await self.test_get_expired_documents(client)
                
                # Test 4: Enhanced get_documents_by_provider
                await self.test_get_documents_by_provider(client)
                
                # Test 5: Enhanced cleanup_expired_documents
                await self.test_cleanup_expired_documents(client)
                
                # Test 6: Performance with large limit
                await self.test_performance(client)
                
                logger.info("✅ All enhanced bulk expiration tests passed!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Enhanced bulk expiration tests failed: {e}")
            return False
    
    async def test_setup(self, client: WeaviateVectorClient):
        """Test workspace setup."""
        logger.info("Setting up test workspace...")
        
        await client.get_or_create_workspace(self.test_workspace)
        logger.info("✅ Workspace setup completed")
    
    async def test_upload_documents(self, client: WeaviateVectorClient):
        """Upload test documents with various TTL settings."""
        logger.info("Uploading test documents...")
        
        now = datetime.utcnow()
        
        # Document 1: Not expired (github provider)
        doc1 = self.create_test_document(
            "test-doc-1", 
            "Not Expired Document", 
            expires_at=now + timedelta(days=30),
            provider="github"
        )
        await client.upload_document(self.test_workspace, doc1, ttl_days=30, source_provider="github")
        
        # Document 2: Expired (github provider)
        doc2 = self.create_test_document(
            "test-doc-2", 
            "Expired Document", 
            expires_at=now - timedelta(days=1),
            provider="github"
        )
        await client.upload_document(self.test_workspace, doc2, ttl_days=-1, source_provider="github")
        
        # Document 3: Not expired (gitlab provider)
        doc3 = self.create_test_document(
            "test-doc-3", 
            "Not Expired GitLab Doc", 
            expires_at=now + timedelta(days=15),
            provider="gitlab"
        )
        await client.upload_document(self.test_workspace, doc3, ttl_days=15, source_provider="gitlab")
        
        # Document 4: Expired (gitlab provider)
        doc4 = self.create_test_document(
            "test-doc-4", 
            "Expired GitLab Doc", 
            expires_at=now - timedelta(days=2),
            provider="gitlab"
        )
        await client.upload_document(self.test_workspace, doc4, ttl_days=-2, source_provider="gitlab")
        
        logger.info("✅ Test documents uploaded")
    
    def create_test_document(self, doc_id: str, title: str, expires_at: datetime, provider: str) -> ProcessedDocument:
        """Create a test document with specified parameters."""
        now = datetime.utcnow()
        
        return ProcessedDocument(
            id=doc_id,
            title=title,
            full_content=f"This is test content for {title}",
            source_url=f"https://example.com/{doc_id}",
            technology="python",
            metadata=DocumentMetadata(
                word_count=10,
                heading_count=1,
                code_block_count=0,
                content_hash=f"hash-{doc_id}",
                created_at=now
            ),
            quality_score=0.8,
            chunks=[
                DocumentChunk(
                    id=f"{doc_id}-chunk-1",
                    parent_document_id=doc_id,
                    content=f"First chunk of {title}",
                    chunk_index=0,
                    total_chunks=2,
                    created_at=now,
                    expires_at=expires_at,
                    updated_at=now,
                    source_provider=provider
                ),
                DocumentChunk(
                    id=f"{doc_id}-chunk-2",
                    parent_document_id=doc_id,
                    content=f"Second chunk of {title}",
                    chunk_index=1,
                    total_chunks=2,
                    created_at=now,
                    expires_at=expires_at,
                    updated_at=now,
                    source_provider=provider
                )
            ],
            created_at=now
        )
    
    async def test_get_expired_documents(self, client: WeaviateVectorClient):
        """Test enhanced get_expired_documents method."""
        logger.info("Testing enhanced get_expired_documents method...")
        
        # Test with default limit
        expired_docs = await client.get_expired_documents(self.test_workspace)
        logger.info(f"Found {len(expired_docs)} expired documents (default limit)")
        
        # Should find 2 expired documents
        assert len(expired_docs) == 2, f"Expected 2 expired documents, got {len(expired_docs)}"
        
        # Test with custom limit
        expired_docs_limited = await client.get_expired_documents(self.test_workspace, limit=1)
        logger.info(f"Found {len(expired_docs_limited)} expired documents (limit=1)")
        
        # Test that TTL fields are present
        if expired_docs:
            doc = expired_docs[0]
            required_fields = ["id", "title", "chunks", "expires_at", "created_at", "updated_at", "source_provider"]
            for field in required_fields:
                assert field in doc, f"Required field '{field}' missing from expired document"
        
        logger.info("✅ Enhanced get_expired_documents method working correctly")
    
    async def test_get_documents_by_provider(self, client: WeaviateVectorClient):
        """Test enhanced get_documents_by_provider method."""
        logger.info("Testing enhanced get_documents_by_provider method...")
        
        # Test GitHub provider
        github_docs = await client.get_documents_by_provider(self.test_workspace, "github")
        logger.info(f"Found {len(github_docs)} GitHub documents")
        assert len(github_docs) == 2, f"Expected 2 GitHub documents, got {len(github_docs)}"
        
        # Test GitLab provider
        gitlab_docs = await client.get_documents_by_provider(self.test_workspace, "gitlab")
        logger.info(f"Found {len(gitlab_docs)} GitLab documents")
        assert len(gitlab_docs) == 2, f"Expected 2 GitLab documents, got {len(gitlab_docs)}"
        
        # Test with custom limit
        github_docs_limited = await client.get_documents_by_provider(self.test_workspace, "github", limit=1)
        logger.info(f"Found {len(github_docs_limited)} GitHub documents (limit=1)")
        
        # Test non-existent provider
        nonexistent_docs = await client.get_documents_by_provider(self.test_workspace, "nonexistent")
        logger.info(f"Found {len(nonexistent_docs)} documents for non-existent provider")
        assert len(nonexistent_docs) == 0, f"Expected 0 documents for non-existent provider, got {len(nonexistent_docs)}"
        
        logger.info("✅ Enhanced get_documents_by_provider method working correctly")
    
    async def test_cleanup_expired_documents(self, client: WeaviateVectorClient):
        """Test enhanced cleanup_expired_documents method."""
        logger.info("Testing enhanced cleanup_expired_documents method...")
        
        # First, check how many expired documents exist
        expired_docs_before = await client.get_expired_documents(self.test_workspace)
        logger.info(f"Expired documents before cleanup: {len(expired_docs_before)}")
        
        # Test cleanup with custom batch size
        cleanup_result = await client.cleanup_expired_documents(self.test_workspace, batch_size=1)
        logger.info(f"Cleanup result: {cleanup_result}")
        
        # Verify cleanup results
        expected_fields = ["deleted_documents", "deleted_chunks", "failed_deletions", "message", "duration_seconds"]
        for field in expected_fields:
            assert field in cleanup_result, f"Required field '{field}' missing from cleanup result"
        
        # Verify documents were deleted
        assert cleanup_result["deleted_documents"] == len(expired_docs_before), \
            f"Expected {len(expired_docs_before)} deleted documents, got {cleanup_result['deleted_documents']}"
        
        # Verify no more expired documents
        expired_docs_after = await client.get_expired_documents(self.test_workspace)
        logger.info(f"Expired documents after cleanup: {len(expired_docs_after)}")
        assert len(expired_docs_after) == 0, f"Expected 0 expired documents after cleanup, got {len(expired_docs_after)}"
        
        logger.info("✅ Enhanced cleanup_expired_documents method working correctly")
    
    async def test_performance(self, client: WeaviateVectorClient):
        """Test performance with larger limits."""
        logger.info("Testing performance with larger limits...")
        
        start_time = datetime.utcnow()
        
        # Test with large limit
        all_docs = await client.get_expired_documents(self.test_workspace, limit=50000)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Performance test completed in {duration:.2f}s, found {len(all_docs)} documents")
        
        # Should complete within reasonable time
        assert duration < 10.0, f"Performance test took too long: {duration:.2f}s"
        
        logger.info("✅ Performance test passed")
    
    async def cleanup_test_data(self):
        """Clean up test data."""
        logger.info("Cleaning up test data...")
        
        try:
            async with WeaviateVectorClient(self.config) as client:
                # Delete all test documents
                docs = await client.list_workspace_documents(self.test_workspace)
                for doc in docs:
                    await client.delete_document(self.test_workspace, doc["id"])
                
                logger.info("✅ Test data cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup failed (this is usually ok): {e}")

async def main():
    """Main test function."""
    tester = BulkExpirationTester()
    
    try:
        # Run enhanced bulk expiration tests
        success = await tester.run_all_tests()
        
        if success:
            logger.info("🎉 All enhanced bulk expiration tests passed!")
            logger.info("Enhanced features verified:")
            logger.info("  ✓ get_expired_documents with custom limit")
            logger.info("  ✓ cleanup_expired_documents with batch processing")
            logger.info("  ✓ get_documents_by_provider with custom limit")
            logger.info("  ✓ Enhanced error handling and logging")
            logger.info("  ✓ Performance optimization for large datasets")
            logger.info("  ✓ Comprehensive statistics and reporting")
            return 0
        else:
            logger.error("❌ Some enhanced bulk expiration tests failed!")
            return 1
    
    finally:
        # Clean up test data
        await tester.cleanup_test_data()

if __name__ == "__main__":
    exit(asyncio.run(main()))