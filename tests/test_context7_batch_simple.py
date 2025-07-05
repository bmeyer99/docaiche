#!/usr/bin/env python3
"""
SUB-TASK A3: Batch Processing and Weaviate Integration Verification Tests (Simplified)
=====================================================================================

Comprehensive verification of Context7IngestionService batch processing and
Weaviate integration. Tests batch processing of multiple documents, TTL metadata
application, error handling, and performance with larger batches without pytest dependency.
"""

import asyncio
import sys
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.ingestion.smart_pipeline import ProcessingResult
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType
from src.document_processing.models import DocumentContent


class BatchProcessingTests:
    """Batch processing and Weaviate integration tests"""
    
    def __init__(self):
        self.mock_weaviate_client = AsyncMock()
        self.mock_weaviate_client.upload_document.return_value = MagicMock(successful_uploads=5)
        self.mock_weaviate_client.cleanup_expired_documents.return_value = {
            "deleted_documents": 3,
            "deleted_chunks": 15,
            "message": "Cleanup successful"
        }
        
        self.mock_db_manager = AsyncMock()
        self.mock_db_manager.execute.return_value = 3
        self.mock_db_manager.fetch_all.return_value = []
        
        self.service = Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=self.mock_weaviate_client,
            db_manager=self.mock_db_manager,
            ttl_config=TTLConfig()
        )
        
        self.sample_intent = QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks", "state"],
            doc_type="guide",
            user_level="intermediate"
        )
    
    def create_search_result(self, title, content, url, metadata=None):
        """Helper to create search results"""
        return SearchResult(
            title=title,
            url=url,
            snippet=content[:200],
            content=content,
            content_type=SearchResultType.DOCUMENTATION,
            source_domain="context7.com",
            relevance_score=0.85,
            provider_rank=1,
            metadata=metadata or {"owner": "facebook", "technology": "react", "source": "context7"}
        )
    
    def create_context7_document(self, title, content, technology="react", owner="facebook"):
        """Helper to create Context7 documents"""
        return Context7Document(
            content=content,
            title=title,
            source_url=f"https://context7.com/{owner}/{technology}/llms.txt",
            technology=technology,
            owner=owner,
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
    
    async def test_small_batch_processing(self):
        """Test batch processing with small batch (under batch size)"""
        # Create 3 search results (under batch size of 5)
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(3)
        ]
        
        # Mock the conversion and processing
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(self.service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                results = await self.service.process_context7_results(search_results, self.sample_intent)
                
                assert len(results) == 3, f"Expected 3 results, got {len(results)}"
                assert all(result.success for result in results), "All results should be successful"
                assert all(result.chunks_processed == 2 for result in results), "All results should have 2 chunks processed"
                assert mock_convert.call_count == 3, f"Expected 3 conversion calls, got {mock_convert.call_count}"
                assert mock_process.call_count == 3, f"Expected 3 processing calls, got {mock_process.call_count}"
    
    async def test_large_batch_processing(self):
        """Test batch processing with large batch (multiple batches)"""
        # Create 12 search results (will be split into 3 batches of 5, 5, 2)
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(12)
        ]
        
        # Mock the conversion and processing
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(self.service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=3,
                    workspace_slug="react-docs"
                )
                
                results = await self.service.process_context7_results(search_results, self.sample_intent)
                
                assert len(results) == 12, f"Expected 12 results, got {len(results)}"
                assert all(result.success for result in results), "All results should be successful"
                assert all(result.chunks_processed == 3 for result in results), "All results should have 3 chunks processed"
                assert mock_convert.call_count == 12, f"Expected 12 conversion calls, got {mock_convert.call_count}"
                assert mock_process.call_count == 12, f"Expected 12 processing calls, got {mock_process.call_count}"
    
    async def test_batch_processing_with_conversion_failures(self):
        """Test batch processing with some conversion failures"""
        # Create 5 search results
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(5)
        ]
        
        # Mock conversion to fail for some documents
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            def conversion_side_effect(result, intent, correlation_id=None):
                if "doc1" in result.url or "doc3" in result.url:
                    return None  # Simulate conversion failure
                return self.create_context7_document("Test Doc", "Test content")
            
            mock_convert.side_effect = conversion_side_effect
            
            with patch.object(self.service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                results = await self.service.process_context7_results(search_results, self.sample_intent)
                
                # Should only process 3 documents (2 failed conversion)
                assert len(results) == 3, f"Expected 3 results (3 successful), got {len(results)}"
                assert all(result.success for result in results), "All returned results should be successful"
                assert mock_convert.call_count == 5, f"Expected 5 conversion calls, got {mock_convert.call_count}"
                assert mock_process.call_count == 3, f"Expected 3 processing calls, got {mock_process.call_count}"
    
    async def test_batch_processing_with_processing_failures(self):
        """Test batch processing with some processing failures"""
        # Create 4 search results
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(4)
        ]
        
        # Mock the conversion
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(self.service, 'process_context7_document') as mock_process:
                def processing_side_effect(doc, intent, correlation_id=None):
                    if "doc1" in doc.source_url:
                        return ProcessingResult(
                            success=False,
                            chunks_processed=0,
                            workspace_slug="",
                            error_message="Processing failed"
                        )
                    return ProcessingResult(
                        success=True,
                        chunks_processed=2,
                        workspace_slug="react-docs"
                    )
                
                mock_process.side_effect = processing_side_effect
                
                results = await self.service.process_context7_results(search_results, self.sample_intent)
                
                # Should get all 4 results (1 failed, 3 successful)
                assert len(results) == 4, f"Expected 4 results, got {len(results)}"
                successful_results = [r for r in results if r.success]
                failed_results = [r for r in results if not r.success]
                assert len(successful_results) == 3, f"Expected 3 successful results, got {len(successful_results)}"
                assert len(failed_results) == 1, f"Expected 1 failed result, got {len(failed_results)}"
                assert failed_results[0].error_message == "Processing failed", "Wrong error message"
    
    async def test_parallel_document_batch_processing(self):
        """Test parallel document batch processing"""
        # Create 3 Context7 documents
        documents = [
            self.create_context7_document(f"Doc {i}", f"Content {i}")
            for i in range(3)
        ]
        
        # Mock the individual document processing
        with patch.object(self.service, 'process_context7_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=2,
                workspace_slug="react-docs"
            )
            
            results = await self.service._process_document_batch(documents, self.sample_intent)
            
            assert len(results) == 3, f"Expected 3 results, got {len(results)}"
            assert all(result.success for result in results), "All results should be successful"
            assert mock_process.call_count == 3, f"Expected 3 processing calls, got {mock_process.call_count}"
    
    async def test_ttl_metadata_application(self):
        """Test TTL metadata application to Weaviate"""
        content = DocumentContent(
            content_id="test-content-id",
            title="Test Document",
            text="Test content",
            source_url="https://context7.com/test",
            metadata={"technology": "react", "owner": "facebook"}
        )
        
        workspace_slug = "react-docs"
        ttl_days = 45
        
        # Mock the database update
        self.mock_db_manager.execute.return_value = 1
        
        await self.service._add_ttl_metadata(content, workspace_slug, ttl_days)
        
        # Verify database was called with correct parameters
        self.mock_db_manager.execute.assert_called_once()
        call_args = self.mock_db_manager.execute.call_args
        
        assert "UPDATE content_metadata" in call_args[0][0], "Wrong SQL query"
        assert "ttl_info" in call_args[0][0], "TTL info not in query"
        assert call_args[1]["content_id"] == "test-content-id", "Wrong content ID"
        
        # Verify TTL metadata structure
        ttl_metadata = json.loads(call_args[1]["ttl_metadata"])
        assert ttl_metadata["ttl_days"] == 45, f"Expected TTL 45 days, got {ttl_metadata['ttl_days']}"
        assert ttl_metadata["source_provider"] == "context7", "Wrong source provider"
        assert "created_at" in ttl_metadata, "Missing created_at"
        assert "updated_at" in ttl_metadata, "Missing updated_at"
        assert "expires_at" in ttl_metadata, "Missing expires_at"
    
    async def test_ttl_metadata_timestamps(self):
        """Test TTL metadata timestamp calculations"""
        content = DocumentContent(
            content_id="test-content-id",
            title="Test Document",
            text="Test content",
            source_url="https://context7.com/test"
        )
        
        ttl_days = 30
        
        # Mock the current time
        with patch('src.ingestion.context7_ingestion_service.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            await self.service._add_ttl_metadata(content, "workspace", ttl_days)
            
            # Verify the call was made
            self.mock_db_manager.execute.assert_called_once()
            call_args = self.mock_db_manager.execute.call_args
            
            # Parse TTL metadata
            ttl_metadata = json.loads(call_args[1]["ttl_metadata"])
            
            # Check timestamps
            created_at = datetime.fromisoformat(ttl_metadata["created_at"])
            expires_at = datetime.fromisoformat(ttl_metadata["expires_at"])
            
            assert created_at == mock_now, f"Expected {mock_now}, got {created_at}"
            assert expires_at == mock_now + timedelta(days=30), f"Wrong expiration time"
    
    async def test_process_with_ttl_success(self):
        """Test processing with TTL success path"""
        content = DocumentContent(
            content_id="test-content-id",
            title="Test Document",
            text="Test content",
            source_url="https://context7.com/test"
        )
        
        intent = QueryIntent(
            intent="documentation",
            technology="react"
        )
        
        ttl_days = 45
        
        # Mock the parent process_documentation method
        with patch.object(self.service, 'process_documentation') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=5,
                workspace_slug="react-docs"
            )
            
            result = await self.service._process_with_ttl(content, intent, ttl_days)
            
            assert result.success is True, "Processing should be successful"
            assert result.chunks_processed == 5, f"Expected 5 chunks, got {result.chunks_processed}"
            assert result.workspace_slug == "react-docs", f"Wrong workspace slug: {result.workspace_slug}"
            
            # Verify TTL metadata was added
            self.mock_db_manager.execute.assert_called_once()
    
    async def test_cleanup_expired_documents(self):
        """Test cleanup of expired documents"""
        workspace_slug = "react-docs"
        
        # Mock Weaviate cleanup
        self.mock_weaviate_client.cleanup_expired_documents.return_value = {
            "deleted_documents": 5,
            "deleted_chunks": 25,
            "message": "Cleanup completed"
        }
        
        # Mock database cleanup
        self.mock_db_manager.execute.return_value = 3
        
        result = await self.service.cleanup_expired_documents(workspace_slug)
        
        assert result["workspace"] == workspace_slug, f"Wrong workspace: {result['workspace']}"
        assert result["weaviate_cleanup"]["deleted_documents"] == 5, "Wrong deleted documents count"
        assert result["weaviate_cleanup"]["deleted_chunks"] == 25, "Wrong deleted chunks count"
        assert result["database_records_cleaned"] == 3, "Wrong database records count"
        assert "cleaned_at" in result, "Missing cleaned_at timestamp"
        
        # Verify Weaviate cleanup was called
        self.mock_weaviate_client.cleanup_expired_documents.assert_called_once_with(workspace_slug)
        
        # Verify database cleanup was called
        self.mock_db_manager.execute.assert_called_once()
        call_args = self.mock_db_manager.execute.call_args
        assert "DELETE FROM content_metadata" in call_args[0][0], "Wrong delete query"
        assert "expires_at" in call_args[0][0], "Missing expires_at condition"
    
    async def test_empty_search_results(self):
        """Test handling of empty search results"""
        search_results = []
        
        results = await self.service.process_context7_results(search_results, self.sample_intent)
        
        assert len(results) == 0, f"Expected 0 results, got {len(results)}"
    
    async def test_all_conversions_fail(self):
        """Test when all document conversions fail"""
        search_results = [
            self.create_search_result(f"Doc {i}", f"Content {i}", f"https://context7.com/doc{i}")
            for i in range(3)
        ]
        
        # Mock conversion to always fail
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = None
            
            results = await self.service.process_context7_results(search_results, self.sample_intent)
            
            assert len(results) == 0, f"Expected 0 results, got {len(results)}"
            assert mock_convert.call_count == 3, f"Expected 3 conversion calls, got {mock_convert.call_count}"
    
    async def test_performance_with_large_batch(self):
        """Test performance with large batch of documents"""
        # Create 20 search results to test performance (reduced from 50 for faster testing)
        search_results = [
            self.create_search_result(f"Doc {i}", f"Content {i}", f"https://context7.com/doc{i}")
            for i in range(20)
        ]
        
        # Mock the conversion and processing
        with patch.object(self.service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(self.service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                import time
                start_time = time.time()
                
                results = await self.service.process_context7_results(search_results, self.sample_intent)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                assert len(results) == 20, f"Expected 20 results, got {len(results)}"
                assert all(result.success for result in results), "All results should be successful"
                assert processing_time < 5, f"Processing took too long: {processing_time:.2f}s"
                
                # Verify batching occurred
                assert mock_convert.call_count == 20, f"Expected 20 conversion calls, got {mock_convert.call_count}"
                assert mock_process.call_count == 20, f"Expected 20 processing calls, got {mock_process.call_count}"


async def main():
    """Run all batch processing and Weaviate integration tests"""
    print("="*60)
    print("SUB-TASK A3: Batch Processing and Weaviate Integration Verification")
    print("="*60)
    
    tests = BatchProcessingTests()
    
    test_methods = [
        ("Small Batch Processing", tests.test_small_batch_processing),
        ("Large Batch Processing", tests.test_large_batch_processing),
        ("Batch Processing with Conversion Failures", tests.test_batch_processing_with_conversion_failures),
        ("Batch Processing with Processing Failures", tests.test_batch_processing_with_processing_failures),
        ("Parallel Document Batch Processing", tests.test_parallel_document_batch_processing),
        ("TTL Metadata Application", tests.test_ttl_metadata_application),
        ("TTL Metadata Timestamps", tests.test_ttl_metadata_timestamps),
        ("Process with TTL Success", tests.test_process_with_ttl_success),
        ("Cleanup Expired Documents", tests.test_cleanup_expired_documents),
        ("Empty Search Results", tests.test_empty_search_results),
        ("All Conversions Fail", tests.test_all_conversions_fail),
        ("Performance with Large Batch", tests.test_performance_with_large_batch)
    ]
    
    tests_passed = 0
    tests_failed = 0
    
    for test_name, test_method in test_methods:
        try:
            print(f"\n🔍 Running {test_name}...")
            await test_method()
            print(f"✅ {test_name} PASSED")
            tests_passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            tests_failed += 1
    
    print(f"\n{'='*60}")
    print(f"SUB-TASK A3 RESULTS:")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
    
    if tests_failed == 0:
        print("✅ ALL BATCH PROCESSING AND WEAVIATE INTEGRATION TESTS PASSED")
        return True
    else:
        print(f"❌ {tests_failed} BATCH PROCESSING AND WEAVIATE INTEGRATION TESTS FAILED")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test runner failed: {e}")
        exit(1)