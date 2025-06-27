"""
Activity Tracking API Endpoints
Recent activity, audit logs, and system events for admin interface
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import ActivityResponse, ActivityItem
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
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/recent - Get recent system activity
    """
    try:
        # Mock recent activity data for now
        # In real implementation, query from activity logs table
        recent_activities = [
            ActivityItem(
                id=f"activity_{i}",
                type="search",
                message=f"User performed search query: 'python async'",
                timestamp=datetime.utcnow() - timedelta(minutes=i*5),
                details=f"Query returned {10-i} results"
            ) for i in range(1, min(limit, 6))
        ]
        
        recent_activities.extend([
            ActivityItem(
                id="config_update",
                type="config",
                message="System configuration updated",
                timestamp=datetime.utcnow() - timedelta(hours=2),
                details="Updated LLM provider settings"
            ),
            ActivityItem(
                id="index_update",
                type="index",
                message="Document collection reindexed",
                timestamp=datetime.utcnow() - timedelta(hours=6),
                details="Python documentation collection updated"
            )
        ])
        
        # Filter by type if requested
        if activity_type:
            recent_activities = [a for a in recent_activities if a.type == activity_type]
        
        return recent_activities[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent activity")


@router.get("/admin/activity/searches", response_model=List[ActivityItem], tags=["admin"])
@limiter.limit("30/minute")
async def get_recent_searches(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/searches - Get recent search queries
    """
    try:
        # Mock search activity data
        search_activities = [
            ActivityItem(
                id=f"search_{i}",
                type="search",
                message=f"Search: '{query}'",
                timestamp=datetime.utcnow() - timedelta(minutes=i*3),
                details=f"Technology: {tech}, Results: {results}"
            ) for i, (query, tech, results) in enumerate([
                ("python async patterns", "python", 15),
                ("react hooks tutorial", "react", 23),
                ("docker compose setup", "docker", 8),
                ("fastapi authentication", "python", 12),
                ("javascript promises", "javascript", 19)
            ])
        ]
        
        return search_activities[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get recent searches: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent searches")


@router.get("/admin/activity/errors", response_model=List[ActivityItem], tags=["admin"])
@limiter.limit("30/minute")
async def get_recent_errors(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    db_manager: DatabaseManager = Depends(get_database_manager)
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
                details="OpenAI API connection timed out after 30 seconds"
            ),
            ActivityItem(
                id="error_2",
                type="error",
                message="Search index unavailable",
                timestamp=datetime.utcnow() - timedelta(hours=4),
                details="AnythingLLM workspace temporarily unavailable"
            )
        ]
        
        return error_activities[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent errors")


@router.get("/admin/dashboard", tags=["admin"])
@limiter.limit("20/minute")
async def get_dashboard_data(
    request: Request,
    db_manager: DatabaseManager = Depends(get_database_manager)
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
                    "average_response_time_ms": 85
                },
                "content_stats": {
                    "total_documents": 15000,
                    "collections": 25,
                    "last_update": datetime.utcnow().isoformat(),
                    "pending_uploads": 3
                },
                "system_stats": {
                    "uptime_seconds": 86400,
                    "memory_usage_percent": 65,
                    "cpu_usage_percent": 12
                },
                "cache_stats": {
                    "hit_rate": 0.78,
                    "total_requests": 25000
                }
            },
            "recent_activity": [
                {
                    "id": f"activity_{i}",
                    "type": ["search", "config", "index", "upload"][i % 4],
                    "message": f"Recent activity {i}",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=i*10)).isoformat()
                } for i in range(5)
            ],
            "providers": {
                "configured": 2,
                "available": 3,
                "active": 1
            },
            "health": {
                "overall_status": "healthy",
                "services_up": 4,
                "services_total": 4
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")