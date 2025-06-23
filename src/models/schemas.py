"""
Pydantic Schemas for AI Documentation Cache System - PRD-001
Request/Response models for API validation and data processing

These schemas define the data structures used throughout the system for
API requests, responses, and internal data processing operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """
    Represents a single chunk of processed document content.
    
    Used by content processing pipeline and AnythingLLM client
    for document upload operations.
    """
    id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Text content of the chunk")
    chunk_index: int = Field(..., description="Index of this chunk in the document")
    total_chunks: int = Field(..., description="Total number of chunks in document")
    word_count: int = Field(0, description="Number of words in this chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional chunk metadata")


class ProcessedDocument(BaseModel):
    """
    Represents a fully processed document ready for upload to vector database.
    
    Contains all chunks and metadata needed for AnythingLLM integration.
    """
    id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    source_url: str = Field(..., description="Original source URL")
    technology: str = Field(..., description="Technology/framework this document covers")
    content_hash: str = Field(..., description="Hash of original content for deduplication")
    chunks: List[DocumentChunk] = Field(..., description="List of document chunks")
    word_count: int = Field(0, description="Total word count")
    quality_score: float = Field(0.0, description="Content quality score (0.0-1.0)")
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class DocumentMetadata(BaseModel):
    """
    Metadata for tracking documents in the system.
    
    Maps to content_metadata database table.
    """
    content_id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Document title")
    source_url: str = Field(..., description="Source URL")
    technology: str = Field(..., description="Technology/framework")
    content_hash: str = Field(..., description="Content hash for deduplication")
    word_count: int = Field(0, description="Total word count")
    heading_count: int = Field(0, description="Number of headings")
    code_block_count: int = Field(0, description="Number of code blocks")
    chunk_count: int = Field(0, description="Number of chunks")
    quality_score: float = Field(0.0, description="Quality score (0.0-1.0)")
    freshness_score: float = Field(1.0, description="Freshness score (0.0-1.0)")
    processing_status: str = Field("pending", description="Processing status")
    anythingllm_workspace: Optional[str] = Field(None, description="AnythingLLM workspace slug")
    anythingllm_document_id: Optional[str] = Field(None, description="AnythingLLM document ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class SearchResult(BaseModel):
    """
    Represents a search result from vector database or cache.
    """
    content_id: str = Field(..., description="Content identifier")
    title: str = Field(..., description="Document title")
    source_url: str = Field(..., description="Source URL")
    technology: str = Field(..., description="Technology/framework")
    excerpt: str = Field(..., description="Relevant content excerpt")
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")
    quality_score: float = Field(..., description="Content quality score (0.0-1.0)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SearchRequest(BaseModel):
    """
    Search request with query and filtering options.
    """
    query: str = Field(..., description="Search query")
    technology_hint: Optional[str] = Field(None, description="Technology filter hint")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    workspace_slugs: Optional[List[str]] = Field(None, description="Workspace filters")


class SearchResponse(BaseModel):
    """
    Complete search response with results and metadata.
    """
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    cache_hit: bool = Field(..., description="Whether results came from cache")
    technology_hint: Optional[str] = Field(None, description="Technology hint used")


class UploadResult(BaseModel):
    """
    Result of document upload operation to AnythingLLM.
    
    Used by AnythingLLM client to return upload status and details.
    """
    document_id: str = Field(..., description="Document identifier")
    workspace_slug: str = Field(..., description="Target workspace slug")
    total_chunks: int = Field(..., description="Total number of chunks")
    successful_uploads: int = Field(..., description="Successfully uploaded chunks")
    failed_uploads: int = Field(..., description="Failed chunk uploads")
    uploaded_chunk_ids: List[str] = Field(..., description="List of successfully uploaded chunk IDs")
    failed_chunk_ids: List[str] = Field(..., description="List of failed chunk IDs")
    errors: List[str] = Field(..., description="List of error messages")


class HealthCheckResult(BaseModel):
    """
    Health check result for system components.
    """
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Component-specific health info")
    version: str = Field(..., description="System version")