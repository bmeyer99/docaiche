"""
Pydantic Data Models for Document Processing Pipeline.
Implements PRD-006: Defines request, response, and internal models for pipeline operations.
"""

import logging
from typing import Optional
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "md"
    HTML = "html"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    filename: str
    file_size: int
    format: DocumentFormat
    mime_type: str
    upload_timestamp: str
    checksum: str


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_offset: int
    end_offset: int


class ProcessingJob(BaseModel):
    job_id: str
    document_id: str
    status: ProcessingStatus
    progress: float
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
