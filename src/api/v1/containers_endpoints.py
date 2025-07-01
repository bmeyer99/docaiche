"""
Container Management API Endpoints
Provides container monitoring and management capabilities
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import docker
from docker.errors import NotFound, APIError, ContainerError
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
import subprocess
import shlex

from .dependencies import get_current_user_optional, require_role
from .middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/containers", tags=["containers"])

# Initialize Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    docker_client = None


def calculate_cpu_percent(stats: dict) -> float:
    """Calculate CPU percentage from Docker stats"""
    try:
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                       stats["precpu_stats"]["system_cpu_usage"]
        
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100.0
            return round(cpu_percent, 2)
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return 0.0


def calculate_memory_stats(stats: dict) -> Dict[str, float]:
    """Calculate memory statistics from Docker stats"""
    try:
        usage = stats["memory_stats"]["usage"]
        limit = stats["memory_stats"]["limit"]
        
        # Calculate cache if available
        cache = stats["memory_stats"].get("stats", {}).get("cache", 0)
        actual_usage = usage - cache
        
        return {
            "usage_mb": round(actual_usage / (1024 * 1024), 2),
            "limit_mb": round(limit / (1024 * 1024), 2),
            "percent": round((actual_usage / limit) * 100, 2) if limit > 0 else 0
        }
    except (KeyError, TypeError, ZeroDivisionError):
        return {
            "usage_mb": 0,
            "limit_mb": 0,
            "percent": 0
        }


def calculate_network_stats(stats: dict) -> Dict[str, float]:
    """Calculate network I/O from Docker stats"""
    try:
        networks = stats.get("networks", {})
        rx_bytes = 0
        tx_bytes = 0
        
        for interface in networks.values():
            rx_bytes += interface.get("rx_bytes", 0)
            tx_bytes += interface.get("tx_bytes", 0)
        
        return {
            "rx_mb": round(rx_bytes / (1024 * 1024), 2),
            "tx_mb": round(tx_bytes / (1024 * 1024), 2)
        }
    except (KeyError, TypeError):
        return {
            "rx_mb": 0,
            "tx_mb": 0
        }


@router.get("")
async def list_containers(
    request: Request,
    all: bool = False,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    List all containers with their status and resource usage
    
    Args:
        all: Include stopped containers
        
    Returns:
        List of containers with detailed information
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker service unavailable")
    
    try:
        containers = docker_client.containers.list(all=all)
        container_list = []
        
        for container in containers:
            # Get container info
            attrs = container.attrs
            
            # Try to get stats (only for running containers)
            resources = {
                "cpu_percent": 0,
                "memory_mb": 0,
                "memory_percent": 0,
                "network_rx_mb": 0,
                "network_tx_mb": 0
            }
            
            if container.status == "running":
                try:
                    stats = container.stats(stream=False)
                    resources["cpu_percent"] = calculate_cpu_percent(stats)
                    
                    memory_stats = calculate_memory_stats(stats)
                    resources["memory_mb"] = memory_stats["usage_mb"]
                    resources["memory_percent"] = memory_stats["percent"]
                    
                    network_stats = calculate_network_stats(stats)
                    resources["network_rx_mb"] = network_stats["rx_mb"]
                    resources["network_tx_mb"] = network_stats["tx_mb"]
                except Exception as e:
                    logger.warning(f"Failed to get stats for container {container.name}: {e}")
            
            # Extract port mappings
            ports = []
            for internal_port, external_ports in attrs["NetworkSettings"]["Ports"].items():
                if external_ports:
                    for ext_port in external_ports:
                        ports.append(f"{ext_port['HostPort']}:{internal_port}")
            
            container_list.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "status": container.status,
                "created": attrs["Created"],
                "started_at": attrs["State"].get("StartedAt"),
                "ports": ports,
                "labels": container.labels,
                "resources": resources,
                "health": attrs["State"].get("Health", {}).get("Status", "none")
            })
        
        return {"containers": container_list}
    
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list containers")


@router.post("/{container_id}/action")
async def container_action(
    request: Request,
    container_id: str,
    action: str,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Execute container actions (start, stop, restart)
    
    Args:
        container_id: Container ID or name
        action: Action to perform (start|stop|restart)
        
    Returns:
        Success message
    """
    if current_user:
        require_role(current_user, ["admin"])
    
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker service unavailable")
    
    if action not in ["start", "stop", "restart"]:
        raise HTTPException(status_code=400, detail="Invalid action. Must be start, stop, or restart")
    
    try:
        container = docker_client.containers.get(container_id)
        
        # Log the action
        logger.info(f"Executing {action} on container {container.name} by user {current_user.get('email', 'anonymous') if current_user else 'anonymous'}")
        
        # Execute action
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop(timeout=30)
        elif action == "restart":
            container.restart(timeout=30)
        
        # Get updated status
        container.reload()
        
        return {
            "success": True,
            "message": f"Container {action} successful",
            "container": {
                "id": container.short_id,
                "name": container.name,
                "status": container.status
            }
        }
    
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except APIError as e:
        logger.error(f"Docker API error: {e}")
        raise HTTPException(status_code=500, detail=f"Docker API error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to {action} container: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to {action} container")


@router.get("/{container_id}/logs")
async def get_container_logs(
    request: Request,
    container_id: str,
    lines: int = 100,
    timestamps: bool = True,
    follow: bool = False,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get container logs (last N lines)
    
    Args:
        container_id: Container ID or name
        lines: Number of lines to return
        timestamps: Include timestamps
        follow: Stream logs (returns streaming response)
        
    Returns:
        Container logs
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker service unavailable")
    
    try:
        container = docker_client.containers.get(container_id)
        
        if follow:
            # Stream logs
            async def log_generator():
                try:
                    for line in container.logs(stream=True, follow=True, timestamps=timestamps, tail=lines):
                        yield line.decode('utf-8', errors='replace')
                except Exception as e:
                    logger.error(f"Error streaming logs: {e}")
                    yield f"Error: {str(e)}\n"
            
            return StreamingResponse(
                log_generator(),
                media_type="text/plain",
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # Get fixed number of lines
            logs = container.logs(
                timestamps=timestamps,
                tail=lines
            ).decode('utf-8', errors='replace')
            
            return {
                "container_id": container.short_id,
                "container_name": container.name,
                "logs": logs,
                "lines": len(logs.splitlines())
            }
    
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except Exception as e:
        logger.error(f"Failed to get container logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get container logs")


@router.get("/{container_id}/stats")
async def get_container_stats(
    request: Request,
    container_id: str,
    stream: bool = False,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get container resource usage statistics
    
    Args:
        container_id: Container ID or name
        stream: Stream stats (returns streaming response)
        
    Returns:
        Container statistics
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker service unavailable")
    
    try:
        container = docker_client.containers.get(container_id)
        
        if container.status != "running":
            raise HTTPException(status_code=400, detail="Container is not running")
        
        if stream:
            # Stream stats
            async def stats_generator():
                try:
                    for stats in container.stats(stream=True, decode=True):
                        formatted_stats = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "cpu_percent": calculate_cpu_percent(stats),
                            "memory": calculate_memory_stats(stats),
                            "network": calculate_network_stats(stats),
                            "block_io": {
                                "read_mb": sum(item.get("value", 0) for item in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) if item.get("op") == "read") / (1024 * 1024),
                                "write_mb": sum(item.get("value", 0) for item in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) if item.get("op") == "write") / (1024 * 1024)
                            }
                        }
                        yield json.dumps(formatted_stats) + "\n"
                        await asyncio.sleep(1)  # Rate limit streaming
                except Exception as e:
                    logger.error(f"Error streaming stats: {e}")
                    yield json.dumps({"error": str(e)}) + "\n"
            
            return StreamingResponse(
                stats_generator(),
                media_type="application/x-ndjson",
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # Get single stats snapshot
            stats = container.stats(stream=False)
            
            return {
                "container_id": container.short_id,
                "container_name": container.name,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu_percent": calculate_cpu_percent(stats),
                "memory": calculate_memory_stats(stats),
                "network": calculate_network_stats(stats),
                "block_io": {
                    "read_mb": sum(item.get("value", 0) for item in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) if item.get("op") == "read") / (1024 * 1024),
                    "write_mb": sum(item.get("value", 0) for item in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) if item.get("op") == "write") / (1024 * 1024)
                }
            }
    
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except Exception as e:
        logger.error(f"Failed to get container stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get container stats")


@router.websocket("/ws/terminal/{container_id}")
async def websocket_terminal(
    websocket: WebSocket,
    container_id: str
):
    """
    WebSocket endpoint for SSH-like terminal access to container
    
    Args:
        websocket: WebSocket connection
        container_id: Container ID or name
    """
    await websocket.accept()
    
    if not docker_client:
        await websocket.send_json({
            "type": "error",
            "data": {"message": "Docker service unavailable"}
        })
        await websocket.close()
        return
    
    try:
        # Get container
        container = docker_client.containers.get(container_id)
        
        if container.status != "running":
            await websocket.send_json({
                "type": "error",
                "data": {"message": "Container is not running"}
            })
            await websocket.close()
            return
        
        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "data": {
                "container_id": container.short_id,
                "container_name": container.name
            }
        })
        
        # Start interactive shell
        exec_command = ["/bin/sh", "-c", "[ -x /bin/bash ] && /bin/bash || /bin/sh"]
        exec_id = docker_client.api.exec_create(
            container.id,
            exec_command,
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True
        )
        
        # Start exec instance
        exec_socket = docker_client.api.exec_start(
            exec_id["Id"],
            socket=True,
            tty=True
        )
        
        # Set socket to non-blocking
        exec_socket._sock.setblocking(False)
        
        # Handle bidirectional communication
        async def read_from_container():
            """Read output from container and send to websocket"""
            while True:
                try:
                    output = exec_socket.recv(1024)
                    if output:
                        await websocket.send_text(output.decode('utf-8', errors='replace'))
                    else:
                        break
                except BlockingIOError:
                    await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error reading from container: {e}")
                    break
        
        # Start reading from container
        read_task = asyncio.create_task(read_from_container())
        
        try:
            # Handle input from websocket
            while True:
                message = await websocket.receive_text()
                
                # Handle special messages
                if message.startswith('{"type":'):
                    try:
                        msg_data = json.loads(message)
                        if msg_data.get("type") == "resize":
                            # Handle terminal resize
                            rows = msg_data.get("rows", 24)
                            cols = msg_data.get("cols", 80)
                            docker_client.api.exec_resize(exec_id["Id"], height=rows, width=cols)
                            continue
                    except json.JSONDecodeError:
                        pass
                
                # Send input to container
                exec_socket.send(message.encode('utf-8'))
        
        except WebSocketDisconnect:
            logger.info(f"Terminal disconnected for container {container_id}")
        except Exception as e:
            logger.error(f"Terminal error: {e}")
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        finally:
            read_task.cancel()
            exec_socket.close()
    
    except NotFound:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Container '{container_id}' not found"}
        })
    except Exception as e:
        logger.error(f"Failed to start terminal: {e}")
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Failed to start terminal: {str(e)}"}
        })
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.get("/{container_id}/inspect")
async def inspect_container(
    request: Request,
    container_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get detailed container information
    
    Args:
        container_id: Container ID or name
        
    Returns:
        Detailed container configuration and state
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker service unavailable")
    
    try:
        container = docker_client.containers.get(container_id)
        attrs = container.attrs
        
        # Extract relevant information
        return {
            "id": attrs["Id"],
            "name": attrs["Name"].lstrip("/"),
            "created": attrs["Created"],
            "state": attrs["State"],
            "config": {
                "image": attrs["Config"]["Image"],
                "env": attrs["Config"].get("Env", []),
                "cmd": attrs["Config"].get("Cmd", []),
                "labels": attrs["Config"].get("Labels", {}),
                "working_dir": attrs["Config"].get("WorkingDir", "/")
            },
            "network": {
                "mode": list(attrs["NetworkSettings"]["Networks"].keys())[0] if attrs["NetworkSettings"]["Networks"] else "none",
                "networks": attrs["NetworkSettings"]["Networks"],
                "ports": attrs["NetworkSettings"]["Ports"]
            },
            "mounts": attrs.get("Mounts", []),
            "resources": {
                "cpu_shares": attrs["HostConfig"].get("CpuShares"),
                "memory_limit": attrs["HostConfig"].get("Memory"),
                "restart_policy": attrs["HostConfig"].get("RestartPolicy")
            }
        }
    
    except NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except Exception as e:
        logger.error(f"Failed to inspect container: {e}")
        raise HTTPException(status_code=500, detail="Failed to inspect container")