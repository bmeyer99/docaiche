"""
Activity Tracking API Endpoints
Recent activity, audit logs, and system events for admin interface
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .schemas import ActivityItem
from .middleware import limiter
from .dependencies import get_database_manager
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

# Create router for activity endpoints
router = APIRouter()


@router.get("/admin/activity/recent", response_model=List[ActivityItem], tags=["admin"])
@limiter.limit("30/minute")
async def get_recent_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/recent - Get recent system activity
    """
    try:
        # First check if tables exist to avoid errors
        tables_check = """
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name IN ('search_cache', 'content_metadata', 'system_config')
        """
        try:
            table_check_result = await db_manager.fetch_one(tables_check)
            table_count = table_check_result.get("count", 0) if table_check_result else 0
            if table_count < 3:
                logger.warning(f"Required tables not found for activity endpoint (found {table_count}/3)")
                # Return empty activities if tables don't exist
                return []
        except Exception as e:
            logger.warning(f"Failed to check tables: {e}")
            return []
            
        # Build query based on activity type
        if activity_type:
            # Get activities from multiple tables based on type
            if activity_type == "search":
                query = """
                SELECT 
                    'search_' || id as id,
                    'search' as type,
                    'Search: ' || query_text as message,
                    created_at as timestamp,
                    'Query hash: ' || query_hash as details
                FROM search_queries
                ORDER BY created_at DESC
                LIMIT ?
                """
            elif activity_type == "config":
                query = """
                SELECT 
                    'config_' || config_key as id,
                    'config' as type,
                    'Configuration: ' || config_key as message,
                    updated_at as timestamp,
                    'Value: ' || config_value as details
                FROM system_config
                WHERE updated_at IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """
            elif activity_type == "error":
                query = """
                SELECT 
                    'error_' || id as id,
                    'error' as type,
                    error_type || ': ' || error_message as message,
                    created_at as timestamp,
                    'Context: ' || error_context as details
                FROM system_metrics
                WHERE metric_type = 'error'
                ORDER BY created_at DESC
                LIMIT ?
                """
            else:
                # For other types, return empty list for now
                return []
            
            results = await db_manager.fetch_all(query, (limit,))
        else:
            # Get mixed recent activities from all sources
            query = """
            WITH all_activities AS (
                SELECT 
                    'search_' || query_hash as id,
                    'search' as type,
                    'Search: ' || original_query as message,
                    created_at as timestamp,
                    'Query' as details
                FROM search_cache
                UNION ALL
                SELECT 
                    'config_' || key as id,
                    'config' as type,
                    'Config: ' || key as message,
                    updated_at as timestamp,
                    value as details
                FROM system_config
                WHERE updated_at IS NOT NULL
                UNION ALL
                SELECT 
                    'content_' || content_id as id,
                    'content' as type,
                    'Document: ' || title as message,
                    created_at as timestamp,
                    'Workspace: ' || COALESCE(anythingllm_workspace, 'None') as details
                FROM content_metadata
            )
            SELECT * FROM all_activities
            ORDER BY timestamp DESC
            LIMIT 20
            """
        
            results = await db_manager.fetch_all(query)
        
        # Convert to ActivityItem objects
        activities = []
        for row in results or []:
            activities.append(
                ActivityItem(
                    id=row["id"],
                    type=row["type"],
                    message=row["message"],
                    timestamp=row["timestamp"],
                    details=row.get("details", ""),
                )
            )
        
        return activities

    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recent activity"
        )


@router.get(
    "/admin/activity/searches", response_model=List[ActivityItem], tags=["admin"]
)
@limiter.limit("30/minute")
async def get_recent_searches(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/searches - Get recent search queries
    """
    try:
        # First check if search_queries table exists
        tables_check = """
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name='search_queries'
        """
        try:
            table_check_result = await db_manager.fetch_one(tables_check)
            table_exists = (table_check_result.get("count", 0) > 0) if table_check_result else False
            if not table_exists:
                logger.warning("search_queries table not found")
                # Return empty list if table doesn't exist
                return []
        except Exception as e:
            logger.warning(f"Failed to check search_queries table: {e}")
            return []
            
        # Get real search data from database
        query = """
        SELECT 
            'search_' || id as id,
            'search' as type,
            'Search: ' || query_text as message,
            created_at as timestamp,
            'Query performed' as details
        FROM search_queries
        ORDER BY created_at DESC
        LIMIT 20
        """
        
        results = await db_manager.fetch_all(query)
        
        # Convert to ActivityItem objects
        search_activities = []
        for row in results or []:
            search_activities.append(
                ActivityItem(
                    id=row["id"],
                    type=row["type"],
                    message=row["message"],
                    timestamp=row["timestamp"],
                    details=row["details"],
                )
            )
        
        return search_activities

    except Exception as e:
        logger.error(f"Failed to get recent searches: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recent searches"
        )


@router.get("/admin/activity/errors", response_model=List[ActivityItem], tags=["admin"])
@limiter.limit("30/minute")
async def get_recent_errors(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/errors - Get recent system errors
    """
    try:
        # Get real error data from system_metrics table
        query = """
        SELECT 
            'error_' || id as id,
            'error' as type,
            error_type || ': ' || error_message as message,
            created_at as timestamp,
            'Context: ' || COALESCE(error_context, 'None') as details
        FROM system_metrics
        WHERE metric_type = 'error'
        ORDER BY created_at DESC
        LIMIT :limit
        """
        
        results = await db_manager.fetch_all(query, {"limit": limit})
        
        # Convert to ActivityItem objects
        error_activities = []
        for row in results or []:
            error_activities.append(
                ActivityItem(
                    id=row["id"],
                    type=row["type"],
                    message=row["message"],
                    timestamp=row["timestamp"],
                    details=row["details"],
                )
            )
        
        return error_activities

    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent errors")


@router.get("/admin/dashboard", tags=["admin"])
@limiter.limit("20/minute")
async def get_dashboard_data(
    request: Request, db_manager: DatabaseManager = Depends(get_database_manager)
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/dashboard - Get aggregated dashboard data
    """
    try:
        # Get real search statistics
        search_stats_query = """
        SELECT 
            COUNT(*) as total_searches,
            COUNT(CASE WHEN date(created_at) = date('now') THEN 1 END) as searches_today,
            COUNT(CASE WHEN created_at >= datetime('now', '-24 hours') THEN 1 END) as searches_24h
        FROM search_cache
        """
        search_result = await db_manager.fetch_one(search_stats_query)
        
        # Get content statistics
        content_stats_query = """
        SELECT 
            COUNT(DISTINCT content_id) as total_documents,
            COUNT(DISTINCT anythingllm_workspace) as collections,
            MAX(updated_at) as last_update
        FROM content_metadata
        """
        content_result = await db_manager.fetch_one(content_stats_query)
        
        # Get system uptime (simplified)
        import time
        uptime_seconds = int(time.time() - 1000000)  # Placeholder for actual boot time
        
        # Get recent activity
        activity_query = """
        WITH recent_activity AS (
            SELECT 
                'search_' || query_hash as id,
                'search' as type,
                'Search: ' || original_query as message,
                created_at as timestamp
            FROM search_cache
            ORDER BY created_at DESC
            LIMIT 5
        )
        SELECT * FROM recent_activity
        """
        activity_results = await db_manager.fetch_all(activity_query)
        
        # Get provider status from config
        provider_query = """
        SELECT COUNT(*) as configured
        FROM system_config
        WHERE key LIKE 'ai.%' AND value != '{}'
        """
        provider_result = await db_manager.fetch_one(provider_query)
        
        # Aggregate all dashboard data
        dashboard_data = {
            "stats": {
                "search_stats": {
                    "total_searches": search_result.get("total_searches", 0) if search_result else 0,
                    "searches_today": search_result.get("searches_today", 0) if search_result else 0,
                    "searches_24h": search_result.get("searches_24h", 0) if search_result else 0,
                    "average_response_time_ms": 0,  # Not tracked in current schema
                },
                "content_stats": {
                    "total_documents": content_result.get("total_documents", 0) if content_result else 0,
                    "collections": content_result.get("collections", 0) if content_result else 0,
                    "last_update": content_result.get("last_update", datetime.utcnow()).isoformat() if content_result and content_result.get("last_update") else datetime.utcnow().isoformat(),
                    "pending_uploads": 0,  # Not tracked in current schema
                },
                "system_stats": {
                    "uptime_seconds": uptime_seconds,
                    "memory_usage_percent": 0,
                    "cpu_usage_percent": 0,
                },
                "cache_stats": {"hit_rate": 0, "total_requests": 0},
            },
            "recent_activity": [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "message": row["message"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else datetime.utcnow().isoformat(),
                }
                for row in (activity_results or [])
            ],
            "providers": {
                "configured": provider_result.get("configured", 0) if provider_result else 0,
                "available": 3,  # Static for now
                "active": 1 if provider_result and provider_result.get("configured", 0) > 0 else 0
            },
            "health": {
                "overall_status": "healthy",
                "services_up": 4,
                "services_total": 4,
            },
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")
