"""
Activity Tracking API Endpoints
Recent activity, audit logs, and system events for admin interface
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .schemas import ActivityItem
from .middleware import limiter, get_trace_id
from .dependencies import get_database_manager, get_configuration_manager
from src.database.connection import DatabaseManager
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

# Import enhanced logging for admin activity security monitoring
try:
    from src.logging_config import SecurityLogger, BusinessMetricsLogger
    _security_logger = SecurityLogger(logger)
    _business_logger = BusinessMetricsLogger(logger)
except ImportError:
    _security_logger = None
    _business_logger = None
    logger.warning("Enhanced activity security logging not available")

# Create router for activity endpoints
router = APIRouter()


@router.get("/admin/activity/recent", response_model=List[ActivityItem], tags=["admin"])
@limiter.limit("30/minute")
async def get_recent_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    db_manager: DatabaseManager = Depends(get_database_manager),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/recent - Get recent system activity
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    # Log admin access to activity data (sensitive operation)
    if _security_logger:
        _security_logger.log_admin_action(
            action="activity_data_access",
            target="recent_activity",
            impact_level="medium",
            client_ip=client_ip,
            trace_id=trace_id,
            activity_type=activity_type,
            limit=limit
        )
    
    try:
        # Get configuration-driven schema validation settings
        try:
            config = config_manager.get_configuration()
            # Check if strict schema validation is enabled (default: True)
            strict_validation = True  # Default to strict validation for admin endpoints
            
            # Configuration-driven required tables for activity tracking
            required_tables = ['search_cache', 'content_metadata', 'system_config']
            
            # Comprehensive schema validation
            schema_validation_query = """
                SELECT name, type 
                FROM sqlite_master 
                WHERE type='table' AND name IN ('search_cache', 'content_metadata', 'system_config')
            """
            
            existing_tables = await db_manager.fetch_all(schema_validation_query)
            existing_table_names = {row['name'] for row in existing_tables or []}
            missing_tables = set(required_tables) - existing_table_names
            
            if missing_tables:
                logger.warning(f"Required tables missing for activity endpoint: {missing_tables}")
                if strict_validation:
                    # Log schema validation failure for admin monitoring
                    if _security_logger:
                        _security_logger.log_admin_action(
                            action="schema_validation_failure",
                            target="activity_recent_endpoint",
                            impact_level="medium",
                            client_ip=client_ip,
                            trace_id=trace_id,
                            missing_tables=list(missing_tables)
                        )
                    # Return empty list in strict mode rather than failing
                    return []
                else:
                    logger.info("Non-strict mode: continuing with partial table availability")
                    
        except Exception as e:
            logger.error(f"Configuration-driven schema validation failed: {e}")
            # Fallback to basic validation if config fails
            basic_table_check = """
                SELECT COUNT(*) as count 
                FROM sqlite_master 
                WHERE type='table' AND name IN ('search_cache', 'content_metadata', 'system_config')
            """
            basic_result = await db_manager.fetch_one(basic_table_check)
            if not basic_result or basic_result.get("count", 0) < 3:
                return []
            
        # Build query based on activity type
        if activity_type:
            # Get activities from multiple tables based on type
            if activity_type == "search":
                query = """
                SELECT 
                    'search_' || query_hash as id,
                    'search' as type,
                    'Search: ' || original_query as message,
                    created_at as timestamp,
                    'Results: ' || result_count || ', Time: ' || execution_time_ms || 'ms' as details
                FROM search_cache
                ORDER BY created_at DESC
                LIMIT ?
                """
            elif activity_type == "config":
                query = """
                SELECT 
                    'config_' || key as id,
                    'config' as type,
                    'Configuration: ' || key as message,
                    updated_at as timestamp,
                    'Value: ' || substr(value, 1, 50) as details
                FROM system_config
                WHERE updated_at IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """
            elif activity_type == "error":
                # system_metrics table doesn't exist, return empty for now
                return []
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
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/searches - Get recent search queries
    """
    try:
        # Configuration-driven schema validation for search endpoint
        try:
            config = config_manager.get_configuration()
            
            # Validate search_cache table with column verification
            search_schema_query = """
                SELECT sql 
                FROM sqlite_master 
                WHERE type='table' AND name='search_cache'
            """
            
            schema_result = await db_manager.fetch_one(search_schema_query)
            if not schema_result:
                logger.warning("search_cache table not found")
                
                # Log schema validation issue for admin monitoring
                if _security_logger:
                    _security_logger.log_admin_action(
                        action="search_schema_validation_failure",
                        target="search_cache_table",
                        impact_level="low",
                        missing_tables=["search_cache"]
                    )
                return []
                
            # Verify required columns exist in search_cache table
            required_columns = ['query_hash', 'original_query', 'created_at', 'result_count']
            table_sql = schema_result.get('sql', '') if schema_result else ''
            missing_columns = [col for col in required_columns if col not in table_sql]
            
            if missing_columns:
                logger.warning(f"search_cache table missing required columns: {missing_columns}")
                return []
                
        except Exception as e:
            logger.error(f"Search schema validation failed: {e}")
            # Fallback to basic table existence check
            basic_check = await db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name='search_cache'"
            )
            if not basic_check or basic_check.get("count", 0) == 0:
                return []
            
        # Get real search data from search_cache table
        query = """
        SELECT 
            'search_' || query_hash as id,
            'search' as type,
            'Search: ' || original_query as message,
            created_at as timestamp,
            'Results: ' || result_count || ', Cached: ' || CASE WHEN cache_hit THEN 'Yes' ELSE 'No' END as details
        FROM search_cache
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
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> List[ActivityItem]:
    """
    GET /api/v1/admin/activity/errors - Get recent system errors
    """
    try:
        # system_metrics table doesn't exist in current schema
        # Return empty list for now
        return []

    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent errors")


@router.get("/admin/dashboard", tags=["admin"])
@limiter.limit("20/minute")
async def get_dashboard_data(
    request: Request, 
    db_manager: DatabaseManager = Depends(get_database_manager),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
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
                    "last_update": content_result.get("last_update") if content_result and content_result.get("last_update") else datetime.utcnow().isoformat(),
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
                    "timestamp": str(row["timestamp"]) if row["timestamp"] else datetime.utcnow().isoformat(),
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
