"""
Admin API Endpoints - PRD-001: HTTP API Foundation
Admin search content and content management endpoints
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import AdminSearchResponse, AdminContentItem
from .middleware import limiter, get_trace_id
from .dependencies import get_database_manager
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

# Import enhanced logging for admin security monitoring
try:
    from src.logging_config import SecurityLogger, BusinessMetricsLogger
    _security_logger = SecurityLogger(logger)
    _business_logger = BusinessMetricsLogger(logger)
except ImportError:
    _security_logger = None
    _business_logger = None
    logger.warning("Enhanced admin security logging not available")

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
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        # Log admin action with security context
        if _security_logger:
            _security_logger.log_admin_action(
                action="content_search",
                target="content_metadata",
                impact_level="low",
                client_ip=client_ip,
                search_term=search_term,
                technology=technology,
                limit=limit,
                offset=offset,
                trace_id=trace_id
            )
            
        logger.info(
            f"Admin content search: term='{search_term}', type='{content_type}', tech='{technology}'"
        )

        # Build query with filters
        where_clauses = []
        params = {}
        
        if search_term:
            where_clauses.append("(title LIKE :search_term OR content_id LIKE :search_term)")
            params["search_term"] = f"%{search_term}%"
        
        # Note: content_type column doesn't exist in current schema
        # if content_type:
        #     where_clauses.append("content_type = :content_type")
        #     params["content_type"] = content_type
            
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
            'documentation' as content_type,  -- Default value since column doesn't exist
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

        duration_ms = (time.time() - start_time) * 1000
        
        # Log business metrics for admin search
        if _business_logger:
            _business_logger.log_content_operation(
                operation="admin_search",
                content_id="multiple",
                content_type="admin_query",
                result_count=len(items),
                total_available=total_count,
                duration_ms=duration_ms,
                client_ip=client_ip,
                trace_id=trace_id
            )
        
        return AdminSearchResponse(
            items=items,
            total_count=total_count,
            page=(offset // limit) + 1,
            page_size=limit,
            has_more=offset + limit < total_count,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log admin action failure
        if _security_logger:
            _security_logger.log_admin_action(
                action="content_search_failed",
                target="content_metadata",
                impact_level="low",
                client_ip=client_ip,
                error_message=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id
            )
        
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
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        # Log high-impact admin action - content deletion
        if _security_logger:
            _security_logger.log_admin_action(
                action="content_deletion_request",
                target=content_id,
                impact_level="high",
                client_ip=client_ip,
                trace_id=trace_id,
                requires_audit=True
            )
            
        logger.info(f"Content flagged for removal: {content_id}")

        # Add background task to flag content (placeholder)
        def flag_content_task():
            task_start = time.time()
            logger.info(f"Flagging content for removal: {content_id}")
            
            # Log business metrics for content flagging
            if _business_logger:
                _business_logger.log_content_operation(
                    operation="content_flagged",
                    content_id=content_id,
                    content_type="admin_action",
                    client_ip=client_ip,
                    trace_id=trace_id,
                    background_task=True
                )
            
            # TODO: Implement content flagging logic
            
            task_duration = (time.time() - task_start) * 1000
            if _security_logger:
                _security_logger.log_admin_action(
                    action="content_flagging_completed",
                    target=content_id,
                    impact_level="high",
                    client_ip=client_ip,
                    duration_ms=task_duration,
                    trace_id=trace_id
                )

        background_tasks.add_task(flag_content_task)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful admin action
        if _security_logger:
            _security_logger.log_admin_action(
                action="content_deletion_initiated",
                target=content_id,
                impact_level="high",
                client_ip=client_ip,
                duration_ms=duration_ms,
                trace_id=trace_id,
                status="success"
            )

        return {"message": f"Content {content_id} flagged for review"}

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log admin action failure with high severity
        if _security_logger:
            _security_logger.log_admin_action(
                action="content_deletion_failed",
                target=content_id,
                impact_level="medium",
                client_ip=client_ip,
                error_message=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id,
                requires_review=True
            )
        
        logger.error(f"Content flagging failed: {e}")
        raise HTTPException(status_code=500, detail="Content flagging failed")
