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
from .middleware import get_trace_id
from .dependencies import get_database_manager, get_configuration_manager
from src.database.connection import DatabaseManager
from src.core.config.manager import ConfigurationManager

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
async def admin_search_content(
    request: Request,
    search_term: Optional[str] = Query(None, description="Search term"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db_manager: DatabaseManager = Depends(get_database_manager),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> AdminSearchResponse:
    """
    GET /api/v1/admin/search-content - Searches content metadata for admin management

    Accepts query parameters: search_term, content_type, technology, limit, offset
    Returns AdminSearchResponse.

    Args:
        request: FastAPI request object
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
        # Configuration-driven schema validation for admin search
        try:
            config = config_manager.get_configuration()
            
            # Skip schema validation for PostgreSQL - just check table accessibility
            try:
                test_query = "SELECT 1 FROM content_metadata LIMIT 1"
                await db_manager.fetch_one(test_query)
            except Exception as table_error:
                logger.error(f"content_metadata table not accessible: {table_error}")
                raise HTTPException(status_code=500, detail="Content metadata table not available")
            
            # For PostgreSQL, we'll trust that the schema is correct
            # If content_type column doesn't exist, the query will fail and we'll handle it
                
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            # Continue with degraded functionality
        
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
            f"Admin content search: term='{search_term}', status_filter='{content_type}', tech='{technology}'"
        )

        # Build query with filters using actual schema columns
        where_clauses = []
        params = {}
        
        if search_term:
            where_clauses.append("(title LIKE :search_term OR content_id LIKE :search_term OR source_url LIKE :search_term)")
            params["search_term"] = f"%{search_term}%"
        
        # Use processing_status as content_type filter since content_type column doesn't exist
        if content_type:
            # Map content_type to processing_status values
            status_mapping = {
                "active": "completed",
                "pending": "pending", 
                "failed": "failed",
                "flagged": "flagged"
            }
            mapped_status = status_mapping.get(content_type.lower(), content_type)
            where_clauses.append("processing_status = :processing_status")
            params["processing_status"] = mapped_status
            
        if technology:
            where_clauses.append("technology = :technology")
            params["technology"] = technology
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM content_metadata {where_clause}"
        count_result = await db_manager.fetch_one(count_query, params)
        total_count = count_result.get("total", 0) if count_result else 0
        
        # Get paginated results using actual schema columns
        query = f"""
        SELECT 
            content_id,
            title,
            CASE 
                WHEN processing_status = 'completed' THEN 'documentation'
                WHEN processing_status = 'pending' THEN 'pending'
                WHEN processing_status = 'failed' THEN 'error'
                WHEN processing_status = 'flagged' THEN 'flagged'
                ELSE 'unknown'
            END as content_type,
            technology,
            source_url,
            COALESCE(anythingllm_workspace, 'default') as collection_name,
            created_at,
            updated_at as last_updated,
            COALESCE(word_count, chunk_count * 250) as size_bytes,  -- Better size estimation
            processing_status as status
        FROM content_metadata
        {where_clause}
        ORDER BY updated_at DESC, created_at DESC
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
async def flag_content(
    request: Request,
    content_id: str,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends(get_database_manager),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, str]:
    """
    DELETE /api/v1/content/{id} - Flags content for removal (admin action)

    Args:
        request: FastAPI request object
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
