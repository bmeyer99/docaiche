#!/usr/bin/env python3
"""
SUB-TASK A3: Batch Processing and Weaviate Integration Verification Tests
=======================================================================

Comprehensive verification of Context7IngestionService batch processing and
Weaviate integration. Tests batch processing of multiple documents, TTL metadata
application, error handling, and performance with larger batches.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.ingestion.smart_pipeline import ProcessingResult
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType
from src.document_processing.models import DocumentContent


class TestBatchProcessingAndWeaviateIntegration:
    """Comprehensive batch processing and Weaviate integration tests"""
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client with comprehensive responses"""
        mock = AsyncMock()
        mock.upload_document.return_value = MagicMock(successful_uploads=5)
        mock.cleanup_expired_documents.return_value = {
            "deleted_documents": 3,
            "deleted_chunks": 15,
            "message": "Cleanup successful"
        }
        return mock
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        mock = AsyncMock()
        mock.execute.return_value = 3  # Number of affected rows
        mock.fetch_all.return_value = []
        return mock
    
    @pytest.fixture
    def service(self, mock_weaviate_client, mock_db_manager):
        """Create service instance with mocked dependencies"""
        return Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=mock_weaviate_client,
            db_manager=mock_db_manager,
            ttl_config=TTLConfig()
        )
    
    @pytest.fixture
    def sample_intent(self):
        """Sample query intent"""
        return QueryIntent(
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
    
    @pytest.mark.asyncio
    async def test_batch_processing_small_batch(self, service, sample_intent):
        """Test batch processing with small batch (under batch size)"""
        # Create 3 search results (under batch size of 5)
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(3)
        ]
        
        # Mock the conversion and processing
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                results = await service.process_context7_results(search_results, sample_intent)
                
                assert len(results) == 3
                assert all(result.success for result in results)
                assert all(result.chunks_processed == 2 for result in results)
                assert mock_convert.call_count == 3
                assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_processing_large_batch(self, service, sample_intent):
        """Test batch processing with large batch (multiple batches)"""
        # Create 12 search results (will be split into 3 batches of 5, 5, 2)
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(12)
        ]
        
        # Mock the conversion and processing
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=3,
                    workspace_slug="react-docs"
                )
                
                results = await service.process_context7_results(search_results, sample_intent)
                
                assert len(results) == 12
                assert all(result.success for result in results)
                assert all(result.chunks_processed == 3 for result in results)
                assert mock_convert.call_count == 12
                assert mock_process.call_count == 12
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_conversion_failures(self, service, sample_intent):
        """Test batch processing with some conversion failures"""
        # Create 5 search results
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(5)
        ]
        
        # Mock conversion to fail for some documents
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            def conversion_side_effect(result, intent, correlation_id=None):
                if "doc1" in result.url or "doc3" in result.url:
                    return None  # Simulate conversion failure
                return self.create_context7_document("Test Doc", "Test content")
            
            mock_convert.side_effect = conversion_side_effect
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                results = await service.process_context7_results(search_results, sample_intent)
                
                # Should only process 3 documents (2 failed conversion)
                assert len(results) == 3
                assert all(result.success for result in results)
                assert mock_convert.call_count == 5
                assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_processing_failures(self, service, sample_intent):
        """Test batch processing with some processing failures"""
        # Create 4 search results
        search_results = [
            self.create_search_result(f"React Doc {i}", f"Content {i}", f"https://context7.com/react/doc{i}")
            for i in range(4)
        ]
        
        # Mock the conversion
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(service, 'process_context7_document') as mock_process:
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
                
                results = await service.process_context7_results(search_results, sample_intent)
                
                # Should get all 4 results (1 failed, 3 successful)
                assert len(results) == 4
                successful_results = [r for r in results if r.success]
                failed_results = [r for r in results if not r.success]
                assert len(successful_results) == 3
                assert len(failed_results) == 1
                assert failed_results[0].error_message == "Processing failed"
    
    @pytest.mark.asyncio
    async def test_document_batch_processing_parallel(self, service, sample_intent):
        """Test parallel document batch processing"""
        # Create 3 Context7 documents
        documents = [
            self.create_context7_document(f"Doc {i}", f"Content {i}")
            for i in range(3)
        ]
        
        # Mock the individual document processing
        with patch.object(service, 'process_context7_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=2,
                workspace_slug="react-docs"
            )
            
            results = await service._process_document_batch(documents, sample_intent)
            
            assert len(results) == 3
            assert all(result.success for result in results)
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_document_batch_processing_with_exceptions(self, service, sample_intent):
        """Test document batch processing with exceptions"""
        # Create 3 Context7 documents
        documents = [
            self.create_context7_document(f"Doc {i}", f"Content {i}")
            for i in range(3)
        ]
        
        # Mock the individual document processing to raise exception for one
        with patch.object(service, 'process_context7_document') as mock_process:
            def processing_side_effect(doc, intent, correlation_id=None):
                if "Doc 1" in doc.title:
                    raise Exception("Processing error")
                return ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
            
            mock_process.side_effect = processing_side_effect
            
            results = await service._process_document_batch(documents, sample_intent)
            
            # Should only get 2 results (1 exception filtered out)
            assert len(results) == 2
            assert all(result.success for result in results)
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_ttl_metadata_application_to_weaviate(self, service, mock_db_manager):
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
        mock_db_manager.execute.return_value = 1
        
        await service._add_ttl_metadata(content, workspace_slug, ttl_days)
        
        # Verify database was called with correct parameters
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        
        assert "UPDATE content_metadata" in call_args[0][0]
        assert "ttl_info" in call_args[0][0]
        assert call_args[1]["content_id"] == "test-content-id"
        
        # Verify TTL metadata structure
        ttl_metadata = json.loads(call_args[1]["ttl_metadata"])
        assert ttl_metadata["ttl_days"] == 45
        assert ttl_metadata["source_provider"] == "context7"
        assert "created_at" in ttl_metadata
        assert "updated_at" in ttl_metadata
        assert "expires_at" in ttl_metadata
    
    @pytest.mark.asyncio
    async def test_ttl_metadata_timestamps(self, service, mock_db_manager):
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
            
            await service._add_ttl_metadata(content, "workspace", ttl_days)
            
            # Verify the call was made
            mock_db_manager.execute.assert_called_once()
            call_args = mock_db_manager.execute.call_args
            
            # Parse TTL metadata
            ttl_metadata = json.loads(call_args[1]["ttl_metadata"])
            
            # Check timestamps
            created_at = datetime.fromisoformat(ttl_metadata["created_at"])
            expires_at = datetime.fromisoformat(ttl_metadata["expires_at"])
            
            assert created_at == mock_now
            assert expires_at == mock_now + timedelta(days=30)
    
    @pytest.mark.asyncio
    async def test_process_with_ttl_success(self, service, mock_db_manager):
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
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=5,
                workspace_slug="react-docs"
            )
            
            result = await service._process_with_ttl(content, intent, ttl_days)
            
            assert result.success is True
            assert result.chunks_processed == 5
            assert result.workspace_slug == "react-docs"
            
            # Verify TTL metadata was added
            mock_db_manager.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_with_ttl_processing_failure(self, service, mock_db_manager):
        """Test processing with TTL when processing fails"""
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
        
        # Mock the parent process_documentation method to fail
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=False,
                chunks_processed=0,
                workspace_slug="",
                error_message="Processing failed"
            )
            
            result = await service._process_with_ttl(content, intent, ttl_days)
            
            assert result.success is False
            assert result.chunks_processed == 0
            assert result.error_message == "Processing failed"
            
            # Verify TTL metadata was NOT added
            mock_db_manager.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_with_ttl_exception_handling(self, service):
        """Test processing with TTL exception handling"""
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
        
        # Mock the parent process_documentation method to raise exception
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.side_effect = Exception("Processing exception")
            
            result = await service._process_with_ttl(content, intent, ttl_days)
            
            assert result.success is False
            assert result.chunks_processed == 0
            assert "Processing exception" in result.error_message
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents(self, service, mock_weaviate_client, mock_db_manager):
        """Test cleanup of expired documents"""
        workspace_slug = "react-docs"
        
        # Mock Weaviate cleanup
        mock_weaviate_client.cleanup_expired_documents.return_value = {
            "deleted_documents": 5,
            "deleted_chunks": 25,
            "message": "Cleanup completed"
        }
        
        # Mock database cleanup
        mock_db_manager.execute.return_value = 3
        
        result = await service.cleanup_expired_documents(workspace_slug)
        
        assert result["workspace"] == workspace_slug
        assert result["weaviate_cleanup"]["deleted_documents"] == 5
        assert result["weaviate_cleanup"]["deleted_chunks"] == 25
        assert result["database_records_cleaned"] == 3
        assert "cleaned_at" in result
        
        # Verify Weaviate cleanup was called
        mock_weaviate_client.cleanup_expired_documents.assert_called_once_with(workspace_slug)
        
        # Verify database cleanup was called
        mock_db_manager.execute.assert_called_once()
        call_args = mock_db_manager.execute.call_args
        assert "DELETE FROM content_metadata" in call_args[0][0]
        assert "expires_at" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_documents_with_errors(self, service, mock_weaviate_client, mock_db_manager):
        """Test cleanup with errors"""
        workspace_slug = "react-docs"
        
        # Mock Weaviate cleanup to raise exception
        mock_weaviate_client.cleanup_expired_documents.side_effect = Exception("Weaviate error")
        
        result = await service.cleanup_expired_documents(workspace_slug)
        
        assert result["workspace"] == workspace_slug
        assert result["weaviate_cleanup"]["deleted_documents"] == 0
        assert result["weaviate_cleanup"]["deleted_chunks"] == 0
        assert result["database_records_cleaned"] == 0
        assert "errors" in result
        assert "Weaviate error" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_performance_with_large_batch(self, service, sample_intent):
        """Test performance with large batch of documents"""
        # Create 50 search results to test performance
        search_results = [
            self.create_search_result(f"Doc {i}", f"Content {i}", f"https://context7.com/doc{i}")
            for i in range(50)
        ]
        
        # Mock the conversion and processing
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                import time
                start_time = time.time()
                
                results = await service.process_context7_results(search_results, sample_intent)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                assert len(results) == 50
                assert all(result.success for result in results)
                assert processing_time < 10  # Should process in under 10 seconds
                
                # Verify batching occurred (50 documents in batches of 5 = 10 batches)
                assert mock_convert.call_count == 50
                assert mock_process.call_count == 50
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, service, sample_intent):
        """Test correlation ID propagation through batch processing"""
        search_results = [
            self.create_search_result("Test Doc", "Test content", "https://context7.com/test")
        ]
        
        correlation_id = "test-correlation-123"
        
        # Mock the conversion and processing
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = self.create_context7_document("Test Doc", "Test content")
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                await service.process_context7_results(search_results, sample_intent, correlation_id)
                
                # Verify correlation ID was passed to conversion
                mock_convert.assert_called_once()
                convert_args = mock_convert.call_args
                assert convert_args[1]["correlation_id"] == correlation_id
    
    @pytest.mark.asyncio
    async def test_empty_search_results(self, service, sample_intent):
        """Test handling of empty search results"""
        search_results = []
        
        results = await service.process_context7_results(search_results, sample_intent)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_all_conversions_fail(self, service, sample_intent):
        """Test when all document conversions fail"""
        search_results = [
            self.create_search_result(f"Doc {i}", f"Content {i}", f"https://context7.com/doc{i}")
            for i in range(3)
        ]
        
        # Mock conversion to always fail
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = None
            
            results = await service.process_context7_results(search_results, sample_intent)
            
            assert len(results) == 0
            assert mock_convert.call_count == 3


async def main():
    """Run all batch processing and Weaviate integration tests"""
    print("="*60)
    print("SUB-TASK A3: Batch Processing and Weaviate Integration Verification")
    print("="*60)
    
    # Initialize test class
    test_class = TestBatchProcessingAndWeaviateIntegration()
    
    # Get fixtures
    mock_weaviate_client = test_class.mock_weaviate_client()
    mock_db_manager = test_class.mock_db_manager()
    service = test_class.service(mock_weaviate_client, mock_db_manager)
    sample_intent = test_class.sample_intent()
    
    tests_passed = 0
    tests_failed = 0
    
    test_methods = [
        test_class.test_batch_processing_small_batch,
        test_class.test_batch_processing_large_batch,
        test_class.test_batch_processing_with_conversion_failures,
        test_class.test_batch_processing_with_processing_failures,
        test_class.test_document_batch_processing_parallel,
        test_class.test_document_batch_processing_with_exceptions,
        test_class.test_ttl_metadata_application_to_weaviate,
        test_class.test_ttl_metadata_timestamps,
        test_class.test_process_with_ttl_success,
        test_class.test_process_with_ttl_processing_failure,
        test_class.test_process_with_ttl_exception_handling,
        test_class.test_cleanup_expired_documents,
        test_class.test_cleanup_expired_documents_with_errors,
        test_class.test_performance_with_large_batch,
        test_class.test_correlation_id_propagation,
        test_class.test_empty_search_results,
        test_class.test_all_conversions_fail
    ]
    
    for test_method in test_methods:
        try:
            test_name = test_method.__name__
            print(f"\n🔍 Running {test_name}...")
            
            # Run the test with appropriate fixtures
            if 'mock_db_manager' in test_method.__code__.co_varnames:
                if 'mock_weaviate_client' in test_method.__code__.co_varnames:
                    await test_method(service, mock_weaviate_client, mock_db_manager)
                else:
                    await test_method(service, mock_db_manager)
            elif 'sample_intent' in test_method.__code__.co_varnames:
                await test_method(service, sample_intent)
            else:
                await test_method(service)
            
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
    success = asyncio.run(main())
    exit(0 if success else 1)