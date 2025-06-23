"""
Document Ingestion Models - Input validation and request/response schemas
Pydantic models for secure document upload and processing operations
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import mimetypes

logger = logging.getLogger(__name__)


class SupportedFormat(str, Enum):
    """Supported document formats for ingestion"""
    PDF = "pdf"
    DOC = "doc" 
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"


class IngestionStatus(str, Enum):
    """Document ingestion processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class DocumentUploadRequest(BaseModel):
    """Request model for single document upload"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the document")
    technology: str = Field(..., description="Technology/framework this document covers")
    title: Optional[str] = Field(None, description="Optional document title")
    source_url: Optional[str] = Field(None, description="Optional source URL reference")
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v):
        """Validate content type is supported"""
        allowed_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/markdown',
            'text/html',
            'application/octet-stream'  # For generic binary files
        }
        if v not in allowed_types:
            raise ValueError(f'Unsupported content type: {v}')
        return v
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Validate filename and extract format"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Filename cannot be empty')
        
        # Security: prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Invalid filename: path components not allowed')
        
        # Check file extension
        extension = v.lower().split('.')[-1] if '.' in v else ''
        supported_extensions = {'pdf', 'doc', 'docx', 'txt', 'md', 'html'}
        if extension not in supported_extensions:
            raise ValueError(f'Unsupported file extension: {extension}')
        
        return v.strip()


class BatchUploadRequest(BaseModel):
    """Request model for batch document upload"""
    documents: List[DocumentUploadRequest] = Field(..., description="List of documents to upload")
    technology: str = Field(..., description="Default technology for all documents")
    batch_name: Optional[str] = Field(None, description="Optional batch identifier")
    
    @field_validator('documents')
    @classmethod
    def validate_batch_size(cls, v):
        """Validate batch size limits"""
        if len(v) == 0:
            raise ValueError('Batch cannot be empty')
        if len(v) > 100:  # Configurable limit
            raise ValueError('Batch size cannot exceed 100 documents')
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion operation"""
    document_id: str = Field(..., description="Generated document identifier")
    filename: str = Field(..., description="Original filename")
    status: IngestionStatus = Field(..., description="Processing status")
    content_hash: Optional[str] = Field(None, description="Content hash for deduplication")
    word_count: Optional[int] = Field(None, description="Extracted word count")
    chunk_count: Optional[int] = Field(None, description="Number of chunks created")
    quality_score: Optional[float] = Field(None, description="Content quality score")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class BatchIngestionResult(BaseModel):
    """Result of batch document ingestion"""
    batch_id: str = Field(..., description="Unique batch identifier")
    batch_name: Optional[str] = Field(None, description="Optional batch name")
    total_documents: int = Field(..., description="Total documents in batch")
    successful_count: int = Field(0, description="Successfully processed documents")
    failed_count: int = Field(0, description="Failed document processing")
    results: List[IngestionResult] = Field(..., description="Individual document results")
    total_processing_time_ms: int = Field(0, description="Total batch processing time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Batch creation timestamp")


class IngestionHealthCheck(BaseModel):
    """Health check response for ingestion service"""
    status: str = Field(..., description="Service health status")
    supported_formats: List[str] = Field(..., description="List of supported document formats")
    max_file_size_mb: int = Field(..., description="Maximum file size in MB")
    max_batch_size: int = Field(..., description="Maximum batch size")
    content_processor_status: str = Field(..., description="Content processor health")
    database_status: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")


class ProcessingMetrics(BaseModel):
    """Processing metrics and statistics"""
    total_documents_processed: int = Field(0, description="Total documents processed")
    documents_by_format: Dict[str, int] = Field(default_factory=dict, description="Count by document format")
    documents_by_technology: Dict[str, int] = Field(default_factory=dict, description="Count by technology")
    average_processing_time_ms: float = Field(0.0, description="Average processing time")
    success_rate: float = Field(0.0, description="Processing success rate")
    quality_score_distribution: Dict[str, int] = Field(default_factory=dict, description="Quality score ranges")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Metrics last updated")


class ValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value provided")


class IngestionError(BaseModel):
    """Structured error response for ingestion operations"""
    error_code: str = Field(..., description="Error code identifier")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Field validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")