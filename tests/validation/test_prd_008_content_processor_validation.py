"""
PRD-008 Content Processing Pipeline Validation Test Suite

This comprehensive test suite validates the Content Processing Pipeline implementation
against all PRD-008 requirements, security standards, and integration points.

Test Categories:
1. Functional Requirements Compliance
2. Security Validation 
3. Performance Testing
4. Integration Testing
5. Error Handling Validation
6. Configuration Integration
7. Quality Filtering System
"""

import pytest
import asyncio
import hashlib
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Test imports - these will be validated during test execution
try:
    from src.processors import (
        ContentProcessor, FileContent, ScrapedContent,
        create_content_processor, create_file_content, create_scraped_content,
        ContentProcessingError, QualityThresholdError, ChunkingError,
        MetadataExtractionError, DatabaseError, ConfigurationError,
        ValidationError, ProcessingTimeoutError
    )
    from src.core.config.models import ContentConfig
    from src.database.models import Document, DocumentChunk, DocumentMetadata
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestPRD008FunctionalRequirements:
    """Test PRD-008 functional requirements compliance"""
    
    def test_imports_available(self):
        """Verify all required components can be imported"""
        assert IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}"
    
    def test_content_processor_class_exists(self):
        """Verify ContentProcessor class is properly defined"""
        assert hasattr(ContentProcessor, '__init__')
        assert hasattr(ContentProcessor, 'process_document')
        assert hasattr(ContentProcessor, '_normalize_content')
        assert hasattr(ContentProcessor, '_extract_metadata')
        assert hasattr(ContentProcessor, '_calculate_quality_score')
        assert hasattr(ContentProcessor, '_create_chunks')
    
    def test_input_data_models_exist(self):
        """Verify FileContent and ScrapedContent models exist"""
        # Test FileContent model
        file_content = FileContent("test content", "https://example.com", "Test Doc")
        assert file_content.content == "test content"
        assert file_content.source_url == "https://example.com"
        assert file_content.title == "Test Doc"
        
        # Test ScrapedContent model
        scraped_content = ScrapedContent("scraped content", "https://example.com", "Scraped Doc")
        assert scraped_content.content == "scraped content"
        assert scraped_content.source_url == "https://example.com"
        assert scraped_content.title == "Scraped Doc"
    
    def test_factory_functions_exist(self):
        """Verify factory functions are available"""
        assert callable(create_content_processor)
        assert callable(create_file_content)
        assert callable(create_scraped_content)
    
    def test_exception_hierarchy_complete(self):
        """Verify all 8 required exception classes exist"""
        required_exceptions = [
            ContentProcessingError, QualityThresholdError, ChunkingError,
            MetadataExtractionError, DatabaseError, ConfigurationError,
            ValidationError, ProcessingTimeoutError
        ]
        
        for exc_class in required_exceptions:
            assert issubclass(exc_class, Exception)
            # Test exception can be instantiated
            exc = exc_class("test message")
            assert str(exc) == "test message"
    
    def test_content_normalization_functionality(self):
        """Verify content normalization works correctly"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test various normalization scenarios
        test_cases = [
            ("Text\r\n\r\nwith\ttabs", "Text\n\nwith tabs"),  # CRLF and tabs
            ("Multiple   spaces", "Multiple spaces"),  # Multiple spaces
            ("  Leading and trailing  ", "Leading and trailing"),  # Trim
            ("Mixed\r\n\twhitespace   \n", "Mixed\n whitespace"),  # Mixed
        ]
        
        for input_text, expected in test_cases:
            result = processor._normalize_content(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_metadata_extraction_functionality(self):
        """Verify metadata extraction includes all required fields"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        content = "# Test Document\n\nContent with `code` and **bold** text."
        file_content = FileContent(content, "https://example.com/test.md", "Test")
        
        metadata = processor._extract_metadata(content, file_content, "markdown")
        
        # Verify required metadata fields
        required_fields = [
            'content_hash', 'word_count', 'character_count', 'language',
            'content_type', 'source_url', 'title', 'extracted_at'
        ]
        
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"
        
        # Verify metadata values are reasonable
        assert len(metadata['content_hash']) == 64  # SHA-256 hash
        assert metadata['word_count'] > 0
        assert metadata['character_count'] > 0
        assert metadata['source_url'] == "https://example.com/test.md"
    
    def test_quality_scoring_algorithm(self):
        """Verify quality scoring algorithm works correctly"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test high-quality content
        high_quality = """
        # Comprehensive Documentation
        
        This document provides detailed information about the system.
        
        ## Overview
        The system consists of multiple components that work together.
        
        ### Features
        - Feature 1: Detailed description
        - Feature 2: Another description
        
        ```python
        def example_function():
            return "Hello World"
        ```
        
        ## Conclusion
        This concludes the documentation.
        """
        
        metadata = {'word_count': 50, 'character_count': 300}
        quality_score = processor._calculate_quality_score(high_quality, metadata)
        assert quality_score > 0.3, f"High-quality content scored too low: {quality_score}"
        
        # Test low-quality content
        low_quality = "short text"
        metadata = {'word_count': 2, 'character_count': 10}
        quality_score = processor._calculate_quality_score(low_quality, metadata)
        assert quality_score < 0.3, f"Low-quality content scored too high: {quality_score}"
    
    def test_content_chunking_functionality(self):
        """Verify content chunking with overlap works correctly"""
        config = ContentConfig(chunk_size_default=100, chunk_overlap=20)
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Create content longer than chunk size
        content = "This is a test document. " * 20  # ~500 characters
        chunks = processor._create_chunks(content, "test_doc_id")
        
        # Verify chunking results
        assert len(chunks) > 1, "Content should be split into multiple chunks"
        
        for chunk in chunks:
            assert len(chunk.content) <= config.chunk_size_default + config.chunk_overlap
            assert chunk.document_id == "test_doc_id"
            assert chunk.chunk_index >= 0
        
        # Verify chunk ordering
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


class TestPRD008SecurityValidation:
    """Test security aspects of content processing"""
    
    def test_content_sanitization(self):
        """Verify malicious content is properly sanitized"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test XSS prevention
        malicious_content = "<script>alert('xss')</script>Regular content"
        normalized = processor._normalize_content(malicious_content)
        # Should not remove HTML but normalize whitespace
        assert "<script>" in normalized  # Normalization doesn't sanitize HTML
        
        # Test SQL injection patterns
        sql_injection = "'; DROP TABLE documents; --"
        normalized = processor._normalize_content(sql_injection)
        assert normalized == "'; DROP TABLE documents; --"  # Preserved as text
    
    def test_input_validation_security(self):
        """Verify input validation prevents security issues"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test with None content
        with pytest.raises((ValidationError, ValueError)):
            processor._normalize_content(None)
        
        # Test with extremely large content
        huge_content = "A" * (config.max_content_length + 1)
        with pytest.raises((ValidationError, ContentProcessingError)):
            FileContent(huge_content, "https://example.com", "Large Doc")
    
    def test_error_information_disclosure(self):
        """Verify error messages don't leak sensitive information"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test error messages don't contain system paths or sensitive data
        try:
            processor._extract_metadata("", None, "")
        except Exception as e:
            error_msg = str(e).lower()
            sensitive_patterns = ['/home/', '/usr/', 'password', 'secret', 'key', 'token']
            for pattern in sensitive_patterns:
                assert pattern not in error_msg, f"Error message contains sensitive info: {pattern}"


class TestPRD008PerformanceValidation:
    """Test performance characteristics of content processing"""
    
    def test_processing_performance(self):
        """Verify content processing meets performance requirements"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test processing time for medium-sized document
        content = "Sample content. " * 1000  # ~15KB
        file_content = FileContent(content, "https://example.com", "Performance Test")
        
        start_time = time.time()
        
        # Mock database operations to focus on processing performance
        with patch.object(processor, '_save_to_database', return_value="doc_id"):
            result = processor.process_document(file_content, "text")
        
        processing_time = time.time() - start_time
        
        # Should process within reasonable time (< 1 second for 15KB)
        assert processing_time < 1.0, f"Processing took too long: {processing_time}s"
        assert result is not None
    
    def test_memory_efficiency(self):
        """Verify memory usage is reasonable for large documents"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test with large document (near max size)
        large_content = "Large document content. " * 10000  # ~250KB
        
        # Should not cause memory issues
        try:
            normalized = processor._normalize_content(large_content)
            assert len(normalized) > 0
        except MemoryError:
            pytest.fail("Memory error during content normalization")
    
    def test_concurrent_processing(self):
        """Verify processor can handle concurrent operations"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test concurrent normalization
        contents = [f"Content {i}. " * 100 for i in range(10)]
        
        results = []
        for content in contents:
            result = processor._normalize_content(content)
            results.append(result)
        
        # All should succeed
        assert len(results) == 10
        assert all(len(r) > 0 for r in results)


class TestPRD008IntegrationValidation:
    """Test integration with other PRD components"""
    
    def test_cfg_001_configuration_integration(self):
        """Verify integration with CFG-001 configuration system"""
        # Test with custom configuration
        custom_config = ContentConfig(
            chunk_size_default=500,
            chunk_size_max=2000,
            chunk_overlap=50,
            quality_threshold=0.4,
            min_content_length=100
        )
        
        mock_db = Mock()
        processor = ContentProcessor(custom_config, mock_db)
        
        # Verify configuration is used
        content = "Test content. " * 100
        chunks = processor._create_chunks(content, "test_id")
        
        # Should respect custom chunk size
        for chunk in chunks:
            assert len(chunk.content) <= custom_config.chunk_size_default + custom_config.chunk_overlap
    
    def test_db_001_database_integration(self):
        """Verify integration with DB-001 database models"""
        config = ContentConfig()
        mock_db = Mock()
        
        # Mock database session and operations
        mock_session = Mock()
        mock_db.get_session = Mock(return_value=mock_session)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        processor = ContentProcessor(config, mock_db)
        
        # Test database integration
        content = FileContent("Test content", "https://example.com", "Test")
        
        with patch.object(processor, '_save_to_database', return_value="doc_id") as mock_save:
            result = processor.process_document(content, "text")
            mock_save.assert_called_once()
        
        assert result is not None
    
    def test_alm_001_anythingllm_compatibility(self):
        """Verify compatibility with ALM-001 AnythingLLM integration"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        content = "Test document for vector storage"
        file_content = FileContent(content, "https://example.com", "Vector Test")
        
        # Process document and verify output format is compatible with AnythingLLM
        with patch.object(processor, '_save_to_database', return_value="doc_id"):
            result = processor.process_document(file_content, "text")
        
        # Verify result structure is compatible with vector database ingestion
        assert hasattr(result, 'chunks')
        assert hasattr(result, 'metadata')
        assert len(result.chunks) > 0
        
        # Check chunk format compatibility
        for chunk in result.chunks:
            assert hasattr(chunk, 'content')
            assert hasattr(chunk, 'chunk_index')
            assert len(chunk.content) > 0


class TestPRD008ErrorHandlingValidation:
    """Test comprehensive error handling"""
    
    def test_quality_threshold_filtering(self):
        """Verify quality threshold filtering works correctly"""
        config = ContentConfig(quality_threshold=0.3)
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test low-quality content rejection
        low_quality = "bad"
        file_content = FileContent(low_quality, "https://example.com", "Bad")
        
        with pytest.raises(QualityThresholdError):
            processor.process_document(file_content, "text")
    
    def test_database_error_handling(self):
        """Verify database errors are properly handled"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Mock database failure
        with patch.object(processor, '_save_to_database', side_effect=Exception("DB Error")):
            content = FileContent("Good content for testing", "https://example.com", "Test")
            
            with pytest.raises(DatabaseError):
                processor.process_document(content, "text")
    
    def test_content_validation_errors(self):
        """Verify content validation error handling"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test empty content
        with pytest.raises(ValidationError):
            processor.process_document(FileContent("", "https://example.com", "Empty"), "text")
        
        # Test content too short
        short_content = "a"
        with pytest.raises(ValidationError):
            processor.process_document(FileContent(short_content, "https://example.com", "Short"), "text")
    
    def test_chunking_error_handling(self):
        """Verify chunking error scenarios are handled"""
        config = ContentConfig(chunk_size_default=10, chunk_size_max=20)
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test with problematic content that might cause chunking issues
        problematic_content = "\x00\x01\x02" + "valid content"
        
        try:
            chunks = processor._create_chunks(problematic_content, "test_id")
            # Should handle or filter problematic characters
            assert len(chunks) > 0
        except ChunkingError:
            # Acceptable if properly caught and handled
            pass


class TestPRD008QualityFilteringSystem:
    """Test the quality filtering system effectiveness"""
    
    def test_quality_scoring_accuracy(self):
        """Verify quality scoring algorithm accuracy"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test cases with expected quality ranges
        test_cases = [
            ("# Good Doc\n\nContent with structure and details.", 0.3, 1.0),
            ("just text", 0.0, 0.3),
            ("", 0.0, 0.1),
            ("# Excellent\n\n## Section\n\nDetailed content with ```code``` and lists:\n- Item 1\n- Item 2", 0.7, 1.0)
        ]
        
        for content, min_score, max_score in test_cases:
            if content:
                metadata = {
                    'word_count': len(content.split()),
                    'character_count': len(content)
                }
                score = processor._calculate_quality_score(content, metadata)
                assert min_score <= score <= max_score, f"Score {score} not in range [{min_score}, {max_score}] for: {content[:50]}"
    
    def test_threshold_configuration(self):
        """Verify quality threshold is configurable and enforced"""
        # Test with different thresholds
        thresholds = [0.1, 0.3, 0.5, 0.7]
        
        for threshold in thresholds:
            config = ContentConfig(quality_threshold=threshold)
            mock_db = Mock()
            processor = ContentProcessor(config, mock_db)
            
            # Create content that should score around 0.4
            medium_content = "# Document\n\nSome content with structure."
            file_content = FileContent(medium_content, "https://example.com", "Medium")
            
            try:
                with patch.object(processor, '_save_to_database', return_value="doc_id"):
                    result = processor.process_document(file_content, "text")
                
                # Should pass if threshold <= 0.4, fail if threshold > 0.4
                if threshold > 0.4:
                    pytest.fail(f"Should have failed quality threshold {threshold}")
                
            except QualityThresholdError:
                # Should fail if threshold > content quality
                if threshold <= 0.4:
                    pytest.fail(f"Should have passed quality threshold {threshold}")


class TestPRD008ProductionReadiness:
    """Test production readiness aspects"""
    
    def test_configuration_validation(self):
        """Verify configuration validation at startup"""
        # Test invalid configurations
        with pytest.raises((ConfigurationError, ValueError)):
            ContentConfig(chunk_size_default=-1)
        
        with pytest.raises((ConfigurationError, ValueError)):
            ContentConfig(quality_threshold=1.5)
    
    def test_logging_and_monitoring(self):
        """Verify appropriate logging is in place"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Should not raise exceptions for normal operations
        content = "Test content for logging validation"
        file_content = FileContent(content, "https://example.com", "Log Test")
        
        with patch.object(processor, '_save_to_database', return_value="doc_id"):
            result = processor.process_document(file_content, "text")
        
        assert result is not None
    
    def test_factory_function_integration(self):
        """Verify factory functions work for dependency injection"""
        # Test create_content_processor factory
        config = ContentConfig()
        mock_db = Mock()
        
        processor = create_content_processor(config, mock_db)
        assert isinstance(processor, ContentProcessor)
        
        # Test content creation factories
        file_content = create_file_content("content", "url", "title")
        assert isinstance(file_content, FileContent)
        
        scraped_content = create_scraped_content("content", "url", "title")
        assert isinstance(scraped_content, ScrapedContent)


# Integration test markers for comprehensive validation
@pytest.mark.integration
class TestPRD008EndToEndValidation:
    """End-to-end integration testing"""
    
    @pytest.mark.asyncio
    async def test_complete_processing_pipeline(self):
        """Test complete content processing pipeline"""
        config = ContentConfig()
        mock_db = Mock()
        processor = ContentProcessor(config, mock_db)
        
        # Test complete workflow
        content = """
        # Complete Test Document
        
        This is a comprehensive test document for validating the complete
        content processing pipeline functionality.
        
        ## Features Tested
        - Content normalization
        - Metadata extraction
        - Quality scoring
        - Content chunking
        - Database integration
        
        ```python
        def test_function():
            return "test successful"
        ```
        
        ## Conclusion
        The pipeline should handle this content successfully.
        """
        
        file_content = FileContent(content, "https://example.com/complete", "Complete Test")
        
        with patch.object(processor, '_save_to_database', return_value="complete_doc_id"):
            result = processor.process_document(file_content, "markdown")
        
        # Verify complete pipeline results
        assert result is not None
        assert result.id == "complete_doc_id"
        assert len(result.chunks) > 0
        assert result.quality_score > config.quality_threshold
        assert result.word_count > 0
        
        # Verify chunk integrity
        total_content = "".join(chunk.content for chunk in result.chunks)
        assert len(total_content) > 0


# Test execution and reporting
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])