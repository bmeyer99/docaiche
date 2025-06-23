"""
Document Ingestion Pipeline - Core ingestion orchestrator
Coordinates file upload, content extraction, processing, and storage
"""

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO

from src.core.config.models import ContentConfig
from src.database.connection import DatabaseManager
from src.processors.content_processor import ContentProcessor, FileContent
from src.processors.factory import create_content_processor
from .extractors import DocumentExtractor, create_document_extractor
from .models import (
    DocumentUploadRequest, BatchUploadRequest, IngestionResult, 
    BatchIngestionResult, IngestionStatus, ProcessingMetrics
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Main document ingestion pipeline coordinating all processing steps.
    
    Integrates with existing Content Processing Pipeline (PRD-008) while providing
    secure file upload handling and multi-format document support.
    """
    
    def __init__(
        self,
        content_processor: ContentProcessor,
        document_extractor: DocumentExtractor,
        db_manager: DatabaseManager
    ):
        """
        Initialize ingestion pipeline with dependencies.
        
        Args:
            content_processor: Content processor from PRD-008
            document_extractor: Document content extractor
            db_manager: Database manager for persistence
        """
        self.content_processor = content_processor
        self.document_extractor = document_extractor
        self.db_manager = db_manager
        
        # Configuration limits
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_batch_size = 100
        self.supported_formats = {'pdf', 'doc', 'docx', 'txt', 'md', 'html'}
        
        logger.info("Document ingestion pipeline initialized")
    
    async def ingest_single_document(
        self,
        file_data: bytes,
        upload_request: DocumentUploadRequest
    ) -> IngestionResult:
        """
        Process a single uploaded document through the complete pipeline.
        
        Processing steps:
        1. Security validation and file size checks
        2. Content extraction based on file format
        3. Integration with Content Processing Pipeline (PRD-008)
        4. Database persistence and result tracking
        
        Args:
            file_data: Raw uploaded file bytes
            upload_request: Validated upload request
            
        Returns:
            IngestionResult with processing status and metadata
        """
        start_time = datetime.utcnow()
        document_id = self._generate_document_id()
        
        try:
            logger.info(f"Starting document ingestion: {upload_request.filename} ({document_id})")
            
            # Step 1: Security validation
            await self._validate_file_security(file_data, upload_request)
            
            # Step 2: Extract content based on format
            extracted_text, extraction_metadata = await self.document_extractor.extract_content(
                file_data, upload_request.filename
            )
            
            if not extracted_text or len(extracted_text.strip()) < 5:
                return IngestionResult(
                    document_id=document_id,
                    filename=upload_request.filename,
                    status=IngestionStatus.REJECTED,
                    error_message="Insufficient text content extracted from document"
                )
            
            # Step 3: Create FileContent for PRD-008 integration
            file_content = FileContent(
                content=extracted_text,
                source_url=upload_request.source_url or f"upload://{upload_request.filename}",
                title=upload_request.title or upload_request.filename
            )
            
            # Step 4: Process through Content Processing Pipeline
            processed_doc, status_message = await self.content_processor.process_and_store_document(
                file_content, upload_request.technology
            )
            
            if not processed_doc or status_message != "success":
                return IngestionResult(
                    document_id=document_id,
                    filename=upload_request.filename,
                    status=IngestionStatus.FAILED,
                    error_message=f"Content processing failed: {status_message}"
                )
            
            # Step 5: Calculate processing metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Step 6: Create successful result
            result = IngestionResult(
                document_id=getattr(processed_doc, 'id', 'mock_id'),
                filename=upload_request.filename,
                status=IngestionStatus.COMPLETED,
                content_hash=getattr(processed_doc, 'content_hash', 'mock_hash'),
                word_count=getattr(processed_doc, 'word_count', 0),
                chunk_count=len(getattr(processed_doc, 'chunks', [])),
                quality_score=getattr(processed_doc, 'quality_score', 0.8),
                processing_time_ms=int(processing_time),
                created_at=start_time
            )
            
            logger.info(f"Document ingestion completed: {document_id} in {processing_time:.0f}ms")
            return result
            
        except ValueError as e:
            # User input validation errors
            logger.warning(f"Document ingestion validation error ({document_id}): {e}")
            return IngestionResult(
                document_id=document_id,
                filename=upload_request.filename,
                status=IngestionStatus.REJECTED,
                error_message=str(e)
            )
            
        except Exception as e:
            # System errors
            logger.error(f"Document ingestion system error ({document_id}): {e}")
            return IngestionResult(
                document_id=document_id,
                filename=upload_request.filename,
                status=IngestionStatus.FAILED,
                error_message="Internal processing error"
            )
    
    async def ingest_batch_documents(
        self,
        files_data: List[Tuple[bytes, DocumentUploadRequest]],
        batch_request: BatchUploadRequest
    ) -> BatchIngestionResult:
        """
        Process multiple documents as a batch with parallel processing.
        
        Args:
            files_data: List of (file_bytes, upload_request) tuples
            batch_request: Batch processing configuration
            
        Returns:
            BatchIngestionResult with individual results and summary
        """
        start_time = datetime.utcnow()
        batch_id = self._generate_batch_id()
        
        logger.info(f"Starting batch ingestion: {len(files_data)} documents ({batch_id})")
        
        # Validate batch size
        if len(files_data) > self.max_batch_size:
            raise ValueError(f"Batch size {len(files_data)} exceeds maximum {self.max_batch_size}")
        
        # Process documents with controlled concurrency
        max_concurrent = min(5, len(files_data))  # Limit concurrent processing
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(file_data_tuple):
            file_data, upload_request = file_data_tuple
            async with semaphore:
                return await self.ingest_single_document(file_data, upload_request)
        
        # Execute batch processing
        results = await asyncio.gather(
            *[process_single(file_data_tuple) for file_data_tuple in files_data],
            return_exceptions=True
        )
        
        # Process results and handle exceptions
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle processing exceptions
                file_data, upload_request = files_data[i]
                failed_result = IngestionResult(
                    document_id=self._generate_document_id(),
                    filename=upload_request.filename,
                    status=IngestionStatus.FAILED,
                    error_message=f"Processing exception: {str(result)}"
                )
                failed_results.append(failed_result)
            elif result.status == IngestionStatus.COMPLETED:
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        # Calculate batch metrics
        total_processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        all_results = successful_results + failed_results
        
        batch_result = BatchIngestionResult(
            batch_id=batch_id,
            batch_name=batch_request.batch_name,
            total_documents=len(files_data),
            successful_count=len(successful_results),
            failed_count=len(failed_results),
            results=all_results,
            total_processing_time_ms=int(total_processing_time),
            created_at=start_time
        )
        
        logger.info(f"Batch ingestion completed: {batch_id} - {len(successful_results)}/{len(files_data)} successful")
        return batch_result
    
    async def get_processing_metrics(self) -> ProcessingMetrics:
        """
        Get processing metrics and statistics from the database.
        
        Returns:
            ProcessingMetrics with current system statistics
        """
        try:
            # Query database for metrics
            total_docs_query = "SELECT COUNT(*) FROM content_metadata WHERE processing_status = 'completed'"
            total_docs = await self.db_manager.fetch_one(total_docs_query)
            total_count = total_docs[0] if total_docs else 0
            
            # Get format distribution (approximated from filenames in source_url)
            format_query = """
                SELECT 
                    CASE 
                        WHEN source_url LIKE '%.pdf' THEN 'pdf'
                        WHEN source_url LIKE '%.doc%' THEN 'docx'
                        WHEN source_url LIKE '%.txt' THEN 'txt'
                        WHEN source_url LIKE '%.md' THEN 'md'
                        WHEN source_url LIKE '%.html' THEN 'html'
                        ELSE 'other'
                    END as format,
                    COUNT(*) as count
                FROM content_metadata 
                WHERE processing_status = 'completed'
                GROUP BY format
            """
            format_results = await self.db_manager.fetch_all(format_query)
            format_distribution = {row[0]: row[1] for row in format_results} if format_results else {}
            
            # Get technology distribution
            tech_query = """
                SELECT technology, COUNT(*) as count
                FROM content_metadata 
                WHERE processing_status = 'completed'
                GROUP BY technology
                ORDER BY count DESC
                LIMIT 10
            """
            tech_results = await self.db_manager.fetch_all(tech_query)
            tech_distribution = {row[0]: row[1] for row in tech_results} if tech_results else {}
            
            # Calculate success rate
            failed_query = "SELECT COUNT(*) FROM content_metadata WHERE processing_status = 'failed'"
            failed_docs = await self.db_manager.fetch_one(failed_query)
            failed_count = failed_docs[0] if failed_docs else 0
            
            success_rate = (total_count / (total_count + failed_count)) * 100 if (total_count + failed_count) > 0 else 100.0
            
            # Quality score distribution
            quality_query = """
                SELECT 
                    CASE 
                        WHEN quality_score < 0.3 THEN 'low'
                        WHEN quality_score < 0.7 THEN 'medium'
                        ELSE 'high'
                    END as quality_range,
                    COUNT(*) as count
                FROM content_metadata 
                WHERE processing_status = 'completed' AND quality_score IS NOT NULL
                GROUP BY quality_range
            """
            quality_results = await self.db_manager.fetch_all(quality_query)
            quality_distribution = {row[0]: row[1] for row in quality_results} if quality_results else {}
            
            return ProcessingMetrics(
                total_documents_processed=total_count,
                documents_by_format=format_distribution,
                documents_by_technology=tech_distribution,
                average_processing_time_ms=0.0,  # Would need additional tracking
                success_rate=success_rate,
                quality_score_distribution=quality_distribution
            )
            
        except Exception as e:
            logger.error(f"Failed to get processing metrics: {e}")
            return ProcessingMetrics()
    
    async def _validate_file_security(self, file_data: bytes, upload_request: DocumentUploadRequest) -> None:
        """
        Perform security validation on uploaded file.
        
        Args:
            file_data: Raw file bytes
            upload_request: Upload request metadata
            
        Raises:
            ValueError: If file fails security validation
        """
        # File size validation
        if len(file_data) > self.max_file_size:
            raise ValueError(f"File size {len(file_data)} bytes exceeds limit {self.max_file_size}")
        
        if len(file_data) == 0:
            raise ValueError("Empty file not allowed")
        
        # File format validation
        filename_ext = upload_request.filename.lower().split('.')[-1] if '.' in upload_request.filename else ''
        if filename_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {filename_ext}")
        
        # Basic content type validation
        if upload_request.content_type not in {
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain', 'text/markdown', 'text/html', 'application/octet-stream'
        }:
            raise ValueError(f"Unsupported content type: {upload_request.content_type}")
        
        # Security: Check for malicious content patterns
        if b'<script' in file_data.lower()[:1024]:  # Basic script detection in first 1KB
            logger.warning(f"Potential script content detected in {upload_request.filename}")
        
        logger.debug(f"File security validation passed: {upload_request.filename}")
    
    def _generate_document_id(self) -> str:
        """Generate unique document identifier"""
        return f"doc_{uuid.uuid4().hex[:12]}"
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch identifier"""
        return f"batch_{uuid.uuid4().hex[:12]}"


async def create_ingestion_pipeline(
    content_config: Optional[ContentConfig] = None,
    db_manager: Optional[DatabaseManager] = None
) -> IngestionPipeline:
    """
    Factory function to create configured ingestion pipeline.
    
    Args:
        content_config: Optional content configuration override
        db_manager: Optional database manager override
        
    Returns:
        Configured IngestionPipeline instance
        
    Raises:
        Exception: If pipeline creation fails
    """
    try:
        # Create content processor using existing factory
        content_processor = await create_content_processor(content_config, db_manager)
        
        # Create document extractor
        document_extractor = await create_document_extractor()
        
        # Use provided database manager or get from content processor
        if db_manager is None:
            db_manager = content_processor.db_manager
        
        # Create and return pipeline
        pipeline = IngestionPipeline(content_processor, document_extractor, db_manager)
        logger.info("Document ingestion pipeline created successfully")
        return pipeline
        
    except Exception as e:
        logger.error(f"Failed to create ingestion pipeline: {e}")
        raise