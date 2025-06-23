"""
Test suite for Document Ingestion Pipeline
Comprehensive testing of file upload, content extraction, and processing workflows
"""

import pytest
import asyncio
from io import BytesIO
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline
from src.ingestion.models import (
    DocumentUploadRequest, BatchUploadRequest, IngestionStatus,
    IngestionResult, BatchIngestionResult
)
from src.ingestion.extractors import DocumentExtractor


@pytest.fixture
async def mock_content_processor():
    """Mock content processor for testing"""
    processor = Mock()
    processor.process_and_store_document = AsyncMock()
    processor.db_manager = Mock()
    processor.db_manager.fetch_one = AsyncMock()
    processor.db_manager.fetch_all = AsyncMock()
    processor.db_manager.execute = AsyncMock()
    return processor


@pytest.fixture
async def mock_document_extractor():
    """Mock document extractor for testing"""
    extractor = Mock()
    extractor.extract_content = AsyncMock()
    extractor.supported_formats = {'pdf', 'doc', 'docx', 'txt', 'md', 'html'}
    return extractor


@pytest.fixture
async def mock_db_manager():
    """Mock database manager for testing"""
    db = Mock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
async def ingestion_pipeline(mock_content_processor, mock_document_extractor, mock_db_manager):
    """Create ingestion pipeline with mocked dependencies"""
    return IngestionPipeline(
        content_processor=mock_content_processor,
        document_extractor=mock_document_extractor,
        db_manager=mock_db_manager
    )


class TestDocumentExtractor:
    """Test document content extraction functionality"""
    
    @pytest.mark.asyncio
    async def test_extract_text_file(self):
        """Test extraction from plain text file"""
        extractor = DocumentExtractor()
        content = "This is a test document with some content."
        file_data = content.encode('utf-8')
        
        extracted_text, metadata = await extractor.extract_content(file_data, "test.txt")
        
        assert extracted_text == content
        assert metadata['format'] == 'txt'
        assert metadata['encoding'] == 'utf-8'
    
    @pytest.mark.asyncio
    async def test_extract_markdown_file(self):
        """Test extraction from markdown file"""
        extractor = DocumentExtractor()
        content = "# Test Document\n\nThis is **markdown** content."
        file_data = content.encode('utf-8')
        
        extracted_text, metadata = await extractor.extract_content(file_data, "test.md")
        
        assert extracted_text == content
        assert metadata['format'] == 'md'
    
    @pytest.mark.asyncio
    async def test_extract_html_file(self):
        """Test extraction from HTML file"""
        extractor = DocumentExtractor()
        html_content = "<html><body><h1>Test</h1><p>Content</p></body></html>"
        file_data = html_content.encode('utf-8')
        
        with patch('src.ingestion.extractors.BeautifulSoup') as mock_bs:
            mock_soup = Mock()
            mock_soup.get_text.return_value = "Test\nContent"
            mock_soup.title = None
            mock_soup.__iter__ = Mock(return_value=iter([]))
            mock_bs.return_value = mock_soup
            
            extracted_text, metadata = await extractor.extract_content(file_data, "test.html")
            
            assert "Test" in extracted_text
            assert metadata['format'] == 'html'
    
    @pytest.mark.asyncio
    async def test_unsupported_format_rejection(self):
        """Test rejection of unsupported file formats"""
        extractor = DocumentExtractor()
        file_data = b"test content"
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            await extractor.extract_content(file_data, "test.xyz")
    
    @pytest.mark.asyncio
    async def test_file_size_limit(self):
        """Test file size limit enforcement"""
        extractor = DocumentExtractor()
        # Create file larger than 50MB limit
        large_content = b"x" * (51 * 1024 * 1024)
        
        with pytest.raises(RuntimeError, match="File size.*exceeds limit"):
            await extractor.extract_content(large_content, "test.txt")
    
    @pytest.mark.asyncio
    async def test_empty_file_rejection(self):
        """Test rejection of empty files"""
        extractor = DocumentExtractor()
        
        with pytest.raises(ValueError, match="Empty file provided"):
            await extractor.extract_content(b"", "test.txt")


class TestIngestionPipeline:
    """Test document ingestion pipeline functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_single_document_ingestion(self, ingestion_pipeline):
        """Test successful processing of a single document"""
        # Setup mocks
        file_data = b"Test document content for processing"
        upload_request = DocumentUploadRequest(
            filename="test.txt",
            content_type="text/plain",
            technology="python",
            title="Test Document"
        )
        
        # Mock successful extraction
        ingestion_pipeline.document_extractor.extract_content.return_value = (
            "Test document content for processing",
            {"format": "txt", "encoding": "utf-8"}
        )
        
        # Mock successful processing
        mock_processed_doc = Mock()
        mock_processed_doc.id = "doc_123456789abc"
        mock_processed_doc.content_hash = "hash123"
        mock_processed_doc.word_count = 5
        mock_processed_doc.chunks = [Mock(), Mock()]  # 2 chunks
        mock_processed_doc.quality_score = 0.8
        
        ingestion_pipeline.content_processor.process_and_store_document.return_value = (
            mock_processed_doc, "success"
        )
        
        # Execute ingestion
        result = await ingestion_pipeline.ingest_single_document(file_data, upload_request)
        
        # Verify result
        assert result.status == IngestionStatus.COMPLETED
        assert result.document_id == "doc_123456789abc"
        assert result.filename == "test.txt"
        assert result.word_count == 5
        assert result.chunk_count == 2
        assert result.quality_score == 0.8
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_file_security_validation_failure(self, ingestion_pipeline):
        """Test security validation failure for oversized files"""
        large_file_data = b"x" * (51 * 1024 * 1024)  # 51MB
        upload_request = DocumentUploadRequest(
            filename="large.txt",
            content_type="text/plain",
            technology="python"
        )
        
        result = await ingestion_pipeline.ingest_single_document(large_file_data, upload_request)
        
        assert result.status == IngestionStatus.REJECTED
        assert "exceeds limit" in result.error_message
    
    @pytest.mark.asyncio
    async def test_content_extraction_failure(self, ingestion_pipeline):
        """Test handling of content extraction failures"""
        file_data = b"test content"
        upload_request = DocumentUploadRequest(
            filename="test.txt",
            content_type="text/plain",
            technology="python"
        )
        
        # Mock extraction failure
        ingestion_pipeline.document_extractor.extract_content.side_effect = ValueError("Extraction failed")
        
        result = await ingestion_pipeline.ingest_single_document(file_data, upload_request)
        
        assert result.status == IngestionStatus.REJECTED
        assert "Extraction failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_insufficient_content_rejection(self, ingestion_pipeline):
        """Test rejection of documents with insufficient content"""
        file_data = b"short"
        upload_request = DocumentUploadRequest(
            filename="short.txt",
            content_type="text/plain",
            technology="python"
        )
        
        # Mock extraction returning minimal content
        ingestion_pipeline.document_extractor.extract_content.return_value = (
            "short", {"format": "txt"}
        )
        
        result = await ingestion_pipeline.ingest_single_document(file_data, upload_request)
        
        assert result.status == IngestionStatus.REJECTED
        assert "Insufficient text content" in result.error_message
    
    @pytest.mark.asyncio
    async def test_content_processing_failure(self, ingestion_pipeline):
        """Test handling of content processing failures"""
        file_data = b"Test document content for processing"
        upload_request = DocumentUploadRequest(
            filename="test.txt",
            content_type="text/plain",
            technology="python"
        )
        
        # Mock successful extraction
        ingestion_pipeline.document_extractor.extract_content.return_value = (
            "Test document content for processing",
            {"format": "txt"}
        )
        
        # Mock processing failure
        ingestion_pipeline.content_processor.process_and_store_document.return_value = (
            None, "processing_failed"
        )
        
        result = await ingestion_pipeline.ingest_single_document(file_data, upload_request)
        
        assert result.status == IngestionStatus.FAILED
        assert "Content processing failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_batch_document_ingestion(self, ingestion_pipeline):
        """Test batch processing of multiple documents"""
        # Prepare test data
        files_data = [
            (b"Content 1", DocumentUploadRequest(
                filename="doc1.txt", content_type="text/plain", technology="python"
            )),
            (b"Content 2", DocumentUploadRequest(
                filename="doc2.txt", content_type="text/plain", technology="python"
            ))
        ]
        
        batch_request = BatchUploadRequest(
            documents=[req for _, req in files_data],
            technology="python",
            batch_name="test-batch"
        )
        
        # Mock successful processing for both documents
        mock_doc1 = Mock()
        mock_doc1.id = "doc_1"
        mock_doc1.content_hash = "hash1"
        mock_doc1.word_count = 5
        mock_doc1.chunks = [Mock()]
        mock_doc1.quality_score = 0.8
        
        mock_doc2 = Mock()
        mock_doc2.id = "doc_2"
        mock_doc2.content_hash = "hash2"
        mock_doc2.word_count = 5
        mock_doc2.chunks = [Mock()]
        mock_doc2.quality_score = 0.7
        
        ingestion_pipeline.document_extractor.extract_content.side_effect = [
            ("Content 1", {"format": "txt"}),
            ("Content 2", {"format": "txt"})
        ]
        
        ingestion_pipeline.content_processor.process_and_store_document.side_effect = [
            (mock_doc1, "success"),
            (mock_doc2, "success")
        ]
        
        # Execute batch ingestion
        result = await ingestion_pipeline.ingest_batch_documents(files_data, batch_request)
        
        # Verify results
        assert result.batch_name == "test-batch"
        assert result.total_documents == 2
        assert result.successful_count == 2
        assert result.failed_count == 0
        assert len(result.results) == 2
        assert all(r.status == IngestionStatus.COMPLETED for r in result.results)
    
    @pytest.mark.asyncio
    async def test_batch_size_limit(self, ingestion_pipeline):
        """Test enforcement of batch size limits"""
        # Create batch exceeding limit
        files_data = []
        for i in range(101):  # Exceeds max_batch_size of 100
            files_data.append((
                b"content",
                DocumentUploadRequest(
                    filename=f"doc{i}.txt",
                    content_type="text/plain",
                    technology="python"
                )
            ))
        
        batch_request = BatchUploadRequest(
            documents=[req for _, req in files_data],
            technology="python"
        )
        
        with pytest.raises(ValueError, match="Batch size.*exceeds maximum"):
            await ingestion_pipeline.ingest_batch_documents(files_data, batch_request)
    
    @pytest.mark.asyncio
    async def test_processing_metrics_retrieval(self, ingestion_pipeline):
        """Test retrieval of processing metrics"""
        # Mock database responses
        ingestion_pipeline.db_manager.fetch_one.side_effect = [
            (100,),  # total documents
            (5,)     # failed documents
        ]
        
        ingestion_pipeline.db_manager.fetch_all.side_effect = [
            [("pdf", 30), ("txt", 40), ("md", 30)],  # format distribution
            [("python", 50), ("javascript", 30), ("java", 20)],  # technology distribution
            [("high", 60), ("medium", 30), ("low", 10)]  # quality distribution
        ]
        
        metrics = await ingestion_pipeline.get_processing_metrics()
        
        assert metrics.total_documents_processed == 100
        assert metrics.success_rate == pytest.approx(95.24, abs=0.01)  # 100/(100+5)*100
        assert "pdf" in metrics.documents_by_format
        assert "python" in metrics.documents_by_technology
        assert "high" in metrics.quality_score_distribution


class TestIngestionModels:
    """Test Pydantic models for validation"""
    
    def test_document_upload_request_validation(self):
        """Test validation of document upload requests"""
        # Valid request
        request = DocumentUploadRequest(
            filename="test.pdf",
            content_type="application/pdf",
            technology="python",
            title="Test Document"
        )
        assert request.filename == "test.pdf"
        assert request.technology == "python"
    
    def test_invalid_filename_rejection(self):
        """Test rejection of invalid filenames"""
        with pytest.raises(ValueError, match="path components not allowed"):
            DocumentUploadRequest(
                filename="../evil.txt",
                content_type="text/plain",
                technology="python"
            )
    
    def test_unsupported_content_type_rejection(self):
        """Test rejection of unsupported content types"""
        with pytest.raises(ValueError, match="Unsupported content type"):
            DocumentUploadRequest(
                filename="test.exe",
                content_type="application/x-executable",
                technology="python"
            )
    
    def test_batch_upload_request_validation(self):
        """Test validation of batch upload requests"""
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
    
    def test_empty_batch_rejection(self):
        """Test rejection of empty batches"""
        with pytest.raises(ValueError, match="Batch cannot be empty"):
            BatchUploadRequest(
                documents=[],
                technology="python"
            )


@pytest.mark.asyncio
async def test_create_ingestion_pipeline():
    """Test factory function for creating ingestion pipeline"""
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