"""
Admin API Endpoints - PRD-001: HTTP API Foundation
Admin search content and content management endpoints
"""

import logging
from datetime import datetime
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import AdminSearchResponse, AdminContentItem
from .middleware import limiter
from .dependencies import get_database_manager
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

# Create router for admin endpoints
router = APIRouter()


@router.get("/admin/search-content", response_model=AdminSearchResponse, tags=["admin"])
@limiter.limit("20/minute")
async def admin_search_content(
    request: Request,
    search_term: Optional[str] = Query(None, description="Search term"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> AdminSearchResponse:
    """
    GET /api/v1/admin/search-content - Searches content metadata for admin management

    Accepts query parameters: search_term, content_type, technology, limit, offset
    Returns AdminSearchResponse.

    Args:
        request: FastAPI request object (required for rate limiting)
        search_term: Optional search term filter
        content_type: Optional content type filter
        technology: Optional technology filter
        limit: Maximum number of results
        offset: Results offset for pagination
        db_manager: Database manager dependency

    Returns:
        AdminSearchResponse with content items and pagination
    """
    try:
        logger.info(
            f"Admin content search: term='{search_term}', type='{content_type}', tech='{technology}'"
        )

        # Build query with filters
        where_clauses = []
        params = {}
        
        if search_term:
            where_clauses.append("(title LIKE :search_term OR content_id LIKE :search_term)")
            params["search_term"] = f"%{search_term}%"
        
        if content_type:
            where_clauses.append("content_type = :content_type")
            params["content_type"] = content_type
            
        if technology:
            where_clauses.append("technology = :technology")
            params["technology"] = technology
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM content_metadata {where_clause}"
        count_result = await db_manager.fetch_one(count_query, params)
        total_count = count_result.get("total", 0) if count_result else 0
        
        # Get paginated results
        query = f"""
        SELECT 
            content_id,
            title,
            content_type,
            technology,
            source_url,
            anythingllm_workspace as collection_name,
            created_at,
            updated_at as last_updated,
            chunk_count * 1000 as size_bytes,  -- Approximate size
            'active' as status
        FROM content_metadata
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset
        
        results = await db_manager.fetch_all(query, params)
        
        # Convert to AdminContentItem objects
        items = []
        for row in results or []:
            items.append(AdminContentItem(
                content_id=row["content_id"],
                title=row["title"] or "Untitled",
                content_type=row["content_type"] or "document",
                technology=row["technology"] or "unknown",
                source_url=row["source_url"] or "",
                collection_name=row["collection_name"] or "default",
                created_at=row["created_at"] or datetime.utcnow(),
                last_updated=row["last_updated"] or datetime.utcnow(),
                size_bytes=row["size_bytes"] or 0,
                status=row["status"] or "active",
            ))

        return AdminSearchResponse(
            items=items,
            total_count=total_count,
            page=(offset // limit) + 1,
            page_size=limit,
            has_more=offset + limit < total_count,
        )

    except Exception as e:
        logger.error(f"Admin content search failed: {e}")
        raise HTTPException(status_code=500, detail="Admin content search failed")


@router.delete("/content/{content_id}", status_code=202, tags=["admin"])
@limiter.limit("10/minute")
async def flag_content(
    request: Request,
    content_id: str,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> Dict[str, str]:
    """
    DELETE /api/v1/content/{id} - Flags content for removal (admin action)

    Args:
        request: FastAPI request object (required for rate limiting)
        content_id: ID of content to flag for removal
        background_tasks: FastAPI background tasks for processing
        db_manager: Database manager dependency

    Returns:
        Confirmation message with HTTP 202
    """
    try:
        logger.info(f"Content flagged for removal: {content_id}")

        # Add background task to flag content (placeholder)
        def flag_content_task():
            logger.info(f"Flagging content for removal: {content_id}")
            # TODO: Implement content flagging logic

        background_tasks.add_task(flag_content_task)

        return {"message": f"Content {content_id} flagged for review"}

    except Exception as e:
        logger.error(f"Content flagging failed: {e}")
        raise HTTPException(status_code=500, detail="Content flagging failed")
