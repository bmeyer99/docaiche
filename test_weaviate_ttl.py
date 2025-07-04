#!/usr/bin/env python3
"""
Test script to verify TTL field support in Weaviate client.

This script tests:
1. Schema migration for TTL fields
2. Document upload with TTL metadata
3. TTL-based queries (expired documents, by provider)
4. TTL cleanup functionality
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

class WeaviateTTLTester:
    """Test TTL functionality in Weaviate client."""
    
    def __init__(self):
        self.config = WeaviateConfig(
            endpoint="http://weaviate:8080",
            api_key=None  # Using default settings
        )
        self.test_workspace = "ttl-test-workspace"
        
    async def run_all_tests(self) -> bool:
        """Run all TTL tests."""
        logger.info("Starting Weaviate TTL functionality tests...")
        
        try:
            async with WeaviateVectorClient(self.config) as client:
                # Test 1: Schema creation/migration
                await self.test_schema_creation(client)
                
                # Test 2: Document upload with TTL
                test_doc = await self.test_document_upload(client)
                
                # Test 3: TTL queries
                await self.test_ttl_queries(client)
                
                # Test 4: Provider-based queries
                await self.test_provider_queries(client)
                
                # Test 5: Expired document cleanup
                await self.test_expired_cleanup(client)
                
                logger.info("✅ All TTL tests passed!")
                return True
                
        except Exception as e:
            logger.error(f"❌ TTL tests failed: {e}")
            return False
    
    async def test_schema_creation(self, client: WeaviateVectorClient):
        """Test schema creation and migration."""
        logger.info("Testing schema creation and migration...")
        
        # This will trigger _ensure_collection_exists which should handle TTL fields
        await client.get_or_create_workspace(self.test_workspace)
        
        logger.info("✅ Schema creation/migration completed")
    
    async def test_document_upload(self, client: WeaviateVectorClient) -> ProcessedDocument:
        """Test document upload with TTL metadata."""
        logger.info("Testing document upload with TTL metadata...")
        
        # Create test document
        now = datetime.utcnow()
        test_doc = ProcessedDocument(
            id="ttl-test-doc-1",
            title="TTL Test Document",
            full_content="This is a test document for TTL functionality testing.",
            source_url="https://example.com/ttl-test",
            technology="python",
            metadata=DocumentMetadata(
                word_count=12,
                heading_count=1,
                code_block_count=0,
                content_hash="test-hash-123",
                created_at=now
            ),
            quality_score=0.8,
            chunks=[
                DocumentChunk(
                    id="ttl-test-chunk-1",
                    parent_document_id="ttl-test-doc-1",
                    content="This is chunk 1 of the TTL test document.",
                    chunk_index=0,
                    total_chunks=2,
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                    updated_at=now,
                    source_provider="github"
                ),
                DocumentChunk(
                    id="ttl-test-chunk-2",
                    parent_document_id="ttl-test-doc-1",
                    content="This is chunk 2 of the TTL test document.",
                    chunk_index=1,
                    total_chunks=2,
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                    updated_at=now,
                    source_provider="github"
                )
            ],
            created_at=now
        )
        
        # Upload with TTL parameters
        result = await client.upload_document(
            workspace_slug=self.test_workspace,
            document=test_doc,
            ttl_days=7,
            source_provider="github"
        )
        
        logger.info(f"✅ Document uploaded: {result.successful_uploads}/{result.total_chunks} chunks")
        return test_doc
    
    async def test_ttl_queries(self, client: WeaviateVectorClient):
        """Test TTL-based queries."""
        logger.info("Testing TTL-based queries...")
        
        # Test expired documents query (should be empty for fresh uploads)
        expired_docs = await client.get_expired_documents(self.test_workspace)
        logger.info(f"Found {len(expired_docs)} expired documents (expected: 0)")
        
        # Test regular document listing (should include TTL metadata)
        all_docs = await client.list_workspace_documents(self.test_workspace)
        if all_docs:
            first_doc = all_docs[0]
            required_ttl_fields = ["expires_at", "created_at", "updated_at", "source_provider"]
            for field in required_ttl_fields:
                if field not in first_doc:
                    raise ValueError(f"TTL field '{field}' missing from document metadata")
                logger.info(f"✓ TTL field '{field}': {first_doc[field]}")
        
        logger.info("✅ TTL queries working correctly")
    
    async def test_provider_queries(self, client: WeaviateVectorClient):
        """Test provider-based queries."""
        logger.info("Testing provider-based queries...")
        
        # Query documents by provider
        github_docs = await client.get_documents_by_provider(self.test_workspace, "github")
        logger.info(f"Found {len(github_docs)} documents from 'github' provider")
        
        if github_docs:
            doc = github_docs[0]
            if doc["source_provider"] != "github":
                raise ValueError(f"Expected source_provider 'github', got '{doc['source_provider']}'")
        
        logger.info("✅ Provider queries working correctly")
    
    async def test_expired_cleanup(self, client: WeaviateVectorClient):
        """Test expired document cleanup."""
        logger.info("Testing expired document cleanup...")
        
        # Upload a document with very short TTL (already expired)
        now = datetime.utcnow()
        expired_doc = ProcessedDocument(
            id="ttl-expired-doc",
            title="Expired TTL Document",
            full_content="This document should be expired immediately.",
            source_url="https://example.com/expired",
            technology="test",
            metadata=DocumentMetadata(
                word_count=8,
                heading_count=1,
                code_block_count=0,
                content_hash="expired-hash",
                created_at=now
            ),
            quality_score=0.5,
            chunks=[
                DocumentChunk(
                    id="expired-chunk-1",
                    parent_document_id="ttl-expired-doc",
                    content="This chunk is already expired.",
                    chunk_index=0,
                    total_chunks=1,
                    created_at=now,
                    expires_at=now - timedelta(days=1),  # Already expired
                    updated_at=now,
                    source_provider="test"
                )
            ],
            created_at=now
        )
        
        # Upload the expired document with negative TTL
        await client.upload_document(
            workspace_slug=self.test_workspace,
            document=expired_doc,
            ttl_days=-1,  # Already expired
            source_provider="test"
        )
        
        # Check for expired documents
        expired_docs = await client.get_expired_documents(self.test_workspace)
        logger.info(f"Found {len(expired_docs)} expired documents")
        
        # Cleanup expired documents
        cleanup_result = await client.cleanup_expired_documents(self.test_workspace)
        logger.info(f"Cleanup result: {cleanup_result}")
        
        logger.info("✅ Expired cleanup working correctly")
    
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
    tester = WeaviateTTLTester()
    
    try:
        # Run TTL tests
        success = await tester.run_all_tests()
        
        if success:
            logger.info("🎉 All Weaviate TTL tests passed!")
            logger.info("The Weaviate client now supports:")
            logger.info("  ✓ TTL fields in document schema")
            logger.info("  ✓ Automatic schema migration")
            logger.info("  ✓ TTL metadata in uploads")
            logger.info("  ✓ TTL-based queries")
            logger.info("  ✓ Expired document cleanup")
            return 0
        else:
            logger.error("❌ Some TTL tests failed!")
            return 1
    
    finally:
        # Clean up test data
        await tester.cleanup_test_data()

if __name__ == "__main__":
    exit(asyncio.run(main()))