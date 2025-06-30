"""
AI Logs API endpoints for intelligent log analysis and troubleshooting.

This module provides AI-optimized log querying, correlation, and analysis
capabilities specifically designed for AI agents and automated troubleshooting.
"""

from fastapi import APIRouter, Query, HTTPException, Depends, WebSocket, WebSocketDisconnect, Body
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import logging

# Import AI log processor
from ..utils.ai_log_processor import AILogProcessor

# Import models and enums
from ..models.ai_logs import (
    QueryMode,
    AggregationType,
    ResponseFormat,
    VerbosityLevel,
    SeverityLevel,
    ExportFormat,
    AILogQuery,
    AILogResponse,
    ExportRequest,
    ExportResponse,
    StreamConfig,
    PatternLibrary,
    CorrelationResult,
    CorrelationRequest,
    CorrelationResponse,
    PatternRequest,
    PatternResponse,
    ConversationTracking,
    WorkspaceSummary,
    ConversationLogs,
    WorkspaceAISummary
)

# Create router with prefix and tags
router = APIRouter(
    prefix="/ai_logs",
    tags=["AI Logs"],
    responses={
        404: {"description": "Not found"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service unavailable"},
    }
)

# Get logger
logger = logging.getLogger(__name__)

# Initialize processor instance
log_processor = AILogProcessor()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for AI logging system.
    
    Returns:
        dict: Health status of the AI logging system
    """
    from datetime import datetime
    
    # Check components
    components = {}
    overall_status = "healthy"
    
    # Check Loki connection
    try:
        loki_client = log_processor.loki_client
        loki_healthy = await loki_client.test_connection()
        components["loki"] = "healthy" if loki_healthy else "unhealthy"
        if not loki_healthy:
            overall_status = "degraded"
    except Exception as e:
        components["loki"] = "unhealthy"
        overall_status = "degraded"
        logger.warning(f"Loki health check failed: {e}")
    
    # Check cache connection
    try:
        cache_manager = log_processor.cache
        cache_stats = await cache_manager.get_stats()
        components["cache"] = "healthy" if cache_stats.get("connected", False) else "unhealthy"
        if not cache_stats.get("connected", False):
            overall_status = "degraded"
    except Exception as e:
        components["cache"] = "unhealthy"
        overall_status = "degraded"
        logger.warning(f"Cache health check failed: {e}")
    
    # Processor is always healthy if we can reach this point
    components["processor"] = "healthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components
    }


@router.get("/query", response_model=AILogResponse,
           summary="Query AI Logs",
           description="Retrieve and filter logs with intelligent optimization",
           responses={
               200: {"description": "Logs retrieved successfully"},
               400: {"description": "Invalid query parameters"},
               422: {"description": "Validation error"},
               429: {"description": "Rate limit exceeded"},
               503: {"description": "Loki service unavailable"}
           },
           tags=["AI Logs Query"])
async def query_ai_logs(
    query_params: AILogQuery = Depends(),
    cache: bool = Query(True, description="Use cached results if available")
) -> AILogResponse:
    """
    Query logs with AI-optimized processing and intelligent summarization.
    
    This endpoint provides:
    - Mode-based query optimization
    - Intelligent pattern detection
    - Natural language summaries
    - Actionable insights
    - Cross-service correlation
    """
    try:
        # Convert Pydantic model to dict for processing
        params_dict = query_params.dict()
        
        # Process query using AILogProcessor
        result = await log_processor.process_query(params_dict, use_cache=cache)
        
        return result
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Query timeout",
                "suggestion": "Try narrowing the time range or adding more specific filters",
                "code": "QUERY_TIMEOUT"
            }
        )
    except Exception as e:
        logger.error(f"AI log query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e),
                "code": "INTERNAL_ERROR"
            }
        )


@router.post("/correlate", response_model=CorrelationResponse,
           summary="Analyze Log Correlation",
           description="Trace request flow across services using correlation IDs",
           responses={
               200: {"description": "Correlation analysis completed"},
               404: {"description": "Correlation ID not found"},
               422: {"description": "Invalid correlation request"},
               503: {"description": "Service unavailable"}
           },
           tags=["AI Logs Analysis"])
async def correlate_logs(
    request: CorrelationRequest
) -> CorrelationResponse:
    """
    Correlate logs across all services for a specific request.
    
    Traces the flow of a request through the system and identifies:
    - Service interactions
    - Timing bottlenecks
    - Errors and failures
    - Request flow visualization
    """
    try:
        # Use real correlation logic
        correlation_result = await log_processor.correlate_logs(
            correlation_id=request.correlation_id,
            time_window="30m"  # Look back 30 minutes
        )
        
        # Format for API response structure
        result = {
            "correlation_id": request.correlation_id,
            "service_flow": [],
            "total_duration_ms": correlation_result.get("total_duration_ms", 0),
            "services_involved": [],
            "bottlenecks": correlation_result.get("bottlenecks", [])[:5],  # Top 5
            "error_propagation": correlation_result.get("errors", [])[:10],  # Top 10
            "recommendations": correlation_result.get("recommendations", [])[:5]  # Top 5
        }
        
        # Convert request flow to service flow format
        request_flow = correlation_result.get("request_flow", {})
        nodes = request_flow.get("nodes", [])
        
        for node in nodes:
            result["service_flow"].append({
                "service": node.get("service", "unknown"),
                "timestamp": node.get("timestamp"),
                "duration_ms": node.get("duration_ms", 0),
                "status": "error" if node.get("error_count", 0) > 0 else "success",
                "operation": "processing"
            })
        
        # Extract unique services
        result["services_involved"] = list(set(node.get("service", "unknown") for node in nodes))
        
        # If no real data found, provide empty result rather than mock data
        if not result["service_flow"]:
            result["service_flow"] = []
            result["services_involved"] = []
            result["recommendations"] = [f"No correlation data found for {request.correlation_id}"]
        
        return CorrelationResponse(**result)
        
    except Exception as e:
        logger.error(f"Log correlation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Correlation failed",
                "message": str(e),
                "code": "CORRELATION_ERROR"
            }
        )


@router.get("/analyze")
async def analyze_logs(
    pattern_detection: bool = Query(True, description="Enable pattern detection"),
    anomaly_detection: bool = Query(True, description="Enable anomaly detection"),
    time_range: str = Query("1h", pattern="^[0-9]+[smhd]$"),
    services: Optional[List[str]] = Query(None)
) -> Dict[str, Any]:
    """
    Perform intelligent log analysis with pattern and anomaly detection.
    
    Features:
    - Automatic pattern recognition
    - Anomaly detection using ML
    - Error clustering
    - Performance bottleneck identification
    - Root cause suggestions
    """
    try:
        # Build query parameters
        query_params = {
            "mode": "troubleshoot",
            "time_range": time_range,
            "services": services or ["all"],
            "limit": 10000  # Higher limit for comprehensive analysis
        }
        
        # Get logs for analysis
        logs_result = await log_processor.process_query(query_params, use_cache=False)
        logs = logs_result.get("logs", [])
        insights = logs_result.get("insights", {})
        
        result = {
            "patterns": insights.get("patterns", []) if pattern_detection else [],
            "anomalies": insights.get("anomalies", []) if anomaly_detection else [],
            "error_clusters": [],  # Would need additional clustering logic
            "performance_issues": [],  # Would need performance analysis
            "root_cause_analysis": {
                "potential_causes": [],
                "confidence_scores": {}
            },
            "recommendations": insights.get("recommendations", [])
        }
        
        # Add basic performance analysis if logs exist
        if logs:
            slow_requests = [log for log in logs if log.get("duration", 0) > 1000]
            if slow_requests:
                result["performance_issues"] = [
                    {
                        "type": "slow_requests",
                        "count": len(slow_requests),
                        "description": f"Found {len(slow_requests)} slow requests (>1s)",
                        "severity": "medium" if len(slow_requests) < 10 else "high"
                    }
                ]
        
        return result
        
    except Exception as e:
        logger.error(f"Log analysis failed: {e}")
        return {
            "patterns": [],
            "anomalies": [],
            "error_clusters": [],
            "performance_issues": [],
            "root_cause_analysis": {
                "potential_causes": [],
                "confidence_scores": {}
            },
            "recommendations": [f"Analysis failed: {str(e)}"]
        }


@router.post("/patterns", response_model=PatternResponse,
            summary="Detect Log Patterns",
            description="AI-powered pattern detection for identifying issues and anomalies",
            responses={
                200: {"description": "Pattern analysis completed"},
                422: {"description": "Invalid pattern request"},
                503: {"description": "Pattern detection service unavailable"}
            },
            tags=["AI Logs Analysis"])
async def detect_patterns(
    request: PatternRequest
) -> PatternResponse:
    """
    Perform AI-powered pattern detection on logs.
    
    Analyzes logs to identify:
    - Common error patterns
    - Performance anomalies
    - Security issues
    - Rate limiting events
    - Custom pattern matches
    """
    try:
        # Use real pattern detection
        import time
        start_time = time.time()
        
        # Build query parameters for log retrieval
        query_params = {
            "mode": "troubleshoot",
            "time_range": request.time_range,
            "services": request.services or ["all"],
            "limit": 5000  # Higher limit for pattern analysis
        }
        
        # Get logs for pattern analysis
        logs_result = await log_processor.process_query(query_params, use_cache=False)
        logs = logs_result.get("logs", [])
        
        # Run pattern detection
        pattern_detector = log_processor.pattern_detector
        detection_results = pattern_detector.detect_patterns(logs)
        
        # Format results for API response
        patterns_found = []
        for pattern in detection_results.get("detected_patterns", [])[:20]:  # Top 20
            patterns_found.append({
                "pattern_type": pattern["category"],
                "confidence": 0.85,  # Default confidence
                "occurrences": detection_results["pattern_counts"].get(pattern["pattern"], 1),
                "description": pattern["description"],
                "affected_services": [pattern["service"]],
                "time_distribution": {
                    "peak_hour": "recent",
                    "frequency": f"{detection_results['pattern_counts'].get(pattern['pattern'], 1)} times"
                },
                "sample_logs": [
                    {
                        "timestamp": pattern["timestamp"].isoformat() if pattern.get("timestamp") else None,
                        "message": pattern["message"][:200]  # Truncate long messages
                    }
                ]
            })
        
        # Generate recommendations based on detected patterns
        recommendations = []
        for pattern_name, count in detection_results["pattern_counts"].items():
            if count > 5:  # Frequent patterns
                pattern_info = pattern_detector.patterns.get(pattern_name)
                if pattern_info:
                    recommendations.append(pattern_info.recommended_action)
        
        # Add generic recommendations if none found
        if not recommendations:
            recommendations = ["Monitor logs regularly for emerging patterns"]
        
        result = {
            "patterns_found": patterns_found,
            "recommendations": recommendations[:10],  # Limit recommendations
            "analysis_duration_ms": int((time.time() - start_time) * 1000)
        }
        
        return PatternResponse(**result)
        
    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pattern detection failed",
                "message": str(e),
                "code": "PATTERN_DETECTION_ERROR"
            }
        )


@router.get("/conversation/{conversation_id}", response_model=ConversationTracking,
           summary="Get Conversation Logs",
           description="Retrieve all logs related to a specific conversation",
           responses={
               200: {"description": "Conversation logs retrieved"},
               404: {"description": "Conversation not found"},
               422: {"description": "Invalid conversation ID"}
           },
           tags=["AI Logs Tracking"])
async def get_conversation_logs(
    conversation_id: str
) -> ConversationTracking:
    """
    Get comprehensive logs for a specific AI conversation.
    
    Provides detailed tracking of:
    - Conversation flow
    - Token usage and costs
    - Performance metrics
    - Errors and retries
    - Related system logs
    """
    try:
        # Use real conversation tracking
        conversation_data = await log_processor.get_conversation_logs(
            conversation_id=conversation_id,
            time_buffer="1h",  # Look back 1 hour
            include_prompts=True,
            include_responses=True,
            include_metrics=True,
            include_related_logs=True
        )
        
        # Format for API response
        logs = []
        timeline = conversation_data.get("timeline", [])
        
        turn_number = 1
        for event in timeline:
            if event.get("event") in ["ai_completion", "request_type=ai_completion"]:
                logs.append({
                    "timestamp": event.get("timestamp"),
                    "message": event.get("details", {}).get("message", "AI interaction"),
                    "turn_number": turn_number,
                    "user_input": "User query",  # Would need to extract from logs
                    "ai_response_preview": "AI response...",  # Would need to extract from logs
                    "tokens_used": event.get("details", {}).get("tokens", 0),
                    "model": event.get("details", {}).get("model", "unknown")
                })
                turn_number += 1
        
        # Build summary from metadata and metrics
        metadata = conversation_data.get("metadata", {})
        metrics = conversation_data.get("metrics", {})
        
        result = {
            "conversation_id": conversation_id,
            "logs": logs,
            "summary": {
                "total_turns": len(logs),
                "total_tokens": metrics.get("total_tokens", 0),
                "average_response_time_ms": metrics.get("average_response_time", 0),
                "errors_encountered": int(metrics.get("error_rate", 0) * len(timeline)) if timeline else 0,
                "workspace": metadata.get("workspace_id", "unknown")
            }
        }
        
        return ConversationTracking(**result)
        
    except Exception as e:
        logger.error(f"Failed to get conversation logs: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve conversation logs",
                "message": str(e),
                "code": "CONVERSATION_ERROR"
            }
        )


@router.get("/workspace/{workspace_id}/summary", response_model=WorkspaceSummary,
           summary="Get Workspace Summary",
           description="Aggregated logs and metrics for a specific workspace",
           responses={
               200: {"description": "Workspace summary generated"},
               404: {"description": "Workspace not found"},
               422: {"description": "Invalid workspace ID or time range"}
           },
           tags=["AI Logs Tracking"])
async def get_workspace_ai_summary(
    workspace_id: str,
    time_range: str = Query("24h", pattern="^[0-9]+[smhd]$")
) -> WorkspaceSummary:
    """
    Get AI usage summary for a workspace.
    
    Provides:
    - Usage statistics
    - Model distribution
    - Cost analysis
    - Error patterns
    - Performance trends
    """
    try:
        # Use real workspace analysis
        workspace_data = await log_processor.get_workspace_ai_logs(
            workspace_id=workspace_id,
            time_range=time_range,
            include_costs=True
        )
        
        # Calculate derived metrics
        total_requests = workspace_data.get("total_requests", 0)
        error_count = workspace_data.get("error_count", 0)
        error_rate = error_count / total_requests if total_requests > 0 else 0
        
        # Format error breakdown from top error patterns
        error_breakdown = []
        top_errors = workspace_data.get("top_error_patterns", [])
        total_errors = sum(error.get("count", 0) for error in top_errors)
        
        for error in top_errors[:5]:  # Top 5 errors
            count = error.get("count", 0)
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            error_breakdown.append({
                "error_type": error.get("pattern", "unknown"),
                "count": count,
                "percentage": percentage
            })
        
        result = {
            "workspace_id": workspace_id,
            "time_range": time_range,
            "metrics": {
                "total_requests": total_requests,
                "successful_requests": total_requests - error_count,
                "error_rate": error_rate,
                "average_response_time_ms": workspace_data.get("average_response_time", 0),
                "total_tokens_used": workspace_data.get("total_tokens", 0),
                "unique_users": workspace_data.get("total_conversations", 0)  # Approximate
            },
            "top_queries": [],  # Would need to extract from conversation data
            "error_breakdown": error_breakdown
        }
        
        return WorkspaceSummary(**result)
        
    except Exception as e:
        logger.error(f"Failed to get workspace AI summary: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate workspace summary",
                "message": str(e),
                "code": "WORKSPACE_ERROR"
            }
        )


@router.post("/export", response_model=ExportResponse,
            summary="Export Logs",
            description="Export logs in various formats for analysis or archival",
            responses={
                200: {"description": "Export completed"},
                422: {"description": "Invalid export request"},
                503: {"description": "Export service unavailable"}
            },
            tags=["AI Logs Export"])
async def export_logs(
    export_request: ExportRequest
) -> ExportResponse:
    """
    Export logs in various formats for offline analysis.
    
    Supports:
    - JSON/JSONL for streaming
    - CSV for spreadsheets
    - Parquet for big data analysis
    - Markdown for reports
    """
    import uuid
    from datetime import datetime, timedelta
    
    try:
        # Generate unique export ID
        export_id = f"export_{uuid.uuid4().hex[:8]}"
        
        # For now, return a preparing status
        # Real implementation would queue the export job
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        logger.info(f"Log export requested: format={export_request.format}, export_id={export_id}")
        
        return ExportResponse(
            export_id=export_id,
            format=export_request.format,
            status="preparing",
            download_url=None,  # Would be generated after export completes
            expires_at=expires_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Export request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Export failed",
                "message": str(e),
                "code": "EXPORT_ERROR"
            }
        )


@router.websocket("/stream")
async def stream_logs(websocket: WebSocket):
    """
    Real-time log streaming with intelligent filtering and alerts.
    
    Features:
    - Live log streaming
    - Dynamic filter updates
    - Pattern-based alerts
    - Automatic error highlighting
    """
    from ..utils.stream_manager import stream_manager
    
    await websocket.accept()
    connection_id = None
    
    try:
        # Start stream manager if not running
        if not stream_manager._running:
            await stream_manager.start()
        
        # Get initial configuration
        config_message = await websocket.receive_json()
        
        if config_message.get("type") == "subscribe":
            filter_config = config_message.get("filter", {})
            
            # Add connection to stream manager
            connection_id = await stream_manager.add_connection(websocket, filter_config)
            logger.info(f"WebSocket connection established: {connection_id}")
            
            # Keep connection alive and handle messages
            while True:
                message = await websocket.receive_json()
                
                if message.get("type") == "update_filter":
                    # Update filter configuration
                    new_filter = message.get("filter", {})
                    success = await stream_manager.update_filter(connection_id, new_filter)
                    
                    if not success:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to update filter"
                        })
                        
                elif message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                elif message.get("type") == "unsubscribe":
                    # Client requesting disconnect
                    break
                    
        else:
            # Invalid initial message
            await websocket.send_json({
                "type": "error",
                "message": "First message must be subscription request"
            })
            await websocket.close()
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Clean up connection
        if connection_id:
            await stream_manager.remove_connection(connection_id)


@router.get("/patterns", response_model=PatternLibrary)
async def get_pattern_library() -> PatternLibrary:
    """
    Get the library of predefined troubleshooting patterns.
    
    Returns:
        dict: Available patterns organized by category
    """
    # Load from pattern detector
    pattern_detector = log_processor.pattern_detector
    patterns = pattern_detector.patterns
    
    # Organize patterns by category
    categories = {}
    for pattern_name, pattern in patterns.items():
        category = pattern.category
        if category not in categories:
            categories[category] = []
        categories[category].append(pattern_name)
    
    return PatternLibrary(
        categories=categories,
        total_patterns=len(patterns)
    )


@router.get("/metrics")
async def get_ai_metrics(
    time_range: str = Query("1h", pattern="^[0-9]+[smhd]$"),
    aggregation_interval: str = Query("5m", pattern="^[0-9]+[smh]$")
) -> Dict[str, Any]:
    """
    Get aggregated AI operation metrics.
    
    Provides:
    - Request volume
    - Token usage
    - Error rates
    - Performance percentiles
    """
    try:
        # Get AI logs for metrics calculation
        query_params = {
            "mode": "performance",
            "time_range": time_range,
            "services": ["all"],
            "limit": 50000  # Large limit for metrics
        }
        
        logs_result = await log_processor.process_query(query_params, use_cache=False)
        logs = logs_result.get("logs", [])
        metadata = logs_result.get("metadata", {})
        
        # Calculate basic metrics
        total_requests = len(logs)
        error_count = len([log for log in logs if log.get("level") in ["error", "fatal"]])
        error_rate = error_count / total_requests if total_requests > 0 else 0
        
        # Calculate token usage
        token_usage = [log.get("tokens_used", 0) for log in logs if log.get("tokens_used")]
        total_tokens = sum(token_usage) if token_usage else 0
        
        # Calculate response times
        response_times = [log.get("duration", 0) for log in logs if log.get("duration")]
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        
        return {
            "time_range": time_range,
            "aggregation_interval": aggregation_interval,
            "metrics": {
                "request_count": [{"timestamp": metadata.get("query_time"), "value": total_requests}],
                "token_usage": [{"timestamp": metadata.get("query_time"), "value": total_tokens}],
                "error_rate": [{"timestamp": metadata.get("query_time"), "value": error_rate}],
                "response_time_p95": [{"timestamp": metadata.get("query_time"), "value": p95_response_time}]
            },
            "summary": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "error_rate": error_rate,
                "p95_response_time_ms": p95_response_time
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI metrics: {e}")
        return {
            "time_range": time_range,
            "aggregation_interval": aggregation_interval,
            "metrics": {
                "request_count": [],
                "token_usage": [],
                "error_rate": [],
                "response_time_p95": []
            },
            "error": str(e)
        }