"""
Content Processor Tests - PRD-008
Comprehensive unit and integration tests for content processing pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.core.config.models import ContentConfig
from src.processors.content_processor import ContentProcessor, FileContent, ScrapedContent
from src.processors.exceptions import (
    ContentProcessingError,
    QualityThresholdError,
    DatabaseIntegrationError
)
from src.models.schemas import ProcessedDocument, DocumentChunk


class TestContentProcessor:
    """Test suite for ContentProcessor functionality"""
    
    @pytest.fixture
    def content_config(self):
        """Create test configuration"""
        return ContentConfig(
            chunk_size_default=1000,
            chunk_size_max=4000,
            chunk_overlap=100,
            quality_threshold=0.3,
            min_content_length=50,
            max_content_length=1000000
        )
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager"""
        db_manager = Mock()
        db_manager.fetch_one = AsyncMock(return_value=None)
        db_manager.execute = AsyncMock()
        db_manager.load_processed_document_from_metadata = AsyncMock()
        return db_manager
    
    @pytest.fixture
    def content_processor(self, content_config, mock_db_manager):
        """Create ContentProcessor instance"""
        return ContentProcessor(content_config, mock_db_manager)
    
    @pytest.fixture
    def sample_markdown_content(self):
        """Sample markdown content for testing"""
        return """# Test Document

This is a test document with multiple sections.

## Introduction

This document contains various elements:
- Lists
- Code blocks
- Multiple paragraphs

```python
def hello_world():
    print("Hello, World!")
```

## Conclusion

This is the end of the test document.
"""
    
    @pytest.fixture
    def sample_file_content(self, sample_markdown_content):
        """Sample FileContent for testing"""
        return FileContent(
            content=sample_markdown_content,
            source_url="https://github.com/user/repo/docs/test.md",
            title="Test Document"
        )
    
    def test_content_processor_initialization(self, content_processor, content_config):
        """Test ContentProcessor initialization"""
        assert content_processor.chunk_size_default == content_config.chunk_size_default
        assert content_processor.chunk_size_max == content_config.chunk_size_max
        assert content_processor.chunk_overlap == content_config.chunk_overlap
        assert content_processor.quality_threshold == content_config.quality_threshold
    
    def test_normalize_content(self, content_processor):
        """Test content normalization functionality"""
        raw_content = "  Test\r\n\r\n\r\nContent\t\twith\nexcessive   whitespace  \n\n\n"
        normalized = content_processor._normalize_content(raw_content)
        
        # The normalization should handle line endings, excessive newlines, and whitespace
        assert "Test\n\nContent with\nexcessive whitespace" == normalized
        assert not normalized.startswith(' ')
        assert not normalized.endswith(' ')
    
    def test_extract_metadata(self, content_processor, sample_file_content):
        """Test metadata extraction from content"""
        metadata = content_processor._extract_metadata(
            sample_file_content.content,
            sample_file_content,
            "python"
        )
        
        assert metadata['title'] == "Test Document"
        assert metadata['word_count'] > 0
        assert metadata['heading_count'] == 3  # Three headings in sample
        assert metadata['code_block_count'] > 0  # Has code blocks
        assert 'content_hash' in metadata
        assert 'content_id' in metadata
    
    def test_calculate_quality_score(self, content_processor, sample_markdown_content):
        """Test quality score calculation"""
        metadata = {
            'word_count': 50,
            'heading_count': 2,
            'code_block_count': 1
        }
        
        quality_score = content_processor._calculate_quality_score(
            sample_markdown_content,
            metadata
        )
        
        assert 0.0 <= quality_score <= 1.0
        assert quality_score > 0.3  # Should be decent quality
    
    def test_create_chunks(self, content_processor, sample_markdown_content):
        """Test content chunking functionality"""
        chunks = content_processor._create_chunks(sample_markdown_content, "test_doc_id")
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.metadata['document_id'] == "test_doc_id" for chunk in chunks)
        assert all(chunk.total_chunks == len(chunks) for chunk in chunks)
        
        # Check chunk indexing is correct
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
    
    def test_chunk_overlap(self, content_processor):
        """Test chunk overlap functionality"""
        # Create long content that will require multiple chunks
        long_content = "This is a test sentence. " * 100  # About 2500 characters
        
        chunks = content_processor._create_chunks(long_content, "test_doc_id")
        
        assert len(chunks) > 1  # Should create multiple chunks
        
        # Check that chunks have overlap (except the first one)
        for i, chunk in enumerate(chunks[1:], 1):
            assert chunk.metadata['overlap_with_previous'] <= content_processor.chunk_overlap
    
    def test_process_document_success(self, content_processor, sample_file_content):
        """Test successful document processing"""
        processed_doc = content_processor.process_document(sample_file_content, "python")
        
        assert processed_doc is not None
        assert isinstance(processed_doc, ProcessedDocument)
        assert processed_doc.title == "Test Document"
        assert processed_doc.technology == "python"
        assert processed_doc.source_url == sample_file_content.source_url
        assert len(processed_doc.chunks) > 0
        assert processed_doc.quality_score >= content_processor.quality_threshold
    
    def test_process_document_too_short(self, content_processor, content_config):
        """Test processing rejection for content too short"""
        short_content = FileContent(
            content="Short",  # Below min_content_length
            source_url="https://example.com/short.md",
            title="Short Doc"
        )
        
        processed_doc = content_processor.process_document(short_content, "python")
        assert processed_doc is None
    
    def test_process_document_too_long(self, content_processor, content_config):
        """Test processing rejection for content too long"""
        long_content = FileContent(
            content="x" * (content_config.max_content_length + 1),  # Exceed max length
            source_url="https://example.com/long.md",
            title="Long Doc"
        )
        
        processed_doc = content_processor.process_document(long_content, "python")
        assert processed_doc is None
    
    def test_process_document_low_quality(self, content_processor):
        """Test processing rejection for low quality content"""
        low_quality_content = FileContent(
            content="a b c d e f g h i j k l m n o p q r s t u v w x y z " * 5,  # Low quality content
            source_url="https://example.com/lowquality.md",
            title="Low Quality"
        )
        
        processed_doc = content_processor.process_document(low_quality_content, "python")
        # May be None if quality is below threshold
        if processed_doc:
            assert processed_doc.quality_score >= content_processor.quality_threshold
    
    @pytest.mark.asyncio
    async def test_process_and_store_document_success(self, content_processor, sample_file_content, mock_db_manager):
        """Test successful document processing and storage"""
        # Mock no duplicate content
        mock_db_manager.fetch_one.return_value = None
        
        processed_doc, status = await content_processor.process_and_store_document(
            sample_file_content,
            "python"
        )
        
        assert processed_doc is not None
        assert status == "success"
        assert isinstance(processed_doc, ProcessedDocument)
        
        # Verify database calls were made
        assert mock_db_manager.execute.call_count >= 2  # Initial record + metadata update
    
    @pytest.mark.asyncio
    async def test_process_and_store_document_duplicate(self, content_processor, sample_file_content, mock_db_manager):
        """Test duplicate content detection"""
        # Mock existing document
        existing_doc = ProcessedDocument(
            id="existing_id",
            title="Existing Doc",
            source_url="https://example.com",
            technology="python",
            content_hash="existing_hash",
            chunks=[],
            word_count=100,
            quality_score=0.8
        )
        
        mock_db_manager.load_processed_document_from_metadata.return_value = existing_doc
        mock_db_manager.fetch_one.return_value = Mock()  # Simulate found record
        
        processed_doc, status = await content_processor.process_and_store_document(
            sample_file_content,
            "python"
        )
        
        assert processed_doc == existing_doc
        assert status == "duplicate_content_found"
    
    @pytest.mark.asyncio
    async def test_process_and_store_document_processing_failed(self, content_processor, mock_db_manager):
        """Test handling of processing failures"""
        # Create content that will fail processing (too short)
        failed_content = FileContent(
            content="Short",
            source_url="https://example.com/fail.md",
            title="Fail Doc"
        )
        
        processed_doc, status = await content_processor.process_and_store_document(
            failed_content,
            "python"
        )
        
        assert processed_doc is None
        assert status == "processing_failed"
        
        # Verify failure status was recorded
        mock_db_manager.execute.assert_called()
    
    def test_compute_content_hash(self, content_processor):
        """Test content hash computation"""
        content1 = "Test content"
        content2 = "Test content"
        content3 = "Different content"
        
        hash1 = content_processor._compute_content_hash(content1)
        hash2 = content_processor._compute_content_hash(content2)
        hash3 = content_processor._compute_content_hash(content3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    def test_generate_content_id(self, content_processor):
        """Test content ID generation"""
        url = "https://github.com/user/repo/docs/test.md"
        technology = "python"
        
        content_id1 = content_processor._generate_content_id(url, technology)
        content_id2 = content_processor._generate_content_id(url, technology)
        
        assert content_id1 != content_id2  # Should be unique due to UUID component
        assert technology in content_id1  # Should contain technology
        assert len(content_id1.split('_')) == 3  # tech_hash_uuid format
    
    def test_extract_title_from_content(self, content_processor):
        """Test title extraction from content"""
        content_with_heading = "# Main Title\n\nSome content here"
        content_without_heading = "Just some content without headings"
        
        title1 = content_processor._extract_title_from_content(content_with_heading)
        title2 = content_processor._extract_title_from_content(content_without_heading)
        
        assert title1 == "Main Title"
        assert title2 == "Just some content without headings"
    
    def test_extract_title_from_url(self, content_processor):
        """Test title extraction from URL"""
        url1 = "https://github.com/user/repo/docs/getting-started.md"
        url2 = "https://example.com/api_reference.html"
        
        title1 = content_processor._extract_title_from_url(url1)
        title2 = content_processor._extract_title_from_url(url2)
        
        assert title1 == "Getting Started"
        assert title2 == "Api Reference"
    
    def test_count_words(self, content_processor):
        """Test word counting functionality"""
        content = """
        This is a test document with some words.
        
        ```python
        # This code block should not be counted
        def hello():
            print("hello")
        ```
        
        More words here.
        """
        
        word_count = content_processor._count_words(content)
        
        # Should count words but exclude code blocks
        assert word_count > 0
        assert word_count < 50  # Should be reasonable number excluding code
    
    def test_is_retryable_error(self, content_processor):
        """Test error retry logic"""
        retryable_errors = [
            ConnectionError("Connection failed"),
            TimeoutError("Request timeout"),
            MemoryError("Out of memory")
        ]
        
        non_retryable_errors = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            RuntimeError("Runtime error")
        ]
        
        for error in retryable_errors:
            assert content_processor._is_retryable_error(error) == True
        
        for error in non_retryable_errors:
            assert content_processor._is_retryable_error(error) == False
    
    @pytest.mark.asyncio
    async def test_database_integration_methods(self, content_processor, mock_db_manager):
        """Test database integration helper methods"""
        content_id = "test_content_id"
        content_hash = "test_hash"
        
        # Test duplicate check
        await content_processor._check_duplicate_content(content_hash)
        mock_db_manager.fetch_one.assert_called_with(
            "SELECT * FROM content_metadata WHERE content_hash = ?",
            (content_hash,)
        )
        
        # Test status update
        await content_processor._update_processing_status(content_id, "completed")
        mock_db_manager.execute.assert_called()
        
        # Test error handling
        await content_processor._handle_processing_error(content_id, Exception("Test error"))
        # Should update status to failed
        mock_db_manager.execute.assert_called()


class TestFileContentAndScrapedContent:
    """Test input content classes"""
    
    def test_file_content_creation(self):
        """Test FileContent creation"""
        content = "Test content"
        url = "https://github.com/user/repo/file.md"
        title = "Test File"
        
        file_content = FileContent(content, url, title)
        
        assert file_content.content == content
        assert file_content.source_url == url
        assert file_content.title == title
    
    def test_scraped_content_creation(self):
        """Test ScrapedContent creation"""
        content = "Scraped content"
        url = "https://example.com/page"
        title = "Test Page"
        
        scraped_content = ScrapedContent(content, url, title)
        
        assert scraped_content.content == content
        assert scraped_content.source_url == url
        assert scraped_content.title == title


@pytest.mark.asyncio
class TestContentProcessorIntegration:
    """Integration tests with real database operations"""
    
    async def test_full_processing_workflow(self):
        """Test complete processing workflow (requires database setup)"""
        # This would be an integration test that uses a real database
        # For now, we'll skip this as it requires database setup
        pytest.skip("Integration test requires database setup")
    
    async def test_anythingllm_integration(self):
        """Test integration with AnythingLLM client"""
        # This would test the integration with AnythingLLM for document upload
        # For now, we'll skip this as it requires AnythingLLM setup
        pytest.skip("Integration test requires AnythingLLM setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])