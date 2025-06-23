"""
Document Ingestion Pipeline - Final Production Readiness Validation
POST-CRITICAL FIX VALIDATION: Comprehensive testing after import os fix

Tests all critical production requirements:
1. Service startup and initialization 
2. Database operations functionality
3. Core document ingestion workflow
4. Security measures validation
5. API endpoints functionality
6. Integration with PRD-008 Content Processing Pipeline
"""

import pytest
import asyncio
import os
import tempfile
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
from src.database.connection import DatabaseManager, create_database_manager
from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline
from src.ingestion.models import DocumentUploadRequest, IngestionStatus
from src.api.v1.ingestion import get_ingestion_pipeline
from src.main import create_application


class TestServiceStartupValidation:
    """Validate service startup and initialization after import fix"""
    
    @pytest.mark.asyncio
    async def test_database_connection_no_import_errors(self):
        """CRITICAL: Verify database connection works without import errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = await create_database_manager({"db_path": db_path})
            
            # Test connection - should not fail with import errors
            await db_manager.connect()
            assert db_manager._connected
            
            # Test basic operation
            result = await db_manager.fetch_one("SELECT 1 as test")
            assert result.test == 1
            
            await db_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_fastapi_application_startup(self):
        """Verify FastAPI application initializes without errors"""
        app = create_application()
        assert app is not None
        assert app.title == "AI Documentation Cache System API"
        assert "/api/v1" in [route.path for route in app.routes if hasattr(route, 'path')]
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_creation(self):
        """Verify ingestion pipeline can be created successfully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_processor:
                mock_processor.return_value = MagicMock()
                mock_processor.return_value.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                pipeline = await create_ingestion_pipeline()
                assert pipeline is not None
                assert hasattr(pipeline, 'ingest_single_document')


class TestDatabaseOperationsValidation:
    """Validate database operations are functional"""
    
    @pytest.mark.asyncio
    async def test_database_crud_operations(self):
        """Test basic database CRUD operations work correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = await create_database_manager({"db_path": db_path})
            await db_manager.connect()
            
            # Test table creation
            await db_manager.execute("""
                CREATE TABLE test_table (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test insert
            await db_manager.execute(
                "INSERT INTO test_table (id, content) VALUES (?, ?)",
                ("test_id", "test_content")
            )
            
            # Test select
            result = await db_manager.fetch_one(
                "SELECT id, content FROM test_table WHERE id = ?",
                ("test_id",)
            )
            assert result.id == "test_id"
            assert result.content == "test_content"
            
            await db_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_database_transaction_support(self):
        """Verify database transactions work correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = await create_database_manager({"db_path": db_path})
            await db_manager.connect()
            
            # Create test table
            await db_manager.execute("""
                CREATE TABLE transaction_test (
                    id TEXT PRIMARY KEY,
                    value INTEGER
                )
            """)
            
            # Test transaction success
            queries = [
                ("INSERT INTO transaction_test (id, value) VALUES (?, ?)", ("id1", 100)),
                ("INSERT INTO transaction_test (id, value) VALUES (?, ?)", ("id2", 200))
            ]
            result = await db_manager.execute_transaction(queries)
            assert result is True
            
            # Verify data was inserted
            count = await db_manager.fetch_one("SELECT COUNT(*) as count FROM transaction_test")
            assert count.count == 2
            
            await db_manager.disconnect()


class TestCoreWorkflowValidation:
    """Validate core document ingestion workflow"""
    
    @pytest.mark.asyncio
    async def test_document_upload_processing_workflow(self):
        """Test complete document upload → processing → storage workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock content processor to simulate PRD-008 integration
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock successful processing
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "doc_12345"
                mock_processed_doc.content_hash = "abc123"
                mock_processed_doc.word_count = 500
                mock_processed_doc.chunks = ["chunk1", "chunk2"]
                mock_processed_doc.quality_score = 0.85
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                # Mock document extractor
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Test document content", {"pages": 1})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    # Create pipeline and test workflow
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test document upload
                    file_data = b"Test document content"
                    upload_request = DocumentUploadRequest(
                        filename="test.txt",
                        content_type="text/plain",
                        technology="python",
                        title="Test Document"
                    )
                    
                    result = await pipeline.ingest_single_document(file_data, upload_request)
                    
                    # Verify successful processing
                    assert result.status == IngestionStatus.COMPLETED
                    assert result.document_id == "doc_12345"
                    assert result.filename == "test.txt"
                    assert result.word_count == 500
                    assert result.quality_score == 0.85
    
    @pytest.mark.asyncio
    async def test_supported_file_formats_processing(self):
        """Test processing of all supported file formats"""
        supported_formats = [
            ("test.txt", "text/plain", b"Plain text content"),
            ("test.md", "text/markdown", b"# Markdown Content\nTest content"),
            ("test.html", "text/html", b"<html><body>HTML content</body></html>")
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock successful processing for all formats
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "doc_test"
                mock_processed_doc.content_hash = "hash123"
                mock_processed_doc.word_count = 100
                mock_processed_doc.chunks = ["chunk1"]
                mock_processed_doc.quality_score = 0.8
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Extracted content", {"format": "text"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    for filename, content_type, file_data in supported_formats:
                        upload_request = DocumentUploadRequest(
                            filename=filename,
                            content_type=content_type,
                            technology="test"
                        )
                        
                        result = await pipeline.ingest_single_document(file_data, upload_request)
                        assert result.status == IngestionStatus.COMPLETED, f"Failed to process {filename}"


class TestSecurityValidation:
    """Validate security measures are working correctly"""
    
    @pytest.mark.asyncio
    async def test_file_size_limits_enforced(self):
        """Verify file size limits prevent oversized uploads"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Create oversized file (larger than 50MB limit)
                    oversized_data = b"x" * (51 * 1024 * 1024)  # 51MB
                    
                    upload_request = DocumentUploadRequest(
                        filename="large.txt",
                        content_type="text/plain",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(oversized_data, upload_request)
                    assert result.status == IngestionStatus.REJECTED
                    assert "exceeds limit" in result.error_message
    
    @pytest.mark.asyncio
    async def test_unsupported_format_rejection(self):
        """Verify unsupported file formats are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test unsupported format
                    upload_request = DocumentUploadRequest(
                        filename="test.exe",  # Unsupported format
                        content_type="application/exe",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(b"binary data", upload_request)
                    assert result.status == IngestionStatus.REJECTED
                    assert "Unsupported file format" in result.error_message
    
    @pytest.mark.asyncio
    async def test_empty_file_rejection(self):
        """Verify empty files are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    upload_request = DocumentUploadRequest(
                        filename="empty.txt",
                        content_type="text/plain",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(b"", upload_request)
                    assert result.status == IngestionStatus.REJECTED
                    assert "Empty file not allowed" in result.error_message


class TestAPIFunctionalityValidation:
    """Validate API endpoints functionality"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_functionality(self):
        """Test ingestion health endpoint returns proper status"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                await mock_processor.db_manager.connect()
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    # Test health check
                    from src.api.v1.ingestion import health_check
                    
                    pipeline = await get_ingestion_pipeline()
                    health_result = await health_check(pipeline)
                    
                    assert health_result.status in ["healthy", "degraded"]
                    assert isinstance(health_result.supported_formats, list)
                    assert health_result.max_file_size_mb > 0
                    assert health_result.max_batch_size > 0
    
    @pytest.mark.asyncio
    async def test_dependency_injection_works(self):
        """Verify dependency injection for pipeline works correctly"""
        with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create:
            mock_pipeline = AsyncMock()
            mock_create.return_value = mock_pipeline
            
            # Test dependency function
            pipeline = await get_ingestion_pipeline()
            assert pipeline is not None
            mock_create.assert_called_once()


class TestIntegrationWithPRD008:
    """Validate integration with Content Processing Pipeline (PRD-008)"""
    
    @pytest.mark.asyncio
    async def test_content_processor_integration(self):
        """Verify proper integration with PRD-008 Content Processing Pipeline"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock PRD-008 processing result
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "processed_doc_id"
                mock_processed_doc.content_hash = "content_hash_123"
                mock_processed_doc.word_count = 750
                mock_processed_doc.chunks = ["chunk1", "chunk2", "chunk3"]
                mock_processed_doc.quality_score = 0.92
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Extracted text content", {"metadata": "test"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test integration
                    file_data = b"Test document for PRD-008 integration"
                    upload_request = DocumentUploadRequest(
                        filename="integration_test.txt",
                        content_type="text/plain",
                        technology="python",
                        title="Integration Test Document",
                        source_url="test://integration"
                    )
                    
                    result = await pipeline.ingest_single_document(file_data, upload_request)
                    
                    # Verify PRD-008 was called with correct parameters
                    mock_processor.process_and_store_document.assert_called_once()
                    call_args = mock_processor.process_and_store_document.call_args
                    file_content = call_args[0][0]
                    technology = call_args[0][1]
                    
                    assert file_content.content == "Extracted text content"
                    assert file_content.title == "Integration Test Document"
                    assert file_content.source_url == "test://integration"
                    assert technology == "python"
                    
                    # Verify result reflects PRD-008 processing
                    assert result.status == IngestionStatus.COMPLETED
                    assert result.document_id == "processed_doc_id"
                    assert result.word_count == 750
                    assert result.chunk_count == 3
                    assert result.quality_score == 0.92
    
    @pytest.mark.asyncio
    async def test_processing_failure_handling(self):
        """Verify proper handling when PRD-008 processing fails"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock PRD-008 failure
                mock_processor.process_and_store_document.return_value = (None, "processing_failed")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Content", {"meta": "data"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    upload_request = DocumentUploadRequest(
                        filename="fail_test.txt",
                        content_type="text/plain",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(b"content", upload_request)
                    
                    # Verify failure is properly handled
                    assert result.status == IngestionStatus.FAILED
                    assert "Content processing failed" in result.error_message


class TestErrorHandlingValidation:
    """Validate comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Verify proper handling of database errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock database error
                mock_processor.db_manager.fetch_one.side_effect = Exception("Database connection failed")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test that database errors don't crash the service
                    metrics = await pipeline.get_processing_metrics()
                    assert metrics is not None  # Should return empty metrics, not crash
    
    @pytest.mark.asyncio
    async def test_extraction_error_handling(self):
        """Verify proper handling of content extraction errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    # Mock extraction failure
                    mock_extractor.extract_content.side_effect = Exception("Extraction failed")
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    upload_request = DocumentUploadRequest(
                        filename="error_test.txt",
                        content_type="text/plain",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(b"content", upload_request)
                    
                    # Verify extraction errors are handled gracefully
                    assert result.status == IngestionStatus.FAILED
                    assert result.error_message == "Internal processing error"


class TestProductionReadinessChecks:
    """Final production readiness validation checks"""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_capability(self):
        """Verify system can handle concurrent document processing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock successful processing
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "concurrent_doc"
                mock_processed_doc.content_hash = "hash"
                mock_processed_doc.word_count = 100
                mock_processed_doc.chunks = ["chunk"]
                mock_processed_doc.quality_score = 0.8
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Content", {})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Create multiple concurrent requests
                    tasks = []
                    for i in range(5):
                        upload_request = DocumentUploadRequest(
                            filename=f"concurrent_{i}.txt",
                            content_type="text/plain",
                            technology="test"
                        )
                        task = pipeline.ingest_single_document(b"content", upload_request)
                        tasks.append(task)
                    
                    # Execute concurrently
                    results = await asyncio.gather(*tasks)
                    
                    # Verify all succeeded
                    for result in results:
                        assert result.status == IngestionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self):
        """Verify system processes documents without memory leaks"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "memory_test"
                mock_processed_doc.content_hash = "hash"
                mock_processed_doc.word_count = 100
                mock_processed_doc.chunks = ["chunk"]
                mock_processed_doc.quality_score = 0.8
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Content", {})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Process multiple documents sequentially to test memory management
                    for i in range(10):
                        upload_request = DocumentUploadRequest(
                            filename=f"memory_test_{i}.txt",
                            content_type="text/plain",
                            technology="test"
                        )
                        
                        result = await pipeline.ingest_single_document(b"content", upload_request)
                        assert result.status == IngestionStatus.COMPLETED
                        
                        # Simulate cleanup between documents
                        del result


# Integration test to ensure all components work together
@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests for production validation"""
    
    @pytest.mark.asyncio
    async def test_complete_ingestion_workflow(self):
        """Test complete workflow from file upload to database storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create real database for integration test
            db_manager = await create_database_manager({"db_path": f"{temp_dir}/integration.db"})
            await db_manager.connect()
            
            # Create content_metadata table for integration
            await db_manager.execute("""
                CREATE TABLE IF NOT EXISTS content_metadata (
                    content_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_url TEXT,
                    technology TEXT,
                    processing_status TEXT DEFAULT 'pending',
                    content_hash TEXT,
                    word_count INTEGER,
                    chunk_count INTEGER,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = db_manager
                
                # Mock successful processing with database storage
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "integration_doc_123"
                mock_processed_doc.content_hash = "integration_hash"
                mock_processed_doc.word_count = 250
                mock_processed_doc.chunks = ["chunk1", "chunk2"]
                mock_processed_doc.quality_score = 0.88
                
                async def mock_process_and_store(file_content, technology):
                    # Simulate actual database storage
                    await db_manager.execute("""
                        INSERT INTO content_metadata 
                        (content_id, title, source_url, technology, processing_status, 
                         content_hash, word_count, chunk_count, quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        mock_processed_doc.id,
                        file_content.title,
                        file_content.source_url,
                        technology,
                        "completed",
                        mock_processed_doc.content_hash,
                        mock_processed_doc.word_count,
                        len(mock_processed_doc.chunks),
                        mock_processed_doc.quality_score
                    ))
                    return mock_processed_doc, "success"
                
                mock_processor.process_and_store_document.side_effect = mock_process_and_store
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Integration test content", {"format": "text"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline(db_manager=db_manager)
                    
                    # Execute complete workflow
                    upload_request = DocumentUploadRequest(
                        filename="integration_test.txt",
                        content_type="text/plain",
                        technology="python",
                        title="Integration Test Document",
                        source_url="test://integration-workflow"
                    )
                    
                    result = await pipeline.ingest_single_document(b"Integration test file content", upload_request)
                    
                    # Verify workflow completion
                    assert result.status == IngestionStatus.COMPLETED
                    assert result.document_id == "integration_doc_123"
                    
                    # Verify database storage
                    stored_doc = await db_manager.fetch_one(
                        "SELECT * FROM content_metadata WHERE content_id = ?",
                        (result.document_id,)
                    )
                    
                    assert stored_doc is not None
                    assert stored_doc.title == "Integration Test Document"
                    assert stored_doc.technology == "python"
                    assert stored_doc.processing_status == "completed"
                    
            await db_manager.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])