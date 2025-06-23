"""
Document Ingestion Service.
Implements PRD-006: Handles file uploads, validation, and initial processing entrypoint.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from src.document_processing.models import DocumentMetadata, ProcessingJob, DocumentFormat, ProcessingStatus
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class DocumentIngestionService:
    """
    Handles document ingestion, validation, storage, and processing job creation.
    Integrates with PRD-002 (DatabaseManager, CacheManager) and PRD-003 (ConfigurationManager).
    """

    def __init__(self, config_manager, db_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.max_file_size = self.config_manager.get("document_max_file_size", 20 * 1024 * 1024)  # 20MB default
        self.allowed_formats = set(self.config_manager.get("document_allowed_formats", [
            DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.TXT, DocumentFormat.MARKDOWN, DocumentFormat.HTML
        ]))

    async def validate_document(self, file_data: bytes, filename: str) -> bool:
        """
        Validates file size and format.
        """
        try:
            if len(file_data) > self.max_file_size:
                logger.warning(f"File {filename} exceeds max size limit.")
                raise HTTPException(status_code=413, detail="File too large")
            ext = filename.split(".")[-1].lower()
            if ext not in [fmt.value for fmt in self.allowed_formats]:
                logger.warning(f"File {filename} has unsupported format: {ext}")
                raise HTTPException(status_code=415, detail="Unsupported file format")
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation error for {filename}: {e}")
            raise HTTPException(status_code=400, detail="Invalid document")

    async def store_document(self, file_data: bytes, metadata: DocumentMetadata) -> str:
        """
        Stores document in database and returns document_id.
        """
        try:
            document_id = await self.db_manager.store_document(file_data, metadata.dict())
            logger.info(f"Stored document {metadata.filename} with id {document_id}")
            return document_id
        except Exception as e:
            logger.error(f"Failed to store document {metadata.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to store document")

    async def create_processing_job(self, document_id: str) -> ProcessingJob:
        """
        Creates an async processing job for the document.
        """
        try:
            now = datetime.utcnow().isoformat()
            job_id = hashlib.sha256(f"{document_id}-{now}".encode()).hexdigest()
            job = ProcessingJob(
                job_id=job_id,
                document_id=document_id,
                status=ProcessingStatus.PENDING,
                progress=0.0,
                created_at=now,
                updated_at=now
            )
            await self.db_manager.create_processing_job(job.dict())
            logger.info(f"Created processing job {job_id} for document {document_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to create processing job for {document_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create processing job")