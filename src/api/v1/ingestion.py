"""
Document Ingestion API Endpoints - FastAPI router for file upload and processing
Secure document upload endpoints with comprehensive validation and monitoring
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline
from src.ingestion.models import (
    DocumentUploadRequest, BatchUploadRequest, IngestionResult, 
    BatchIngestionResult, IngestionHealthCheck, ProcessingMetrics,
    IngestionError, IngestionStatus
)

logger = logging.getLogger(__name__)

# Create router for ingestion endpoints
ingestion_router = APIRouter(prefix="/ingestion", tags=["ingestion"])


async def get_ingestion_pipeline() -> IngestionPipeline:
    """
    Dependency to provide ingestion pipeline instance.
    
    Returns:
        Configured IngestionPipeline instance
    """
    try:
        return await create_ingestion_pipeline()
    except Exception as e:
        logger.error(f"Failed to create ingestion pipeline: {e}")
        raise HTTPException(status_code=500, detail="Ingestion service unavailable")


@ingestion_router.get("/health", response_model=IngestionHealthCheck)
async def health_check(
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> IngestionHealthCheck:
    """
    Health check endpoint for document ingestion service.
    
    Returns service status, capabilities, and integration health.
    """
    try:
        # Check content processor health
        content_processor_status = "healthy"
        try:
            # Test database connection
            await pipeline.db_manager.fetch_one("SELECT 1")
            database_status = "healthy"
        except Exception:
            database_status = "unhealthy"
            content_processor_status = "degraded"
        
        return IngestionHealthCheck(
            status="healthy" if database_status == "healthy" else "degraded",
            supported_formats=list(pipeline.supported_formats),
            max_file_size_mb=pipeline.max_file_size // (1024 * 1024),
            max_batch_size=pipeline.max_batch_size,
            content_processor_status=content_processor_status,
            database_status=database_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@ingestion_router.post("/upload", response_model=IngestionResult)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    technology: str = Form(..., description="Technology/framework this document covers"),
    title: str = Form(None, description="Optional document title"),
    source_url: str = Form(None, description="Optional source URL reference"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> IngestionResult:
    """
    Upload and process a single document.
    
    Supports PDF, DOC, DOCX, TXT, MD, and HTML formats with secure processing
    through the integrated Content Processing Pipeline (PRD-008).
    """
    try:
        # Validate file upload
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not file.content_type:
            raise HTTPException(status_code=400, detail="No content type provided")
        
        # Read file data
        try:
            file_data = await file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file {file.filename}: {e}")
            raise HTTPException(status_code=400, detail="Failed to read uploaded file")
        
        # Create upload request
        upload_request = DocumentUploadRequest(
            filename=file.filename,
            content_type=file.content_type,
            technology=technology,
            title=title,
            source_url=source_url
        )
        
        # Process document
        result = await pipeline.ingest_single_document(file_data, upload_request)
        
        # Set appropriate HTTP status based on result
        if result.status == IngestionStatus.COMPLETED:
            logger.info(f"Document upload successful: {result.document_id}")
            return result
        elif result.status == IngestionStatus.REJECTED:
            raise HTTPException(status_code=422, detail=result.error_message)
        else:
            raise HTTPException(status_code=500, detail=result.error_message)
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Document upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document upload system error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@ingestion_router.post("/upload/batch", response_model=BatchIngestionResult)
async def upload_batch_documents(
    files: List[UploadFile] = File(..., description="List of document files to upload"),
    technology: str = Form(..., description="Default technology for all documents"),
    batch_name: str = Form(None, description="Optional batch identifier"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> BatchIngestionResult:
    """
    Upload and process multiple documents as a batch.
    
    Processes documents in parallel with controlled concurrency for optimal
    performance and resource utilization.
    """
    try:
        # Validate batch request
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        if len(files) > pipeline.max_batch_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Batch size {len(files)} exceeds maximum {pipeline.max_batch_size}"
            )
        
        # Process files and create requests
        files_data = []
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail=f"No filename provided for file")
            
            # Read file data
            try:
                file_data = await file.read()
            except Exception as e:
                logger.error(f"Failed to read file {file.filename}: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to read file {file.filename}")
            
            # Create upload request
            upload_request = DocumentUploadRequest(
                filename=file.filename,
                content_type=file.content_type or "application/octet-stream",
                technology=technology
            )
            
            files_data.append((file_data, upload_request))
        
        # Create batch request
        batch_request = BatchUploadRequest(
            documents=[req for _, req in files_data],
            technology=technology,
            batch_name=batch_name
        )
        
        # Process batch
        result = await pipeline.ingest_batch_documents(files_data, batch_request)
        
        logger.info(f"Batch upload completed: {result.batch_id} - {result.successful_count}/{result.total_documents} successful")
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Batch upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Batch upload system error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@ingestion_router.get("/metrics", response_model=ProcessingMetrics)
async def get_processing_metrics(
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> ProcessingMetrics:
    """
    Get document processing metrics and statistics.
    
    Returns processing statistics including format distribution,
    technology breakdown, and success rates.
    """
    try:
        metrics = await pipeline.get_processing_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get processing metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve processing metrics")


@ingestion_router.get("/status/{document_id}")
async def get_document_status(
    document_id: str,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> Dict[str, Any]:
    """
    Get processing status for a specific document.
    
    Args:
        document_id: Document identifier from upload response
        
    Returns:
        Document status and processing information
    """
    try:
        # Query document status from database
        query = """
            SELECT content_id, title, processing_status, quality_score, 
                   word_count, chunk_count, created_at, updated_at
            FROM content_metadata 
            WHERE content_id = ?
        """
        result = await pipeline.db_manager.fetch_one(query, (document_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "document_id": result[0],
            "title": result[1],
            "processing_status": result[2],
            "quality_score": result[3],
            "word_count": result[4],
            "chunk_count": result[5],
            "created_at": result[6],
            "updated_at": result[7]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document status")


@ingestion_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)
) -> Dict[str, str]:
    """
    Delete a document and its associated data.
    
    Args:
        document_id: Document identifier to delete
        
    Returns:
        Deletion confirmation
    """
    try:
        # Check if document exists
        check_query = "SELECT content_id FROM content_metadata WHERE content_id = ?"
        result = await pipeline.db_manager.fetch_one(check_query, (document_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document metadata (cascading deletes will handle related records)
        delete_query = "DELETE FROM content_metadata WHERE content_id = ?"
        await pipeline.db_manager.execute(delete_query, (document_id,))
        
        logger.info(f"Document deleted: {document_id}")
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


# Note: Exception handlers would be added to the main FastAPI app, not the router
# === PRD-006: Document Processing Pipeline Endpoints ===

from src.document_processing.pipeline import DocumentProcessingPipeline
from src.core.config.manager import ConfigurationManager
from src.database.manager import DatabaseManager
from src.cache.manager import CacheManager
from src.document_processing.models import ProcessingJob
from fastapi import status

async def get_document_processing_pipeline() -> DocumentProcessingPipeline:
    """
    Dependency to provide DocumentProcessingPipeline instance.
    """
    try:
        config_manager = ConfigurationManager()
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        return DocumentProcessingPipeline(config_manager, db_manager, cache_manager)
    except Exception as e:
        logger.error(f"Failed to create DocumentProcessingPipeline: {e}")
        raise HTTPException(status_code=500, detail="Document processing service unavailable")

@ingestion_router.post(
    "/v2/upload",
    response_model=ProcessingJob,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["ingestion"]
)
async def upload_document_v2(
    file: UploadFile = File(..., description="Document file to upload"),
    pipeline: DocumentProcessingPipeline = Depends(get_document_processing_pipeline)
) -> ProcessingJob:
    """
    Upload and process a document using PRD-006 pipeline.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        file_data = await file.read()
        job = await pipeline.process_document(file_data, file.filename)
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PRD-006 upload failed: {e}")
        raise HTTPException(status_code=500, detail="Document processing failed")

@ingestion_router.get(
    "/v2/status/{job_id}",
    response_model=ProcessingJob,
    tags=["ingestion"]
)
async def get_processing_status_v2(
    job_id: str,
    pipeline: DocumentProcessingPipeline = Depends(get_document_processing_pipeline)
) -> ProcessingJob:
    """
    Get processing status for a document job (PRD-006).
    """
    try:
        return await pipeline.get_processing_status(job_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PRD-006 status check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")

@ingestion_router.post(
    "/v2/retry/{job_id}",
    response_model=dict,
    tags=["ingestion"]
)
async def retry_failed_job_v2(
    job_id: str,
    pipeline: DocumentProcessingPipeline = Depends(get_document_processing_pipeline)
) -> dict:
    """
    Retry a failed processing job (PRD-006).
    """
    try:
        result = await pipeline.retry_failed_job(job_id)
        return {"success": result, "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PRD-006 retry failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry job")

@ingestion_router.get(
    "/v2/health",
    response_model=dict,
    tags=["ingestion"]
)
async def document_processing_health_check_v2(
    pipeline: DocumentProcessingPipeline = Depends(get_document_processing_pipeline)
) -> dict:
    """
    Health check for PRD-006 document processing pipeline.
    """
    try:
        # Simple health check: try to instantiate pipeline and ping DB/cache
        await pipeline.db_manager.health_check()
        await pipeline.cache_manager.health_check()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"PRD-006 health check failed: {e}")
        raise HTTPException(status_code=500, detail="Document processing pipeline unhealthy")
# These are handled through try/catch blocks in the endpoints above