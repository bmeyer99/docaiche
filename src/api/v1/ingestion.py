"""
Ingestion API Router - PRD-006/PRD-008
Defines the ingestion_router for document upload and processing endpoints.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

ingestion_router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@ingestion_router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for ingestion and processing.
    Returns a document_id on success.
    """
    try:
        # Simulate document processing and return a stub document_id
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")
        # In production, save file and trigger processing pipeline
        return {"document_id": "stub-doc-id"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")