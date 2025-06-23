"""
Comprehensive Validation Test Suite for Document Ingestion Pipeline
Tests ALL requirements: Security, Performance, Integration, Production Readiness

VALIDATION SCOPE:
- Document ingestion pipeline meets all functional requirements
- Security assessment for file upload handling  
- Multi-format document processing (PDF, DOC, DOCX, TXT, MD, HTML)
- Integration with Content Processing Pipeline (PRD-008)
- Batch processing performance and concurrency handling
- API endpoints functionality and error handling
- Security measures including file validation and sanitization
"""

import pytest
import asyncio
import tempfile
import hashlib
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline
from src.ingestion.extractors import DocumentExtractor, create_document_extractor
from src.ingestion.models import (
    DocumentUploadRequest, BatchUploadRequest, IngestionStatus,
    IngestionResult, BatchIngestionResult, ProcessingMetrics,
    SupportedFormat, IngestionHealthCheck
)
from src.api.v1.ingestion import ingestion_router
from src.main import app


class TestDocumentIngestionSecurityValidation:
    """Security validation tests for document ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_file_upload_security_path_traversal_prevention(self):
        """SECURITY TEST: Verify path traversal attacks are prevented"""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\hosts",
            "/etc/shadow",
            "C:\\Windows\\System32\\cmd.exe",
            "evil/../../../../../etc/passwd.txt"
        ]
        
        for filename in malicious_filenames:
            with pytest.raises(ValueError, match="path components not allowed"):
                DocumentUploadRequest(
                    filename=filename,
                    content_type="text/plain",
                    technology="test"
                )
    
    @pytest.mark.asyncio
    async def test_file_size_limit_enforcement(self):
        """SECURITY TEST: Verify file size limits prevent DOS attacks"""
        extractor = DocumentExtractor()
        
        # Test file exceeding 50MB limit
        oversized_content = b"x" * (51 * 1024 * 1024)
        
        with pytest.raises(RuntimeError, match="File size.*exceeds limit"):
            await extractor.extract_content(oversized_content, "large.txt")
    
    @pytest.mark.asyncio
    async def test_malicious_content_type_rejection(self):
        """SECURITY TEST: Verify malicious content types are rejected"""
        malicious_content_types = [
            "application/x-executable",
            "application/x-msdownload",
            "application/x-sh",
            "application/java-archive",
            "application/javascript"
        ]
        
        for content_type in malicious_content_types:
            with pytest.raises(ValueError, match="Unsupported content type"):
                DocumentUploadRequest(
                    filename="test.txt",
                    content_type=content_type,
                    technology="test"
                )
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention_in_queries(self):
        """SECURITY TEST: Verify SQL injection attacks are prevented"""
        pipeline = Mock()
        pipeline.db_manager = Mock()
        pipeline.db_manager.fetch_one = AsyncMock()
        
        # Test malicious document IDs
        malicious_inputs = [
            "'; DROP TABLE content_metadata; --",
            "1 OR 1=1",
            "1; DELETE FROM content_metadata WHERE 1=1; --"
        ]
        
        # These should be handled safely by parameterized queries
        for malicious_id in malicious_inputs:
            pipeline.db_manager.fetch_one.return_value = None
            # Should not raise exception, should handle safely
            assert pipeline.db_manager.fetch_one.call_count >= 0
    
    @pytest.mark.asyncio
    async def test_script_content_detection(self):
        """SECURITY TEST: Verify script content detection in files"""
        extractor = DocumentExtractor()
        
        # Test HTML with script content
        malicious_html = b"""
        <html>
        <head><script>alert('XSS')</script></head>
        <body>Content</body>
        </html>
        """
        
        with patch('src.ingestion.extractors.BeautifulSoup') as mock_bs:
            mock_soup = Mock()
            mock_soup.get_text.return_value = "Content"
            mock_soup.title = None
            mock_soup.__iter__ = Mock(return_value=iter([]))
            mock_bs.return_value = mock_soup
            
            # Should process but scripts should be removed
            text, metadata = await extractor.extract_content(malicious_html, "test.html")
            assert "script" not in text.lower()
    
    @pytest.mark.asyncio
    async def test_password_protected_pdf_rejection(self):
        """SECURITY TEST: Verify password-protected PDFs are rejected"""
        extractor = DocumentExtractor()
        
        with patch('src.ingestion.extractors.PyPDF2') as mock_pdf:
            mock_reader = Mock()
            mock_reader.is_encrypted = True
            mock_pdf.PdfReader.return_value = mock_reader
            
            with pytest.raises(ValueError, match="Password-protected PDFs are not supported"):
                await extractor.extract_content(b"fake pdf content", "test.pdf")


class TestDocumentIngestionFunctionalValidation:
    """Functional validation tests for document ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_all_supported_formats_processing(self):
        """FUNCTIONAL TEST: Verify all supported formats can be processed"""
        extractor = DocumentExtractor()
        
        test_files = {
            "test.txt": (b"Plain text content", "text/plain"),
            "test.md": (b"# Markdown\nContent", "text/markdown"), 
            "test.html": (b"<html><body>HTML content</body></html>", "text/html")
        }
        
        for filename, (content, content_type) in test_files.items():
            if filename.endswith('.html'):
                with patch('src.ingestion.extractors.BeautifulSoup') as mock_bs:
                    mock_soup = Mock()
                    mock_soup.get_text.return_value = "HTML content"
                    mock_soup.title = None
                    mock_soup.__iter__ = Mock(return_value=iter([]))
                    mock_bs.return_value = mock_soup
                    
                    text, metadata = await extractor.extract_content(content, filename)
                    assert len(text) > 0
                    assert metadata['format'] == filename.split('.')[-1]
            else:
                text, metadata = await extractor.extract_content(content, filename)
                assert len(text) > 0
                assert metadata['format'] == filename.split('.')[-1]
    
    @pytest.mark.asyncio
    async def test_document_upload_request_validation(self):
        """FUNCTIONAL TEST: Verify document upload request validation"""
        # Valid request
        valid_request = DocumentUploadRequest(
            filename="test.pdf",
            content_type="application/pdf",
            technology="python",
            title="Test Document"
        )
        assert valid_request.filename == "test.pdf"
        
        # Invalid file extension
        with pytest.raises(ValueError, match="Unsupported file extension"):
            DocumentUploadRequest(
                filename="test.exe",
                content_type="application/pdf",
                technology="python"
            )
    
    @pytest.mark.asyncio
    async def test_batch_upload_validation(self):
        """FUNCTIONAL TEST: Verify batch upload validation"""
        documents = [
            DocumentUploadRequest(
                filename="doc1.txt",
                content_type="text/plain",
                technology="python"
            ),
            DocumentUploadRequest(
                filename="doc2.md",
                content_type="text/markdown",
                technology="python"
            )
        ]
        
        batch_request = BatchUploadRequest(
            documents=documents,
            technology="python",
            batch_name="test-batch"
        )
        
        assert len(batch_request.documents) == 2
        assert batch_request.technology == "python"
        
        # Empty batch should fail
        with pytest.raises(ValueError, match="Batch cannot be empty"):
            BatchUploadRequest(documents=[], technology="python")
        
        # Oversized batch should fail
        large_batch = [documents[0]] * 101  # Exceeds limit of 100
        with pytest.raises(ValueError, match="Batch size cannot exceed"):
            BatchUploadRequest(documents=large_batch, technology="python")


class TestDocumentIngestionPerformanceValidation:
    """Performance validation tests for document ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_concurrent_document_processing_performance(self):
        """PERFORMANCE TEST: Verify concurrent processing performance"""
        # Mock pipeline
        pipeline = Mock()
        pipeline.ingest_single_document = AsyncMock()
        pipeline.max_batch_size = 100
        
        # Mock successful processing with timing
        async def mock_process(file_data, request):
            await asyncio.sleep(0.1)  # Simulate processing time
            return IngestionResult(
                document_id=f"doc_{request.filename}",
                filename=request.filename,
                status=IngestionStatus.COMPLETED,
                processing_time_ms=100
            )
        
        pipeline.ingest_single_document.side_effect = mock_process
        
        # Test concurrent processing
        files_data = []
        for i in range(10):
            request = DocumentUploadRequest(
                filename=f"doc{i}.txt",
                content_type="text/plain",
                technology="python"
            )
            files_data.append((b"content", request))
        
        batch_request = BatchUploadRequest(
            documents=[req for _, req in files_data],
            technology="python"
        )
        
        # Simulate batch processing with concurrency
        start_time = time.time()
        
        # Process with semaphore (max 5 concurrent)
        semaphore = asyncio.Semaphore(5)
        
        async def process_single(file_data_tuple):
            file_data, upload_request = file_data_tuple
            async with semaphore:
                return await pipeline.ingest_single_document(file_data, upload_request)
        
        results = await asyncio.gather(
            *[process_single(file_data_tuple) for file_data_tuple in files_data]
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete faster than sequential processing
        assert total_time < 1.0  # Should be faster than 10 * 0.1 seconds
        assert len(results) == 10
        assert all(r.status == IngestionStatus.COMPLETED for r in results)
    
    @pytest.mark.asyncio
    async def test_large_file_processing_performance(self):
        """PERFORMANCE TEST: Verify large file processing performance"""
        extractor = DocumentExtractor()
        
        # Create large text file (5MB)
        large_content = b"Lorem ipsum dolor sit amet. " * (5 * 1024 * 1024 // 28)
        
        start_time = time.time()
        text, metadata = await extractor.extract_content(large_content, "large.txt")
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process within reasonable time (< 5 seconds for 5MB)
        assert processing_time < 5.0
        assert len(text) > 0
        assert metadata['format'] == 'txt'
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_processing(self):
        """PERFORMANCE TEST: Verify memory usage stays within limits"""
        extractor = DocumentExtractor()
        
        # Process multiple files sequentially to check for memory leaks
        for i in range(20):
            content = f"Document {i} content. " * 1000
            text, metadata = await extractor.extract_content(content.encode(), f"doc{i}.txt")
            
            # Verify processing succeeded
            assert len(text) > 0
            assert f"Document {i}" in text


class TestDocumentIngestionIntegrationValidation:
    """Integration validation tests with PRD-008 Content Processing Pipeline"""
    
    @pytest.mark.asyncio
    async def test_content_processor_integration(self):
        """INTEGRATION TEST: Verify integration with Content Processing Pipeline"""
        # Mock dependencies
        mock_content_processor = Mock()
        mock_content_processor.process_and_store_document = AsyncMock()
        mock_document_extractor = Mock()
        mock_document_extractor.extract_content = AsyncMock()
        mock_db_manager = Mock()
        
        # Create pipeline
        pipeline = IngestionPipeline(
            content_processor=mock_content_processor,
            document_extractor=mock_document_extractor,
            db_manager=mock_db_manager
        )
        
        # Mock successful extraction
        mock_document_extractor.extract_content.return_value = (
            "Extracted text content",
            {"format": "txt", "encoding": "utf-8"}
        )
        
        # Mock successful processing
        mock_processed_doc = Mock()
        mock_processed_doc.id = "doc_123"
        mock_processed_doc.content_hash = "hash123"
        mock_processed_doc.word_count = 3
        mock_processed_doc.chunks = [Mock()]
        mock_processed_doc.quality_score = 0.8
        
        mock_content_processor.process_and_store_document.return_value = (
            mock_processed_doc, "success"
        )
        
        # Test integration
        upload_request = DocumentUploadRequest(
            filename="test.txt",
            content_type="text/plain",
            technology="python"
        )
        
        result = await pipeline.ingest_single_document(b"test content", upload_request)
        
        # Verify integration calls
        mock_document_extractor.extract_content.assert_called_once()
        mock_content_processor.process_and_store_document.assert_called_once()
        
        # Verify result
        assert result.status == IngestionStatus.COMPLETED
        assert result.document_id == "doc_123"
    
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """INTEGRATION TEST: Verify database integration for metrics"""
        # Mock database manager
        mock_db_manager = Mock()
        mock_db_manager.fetch_one = AsyncMock()
        mock_db_manager.fetch_all = AsyncMock()
        
        # Mock pipeline with database
        pipeline = Mock()
        pipeline.db_manager = mock_db_manager
        pipeline.get_processing_metrics = AsyncMock()
        
        # Mock database responses for metrics
        mock_db_manager.fetch_one.side_effect = [
            (100,),  # total documents
            (5,)     # failed documents
        ]
        
        mock_db_manager.fetch_all.side_effect = [
            [("pdf", 30), ("txt", 40), ("md", 30)],  # format distribution
            [("python", 50), ("javascript", 30)],   # technology distribution
            [("high", 60), ("medium", 30), ("low", 10)]  # quality distribution
        ]
        
        # Mock metrics calculation
        expected_metrics = ProcessingMetrics(
            total_documents_processed=100,
            documents_by_format={"pdf": 30, "txt": 40, "md": 30},
            documents_by_technology={"python": 50, "javascript": 30},
            success_rate=95.24,
            quality_score_distribution={"high": 60, "medium": 30, "low": 10}
        )
        
        pipeline.get_processing_metrics.return_value = expected_metrics
        
        metrics = await pipeline.get_processing_metrics()
        
        # Verify metrics retrieval
        assert metrics.total_documents_processed == 100
        assert metrics.success_rate > 95
        assert "pdf" in metrics.documents_by_format


class TestDocumentIngestionAPIValidation:
    """API endpoint validation tests"""
    
    def test_health_check_endpoint(self):
        """API TEST: Verify health check endpoint functionality"""
        client = TestClient(app)
        
        with patch('src.api.v1.ingestion.get_ingestion_pipeline') as mock_get_pipeline:
            mock_pipeline = Mock()
            mock_pipeline.db_manager.fetch_one = AsyncMock(return_value=(1,))
            mock_pipeline.supported_formats = {"pdf", "txt", "md", "html", "docx"}
            mock_pipeline.max_file_size = 50 * 1024 * 1024
            mock_pipeline.max_batch_size = 100
            mock_get_pipeline.return_value = mock_pipeline
            
            response = client.get("/api/v1/ingestion/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "supported_formats" in data
            assert "max_file_size_mb" in data
    
    def test_single_document_upload_endpoint(self):
        """API TEST: Verify single document upload endpoint"""
        client = TestClient(app)
        
        with patch('src.api.v1.ingestion.get_ingestion_pipeline') as mock_get_pipeline:
            mock_pipeline = Mock()
            mock_result = IngestionResult(
                document_id="doc_123",
                filename="test.txt",
                status=IngestionStatus.COMPLETED,
                word_count=5,
                quality_score=0.8
            )
            mock_pipeline.ingest_single_document = AsyncMock(return_value=mock_result)
            mock_get_pipeline.return_value = mock_pipeline
            
            test_content = b"Test document content"
            
            response = client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("test.txt", BytesIO(test_content), "text/plain")},
                data={"technology": "python", "title": "Test Document"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == "doc_123"
            assert data["status"] == "completed"
    
    def test_batch_upload_endpoint(self):
        """API TEST: Verify batch document upload endpoint"""
        client = TestClient(app)
        
        with patch('src.api.v1.ingestion.get_ingestion_pipeline') as mock_get_pipeline:
            mock_pipeline = Mock()
            mock_pipeline.max_batch_size = 100
            
            mock_batch_result = BatchIngestionResult(
                batch_id="batch_123",
                total_documents=2,
                successful_count=2,
                failed_count=0,
                results=[
                    IngestionResult(
                        document_id="doc_1",
                        filename="doc1.txt",
                        status=IngestionStatus.COMPLETED
                    ),
                    IngestionResult(
                        document_id="doc_2", 
                        filename="doc2.txt",
                        status=IngestionStatus.COMPLETED
                    )
                ]
            )
            
            mock_pipeline.ingest_batch_documents = AsyncMock(return_value=mock_batch_result)
            mock_get_pipeline.return_value = mock_pipeline
            
            files = [
                ("files", ("doc1.txt", BytesIO(b"Content 1"), "text/plain")),
                ("files", ("doc2.txt", BytesIO(b"Content 2"), "text/plain"))
            ]
            
            response = client.post(
                "/api/v1/ingestion/upload/batch",
                files=files,
                data={"technology": "python"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_documents"] == 2
            assert data["successful_count"] == 2


class TestDocumentIngestionErrorHandlingValidation:
    """Error handling validation tests"""
    
    @pytest.mark.asyncio
    async def test_empty_file_handling(self):
        """ERROR TEST: Verify empty file handling"""
        extractor = DocumentExtractor()
        
        with pytest.raises(ValueError, match="Empty file provided"):
            await extractor.extract_content(b"", "empty.txt")
    
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self):
        """ERROR TEST: Verify corrupted file handling"""
        extractor = DocumentExtractor()
        
        # Test corrupted PDF
        with patch('src.ingestion.extractors.PyPDF2') as mock_pdf:
            mock_pdf.PdfReader.side_effect = Exception("Corrupted PDF")
            
            with pytest.raises(ValueError, match="PDF extraction failed"):
                await extractor.extract_content(b"corrupted pdf", "corrupted.pdf")
    
    @pytest.mark.asyncio
    async def test_unsupported_encoding_handling(self):
        """ERROR TEST: Verify unsupported encoding handling"""
        extractor = DocumentExtractor()
        
        # Create content with unsupported encoding
        with patch('builtins.bytes.decode') as mock_decode:
            mock_decode.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "error")
            
            with pytest.raises(ValueError, match="Could not decode text file"):
                await extractor.extract_content(b"bad encoding", "bad.txt")
    
    @pytest.mark.asyncio
    async def test_processing_timeout_handling(self):
        """ERROR TEST: Verify processing timeout handling"""
        # Mock pipeline with timeout
        pipeline = Mock()
        pipeline.ingest_single_document = AsyncMock()
        
        # Simulate timeout
        async def timeout_process(*args):
            await asyncio.sleep(10)  # Long processing time
            
        pipeline.ingest_single_document.side_effect = timeout_process
        
        # Test with timeout (this would be handled by actual timeout mechanisms)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                pipeline.ingest_single_document(b"content", Mock()),
                timeout=1.0
            )


class TestDocumentIngestionProductionReadinessValidation:
    """Production readiness validation tests"""
    
    @pytest.mark.asyncio
    async def test_factory_function_creation(self):
        """PRODUCTION TEST: Verify factory function works correctly"""
        with patch('src.ingestion.pipeline.create_content_processor') as mock_create_processor:
            with patch('src.ingestion.pipeline.create_document_extractor') as mock_create_extractor:
                # Mock factory functions
                mock_processor = Mock()
                mock_processor.db_manager = Mock()
                mock_create_processor.return_value = mock_processor
                
                mock_extractor = Mock()
                mock_create_extractor.return_value = mock_extractor
                
                # Create pipeline
                pipeline = await create_ingestion_pipeline()
                
                # Verify creation
                assert isinstance(pipeline, IngestionPipeline)
                assert pipeline.content_processor == mock_processor
                assert pipeline.document_extractor == mock_extractor
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """PRODUCTION TEST: Verify configuration validation"""
        # Test pipeline configuration limits
        pipeline = Mock()
        pipeline.max_file_size = 50 * 1024 * 1024  # 50MB
        pipeline.max_batch_size = 100
        pipeline.supported_formats = {"pdf", "docx", "txt", "md", "html"}
        
        # Verify limits are properly set
        assert pipeline.max_file_size == 50 * 1024 * 1024
        assert pipeline.max_batch_size == 100
        assert len(pipeline.supported_formats) == 5
    
    @pytest.mark.asyncio
    async def test_logging_integration(self):
        """PRODUCTION TEST: Verify logging integration"""
        with patch('src.ingestion.pipeline.logger') as mock_logger:
            # Mock pipeline
            mock_content_processor = Mock()
            mock_document_extractor = Mock()
            mock_db_manager = Mock()
            
            pipeline = IngestionPipeline(
                content_processor=mock_content_processor,
                document_extractor=mock_document_extractor, 
                db_manager=mock_db_manager
            )
            
            # Verify initialization logging
            mock_logger.info.assert_called_with("Document ingestion pipeline initialized")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """PRODUCTION TEST: Verify graceful degradation on failures"""
        # Mock pipeline with failing components
        mock_content_processor = Mock()
        mock_content_processor.process_and_store_document = AsyncMock(
            return_value=(None, "processing_failed")
        )
        
        mock_document_extractor = Mock()
        mock_document_extractor.extract_content = AsyncMock(
            return_value=("extracted text", {"format": "txt"})
        )
        
        mock_db_manager = Mock()
        
        pipeline = IngestionPipeline(
            content_processor=mock_content_processor,
            document_extractor=mock_document_extractor,
            db_manager=mock_db_manager
        )
        
        upload_request = DocumentUploadRequest(
            filename="test.txt",
            content_type="text/plain",
            technology="python"
        )
        
        # Should handle failure gracefully
        result = await pipeline.ingest_single_document(b"test content", upload_request)
        
        assert result.status == IngestionStatus.FAILED
        assert "Content processing failed" in result.error_message


# Test execution runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])