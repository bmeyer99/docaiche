"""
Main processing pipeline for document processing.
Implements PRD-006: Orchestrates ingestion, extraction, preprocessing, chunking, metadata, queue, and error handling.
"""

import logging
from fastapi import HTTPException
from src.document_processing.ingestion import DocumentIngestionService
from src.document_processing.extraction import TextExtractor
from src.document_processing.preprocessing import ContentPreprocessor
from src.document_processing.chunking import DocumentChunker
from src.document_processing.metadata import MetadataExtractor
from src.document_processing.queue import ProcessingQueueManager
from src.document_processing.models import ProcessingJob, ProcessingStatus
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentProcessingPipeline:
    """
    Orchestrates the document processing pipeline.
    Integrates PRD-002 (DatabaseManager, CacheManager), PRD-003 (ConfigurationManager), PRD-004 (logging).
    """

    def __init__(self, config_manager, db_manager, cache_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.ingestion = DocumentIngestionService(config_manager, db_manager)
        self.extractor = TextExtractor()
        self.preprocessor = ContentPreprocessor()
        self.chunker = DocumentChunker(
            chunk_size=config_manager.get("chunk_size", 1000),
            overlap=config_manager.get("chunk_overlap", 100),
        )
        self.metadata_extractor = MetadataExtractor()
        self.queue = ProcessingQueueManager(cache_manager)

    async def process_document(self, file_data: bytes, filename: str) -> ProcessingJob:
        """
        Main processing workflow: validate, store, extract, preprocess, chunk, enqueue.
        """
        try:
            # Validate document
            await self.ingestion.validate_document(file_data, filename)
            # Save file temporarily for extraction/metadata
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name
            # Extract metadata
            metadata = await self.metadata_extractor.extract_metadata(
                tmp_path, filename
            )
            # Store document and get document_id
            document_id = await self.ingestion.store_document(file_data, metadata)
            # Create processing job
            job = await self.ingestion.create_processing_job(document_id)
            # Extract text
            text = await self.extractor.extract_text(tmp_path, metadata.format)
            # Preprocess text
            clean_text = await self.preprocessor.clean_text(text)
            # Chunk document
            chunks = await self.chunker.chunk_document(clean_text, document_id)
            # Store chunks in DB
            for chunk in chunks:
                await self.db_manager.store_chunk(chunk.dict())
            # Enqueue job for further processing
            await self.queue.enqueue_job(job)
            logger.info(f"Document {filename} processed and job {job.job_id} enqueued")
            return job
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document processing failed for {filename}: {e}")
            raise HTTPException(status_code=500, detail="Document processing failed")

    async def get_processing_status(self, job_id: str) -> ProcessingJob:
        """
        Returns the current status of a processing job.
        """
        try:
            job_data = await self.db_manager.get_processing_job(job_id)
            if not job_data:
                raise HTTPException(status_code=404, detail="Job not found")
            return ProcessingJob(**job_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get status for job {job_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get job status")

    async def retry_failed_job(self, job_id: str) -> bool:
        """
        Retries a failed processing job.
        """
        try:
            job_data = await self.db_manager.get_processing_job(job_id)
            if not job_data:
                raise HTTPException(status_code=404, detail="Job not found")
            job = ProcessingJob(**job_data)
            if job.status != ProcessingStatus.FAILED:
                raise HTTPException(
                    status_code=400, detail="Job is not in failed state"
                )
            # Reset status and progress
            job.status = ProcessingStatus.PENDING
            job.progress = 0.0
            job.updated_at = datetime.utcnow().isoformat()
            await self.db_manager.update_processing_job(job_id, job.dict())
            await self.queue.enqueue_job(job)
            logger.info(f"Retried failed job {job_id}")
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retry job")
