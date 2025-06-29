"""
Log Management API Endpoints
Provides log retrieval and streaming capabilities
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
import json
from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
import asyncio

from .dependencies import get_current_user_optional, require_role
from .middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# Service definitions
AVAILABLE_SERVICES = {
    "api": {
        "id": "api",
        "name": "DocAIche API",
        "container_pattern": "docaiche-api",
        "log_level": "INFO"
    },
    "admin-ui": {
        "id": "admin-ui", 
        "name": "Admin UI",
        "container_pattern": "docaiche-admin-ui",
        "log_level": "INFO"
    },
    "redis": {
        "id": "redis",
        "name": "Redis Cache",
        "container_pattern": "docaiche-redis",
        "log_level": "WARN"
    },
    "anythingllm": {
        "id": "anythingllm",
        "name": "AnythingLLM",
        "container_pattern": "docaiche-anythingllm",
        "log_level": "INFO"
    },
    "loki": {
        "id": "loki",
        "name": "Loki",
        "container_pattern": "docaiche-loki",
        "log_level": "INFO"
    },
    "prometheus": {
        "id": "prometheus",
        "name": "Prometheus",
        "container_pattern": "docaiche-prometheus",
        "log_level": "INFO"
    },
    "grafana": {
        "id": "grafana",
        "name": "Grafana",
        "container_pattern": "docaiche-grafana",
        "log_level": "INFO"
    }
}


@router.get("/services")
@limiter.limit("30/minute")
async def list_services(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    List all available services for log viewing
    
    Returns:
        List of services with their status and log configuration
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    # Get service status from containers
    services = []
    for service_id, service_info in AVAILABLE_SERVICES.items():
        # For now, assume all services are running
        # In production, this would check actual container status
        services.append({
            "id": service_info["id"],
            "name": service_info["name"],
            "status": "running",
            "log_level": service_info["log_level"]
        })
    
    return {"services": services}


@router.get("/{service_id}")
@limiter.limit("20/minute")
async def get_service_logs(
    request: Request,
    service_id: str,
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARN|WARNING|ERROR|FATAL)$"),
    start_time: Optional[datetime] = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end_time: Optional[datetime] = Query(default_factory=datetime.utcnow),
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retrieve logs for a specific service
    
    Args:
        service_id: ID of the service to get logs for
        level: Log level filter (DEBUG|INFO|WARN|ERROR|FATAL)
        start_time: Start time for log query
        end_time: End time for log query
        search: Search term to filter logs
        limit: Maximum number of logs to return
        offset: Offset for pagination
        
    Returns:
        Logs with metadata and pagination info
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    # Validate service exists
    if service_id not in AVAILABLE_SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    
    service_info = AVAILABLE_SERVICES[service_id]
    
    # Build Loki query
    query_parts = []
    query_parts.append(f'{{service_name=~"{service_info["container_pattern"]}.*"}}')
    
    if level:
        query_parts.append(f'|= "{level}"')
    
    if search:
        # Escape special regex characters in search term
        escaped_search = search.replace('"', '\\"')
        query_parts.append(f'|~ "{escaped_search}"')
    
    loki_query = " ".join(query_parts)
    
    # Query Loki
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://loki:3100/loki/api/v1/query_range",
                params={
                    "query": loki_query,
                    "start": int(start_time.timestamp() * 1e9),  # Nanoseconds
                    "end": int(end_time.timestamp() * 1e9),      # Nanoseconds
                    "limit": limit,
                    "direction": "backward"  # Most recent first
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Loki query failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="Failed to query logs")
            
            data = response.json()
            
    except httpx.TimeoutException:
        logger.error("Loki query timeout")
        raise HTTPException(status_code=504, detail="Log query timeout")
    except Exception as e:
        logger.error(f"Failed to query Loki: {e}")
        raise HTTPException(status_code=502, detail="Failed to query logs")
    
    # Parse and format logs
    logs = []
    total_logs = 0
    
    if data.get("status") == "success":
        for stream in data.get("data", {}).get("result", []):
            stream_labels = stream.get("stream", {})
            for value in stream.get("values", []):
                timestamp_ns, log_line = value
                total_logs += 1
                
                # Skip if before offset
                if total_logs <= offset:
                    continue
                
                # Parse timestamp
                timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)
                
                # Try to parse JSON log
                try:
                    log_data = json.loads(log_line)
                    message = log_data.get("message", log_line)
                    log_level = log_data.get("level", "INFO")
                    metadata = {k: v for k, v in log_data.items() 
                               if k not in ["message", "level", "timestamp"]}
                except json.JSONDecodeError:
                    # Plain text log
                    message = log_line
                    log_level = "INFO"
                    # Try to extract level from log line
                    for lvl in ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL"]:
                        if lvl in log_line.upper():
                            log_level = lvl
                            break
                    metadata = {}
                
                logs.append({
                    "timestamp": timestamp.isoformat() + "Z",
                    "level": log_level,
                    "service": service_id,
                    "message": message,
                    "metadata": {**metadata, **stream_labels}
                })
                
                # Stop if we have enough logs
                if len(logs) >= limit:
                    break
    
    return {
        "logs": logs,
        "total": total_logs,
        "has_more": total_logs > (offset + limit),
        "offset": offset,
        "limit": limit
    }


@router.websocket("/ws/{service_id}")
async def websocket_logs(
    websocket: WebSocket,
    service_id: str,
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARN|WARNING|ERROR|FATAL)$"),
    search: Optional[str] = Query(None, max_length=100)
):
    """
    WebSocket endpoint for real-time log streaming
    
    Args:
        websocket: WebSocket connection
        service_id: ID of the service to stream logs for
        level: Log level filter
        search: Search term to filter logs
    """
    await websocket.accept()
    
    # Validate service exists
    if service_id not in AVAILABLE_SERVICES:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Service '{service_id}' not found"}
        })
        await websocket.close()
        return
    
    service_info = AVAILABLE_SERVICES[service_id]
    
    # Build Loki query for tail
    query_parts = []
    query_parts.append(f'{{service_name=~"{service_info["container_pattern"]}.*"}}')
    
    if level:
        query_parts.append(f'|= "{level}"')
    
    if search:
        escaped_search = search.replace('"', '\\"')
        query_parts.append(f'|~ "{escaped_search}"')
    
    loki_query = " ".join(query_parts)
    
    try:
        # Start tailing logs
        async with httpx.AsyncClient(timeout=None) as client:
            # Use Loki's tail endpoint for real-time streaming
            async with client.stream(
                "GET",
                "http://loki:3100/loki/api/v1/tail",
                params={
                    "query": loki_query,
                    "delay_for": 0,
                    "limit": 100
                }
            ) as response:
                if response.status_code != 200:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Failed to connect to log stream"}
                    })
                    await websocket.close()
                    return
                
                # Send initial connected message
                await websocket.send_json({
                    "type": "connected",
                    "data": {"service": service_id}
                })
                
                # Stream logs
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        # Parse SSE format
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            
                            for stream in data.get("streams", []):
                                stream_labels = stream.get("stream", {})
                                for value in stream.get("values", []):
                                    timestamp_ns, log_line = value
                                    timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)
                                    
                                    # Parse log
                                    try:
                                        log_data = json.loads(log_line)
                                        message = log_data.get("message", log_line)
                                        log_level = log_data.get("level", "INFO")
                                        metadata = {k: v for k, v in log_data.items() 
                                                   if k not in ["message", "level", "timestamp"]}
                                    except json.JSONDecodeError:
                                        message = log_line
                                        log_level = "INFO"
                                        metadata = {}
                                    
                                    # Send log to client
                                    await websocket.send_json({
                                        "type": "log",
                                        "data": {
                                            "timestamp": timestamp.isoformat() + "Z",
                                            "level": log_level,
                                            "service": service_id,
                                            "message": message,
                                            "metadata": {**metadata, **stream_labels}
                                        }
                                    })
                    
                    except Exception as e:
                        logger.error(f"Error parsing log stream: {e}")
                        continue
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for service {service_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.get("/{service_id}/export")
@limiter.limit("5/minute")
async def export_logs(
    request: Request,
    service_id: str,
    format: str = Query("json", regex="^(json|csv|txt)$"),
    start_time: Optional[datetime] = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end_time: Optional[datetime] = Query(default_factory=datetime.utcnow),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Export logs in various formats
    
    Args:
        service_id: Service to export logs for
        format: Export format (json|csv|txt)
        start_time: Start time for export
        end_time: End time for export
        level: Log level filter
        search: Search filter
        
    Returns:
        Streaming response with exported logs
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    # Get logs
    logs_response = await get_service_logs(
        service_id=service_id,
        level=level,
        start_time=start_time,
        end_time=end_time,
        search=search,
        limit=10000,  # Higher limit for export
        offset=0,
        current_user=current_user
    )
    
    logs = logs_response["logs"]
    
    # Format based on requested type
    if format == "json":
        content = json.dumps(logs, indent=2)
        media_type = "application/json"
        filename = f"{service_id}_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    elif format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Timestamp", "Level", "Service", "Message", "Metadata"])
        
        # Write logs
        for log in logs:
            writer.writerow([
                log["timestamp"],
                log["level"],
                log["service"],
                log["message"],
                json.dumps(log.get("metadata", {}))
            ])
        
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"{service_id}_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    else:  # txt
        lines = []
        for log in logs:
            lines.append(
                f"[{log['timestamp']}] [{log['level']}] {log['service']}: {log['message']}"
            )
        content = "\n".join(lines)
        media_type = "text/plain"
        filename = f"{service_id}_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Return streaming response
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )