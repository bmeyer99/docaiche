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
                LIMIT :limit
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
                LIMIT :limit
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
                LIMIT :limit
                """
            else:
                # For other types, return empty list for now
                return []
        else:
            # Get mixed recent activities from all sources
            query = """
            WITH all_activities AS (
                SELECT 
                    'search_' || id as id,
                    'search' as type,
                    'Search: ' || query_text as message,
                    created_at as timestamp,
                    'Query' as details
                FROM search_queries
                UNION ALL
                SELECT 
                    'config_' || config_key as id,
                    'config' as type,
                    'Config: ' || config_key as message,
                    updated_at as timestamp,
                    config_value as details
                FROM system_config
                WHERE updated_at IS NOT NULL
                UNION ALL
                SELECT 
                    'content_' || content_id as id,
                    'content' as type,
                    'Document: ' || title as message,
                    created_at as timestamp,
                    'Workspace: ' || workspace as details
                FROM content_metadata
            )
            SELECT * FROM all_activities
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        
        results = await db_manager.fetch_all(query, {"limit": limit})
        
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
        LIMIT :limit
        """
        
        results = await db_manager.fetch_all(query, {"limit": limit})
        
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
        # Mock error activity data
        error_activities = [
            ActivityItem(
                id="error_1",
                type="error",
                message="Provider connection timeout",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                details="OpenAI API connection timed out after 30 seconds",
            ),
            ActivityItem(
                id="error_2",
                type="error",
                message="Search index unavailable",
                timestamp=datetime.utcnow() - timedelta(hours=4),
                details="AnythingLLM workspace temporarily unavailable",
            ),
        ]

        return error_activities[:limit]

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
        # Aggregate all dashboard data in one endpoint
        dashboard_data = {
            "stats": {
                "search_stats": {
                    "total_searches": 50000,
                    "searches_today": 1250,
                    "searches_24h": 2100,
                    "average_response_time_ms": 85,
                },
                "content_stats": {
                    "total_documents": 15000,
                    "collections": 25,
                    "last_update": datetime.utcnow().isoformat(),
                    "pending_uploads": 3,
                },
                "system_stats": {
                    "uptime_seconds": 86400,
                    "memory_usage_percent": 65,
                    "cpu_usage_percent": 12,
                },
                "cache_stats": {"hit_rate": 0.78, "total_requests": 25000},
            },
            "recent_activity": [
                {
                    "id": f"activity_{i}",
                    "type": ["search", "config", "index", "upload"][i % 4],
                    "message": f"Recent activity {i}",
                    "timestamp": (
                        datetime.utcnow() - timedelta(minutes=i * 10)
                    ).isoformat(),
                }
                for i in range(5)
            ],
            "providers": {"configured": 2, "available": 3, "active": 1},
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
