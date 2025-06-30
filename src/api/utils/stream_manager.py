"""
Stream Manager for real-time log streaming via WebSocket.

This module handles WebSocket connections, real-time log filtering,
and dynamic stream management for AI log monitoring.
"""

import asyncio
import logging
import json
from typing import Dict, Set, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import weakref

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class StreamFilter:
    """Filter configuration for a log stream."""
    services: Optional[List[str]] = None
    severity_threshold: str = "info"
    pattern_alerts: Optional[List[str]] = None
    include_metrics: bool = True
    correlation_id: Optional[str] = None
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = None
    
    def matches(self, log_entry: Dict[str, Any]) -> bool:
        """Check if a log entry matches this filter."""
        # Service filter
        if self.services and log_entry.get("service") not in self.services:
            return False
            
        # Severity filter
        severity_levels = ["debug", "info", "warn", "error", "fatal"]
        if log_entry.get("level", "info") not in severity_levels:
            return True  # Unknown level, include it
            
        threshold_index = severity_levels.index(self.severity_threshold)
        log_level_index = severity_levels.index(log_entry.get("level", "info"))
        
        if log_level_index < threshold_index:
            return False
            
        # Correlation filters
        if self.correlation_id and log_entry.get("correlation_id") != self.correlation_id:
            return False
            
        if self.conversation_id and log_entry.get("conversation_id") != self.conversation_id:
            return False
            
        if self.workspace_id and log_entry.get("workspace_id") != self.workspace_id:
            return False
            
        return True


@dataclass
class StreamConnection:
    """Represents an active WebSocket connection."""
    websocket: WebSocket
    filter: StreamFilter
    connection_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    messages_sent: int = 0
    errors: int = 0
    pattern_detector: Optional[Any] = None  # PatternDetector instance
    
    async def send_log(self, log_entry: Dict[str, Any]) -> bool:
        """Send a log entry to this connection."""
        try:
            if self.filter.matches(log_entry):
                # Check for pattern alerts
                alert = None
                if self.filter.pattern_alerts and self.pattern_detector:
                    for pattern in self.filter.pattern_alerts:
                        if pattern.lower() in log_entry.get("message", "").lower():
                            alert = {
                                "pattern": pattern,
                                "severity": "high",
                                "message": f"Pattern '{pattern}' detected"
                            }
                            break
                
                message = {
                    "type": "log",
                    "data": log_entry,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if alert:
                    message["alert"] = alert
                    
                await self.websocket.send_json(message)
                self.messages_sent += 1
                return True
                
        except Exception as e:
            logger.error(f"Error sending log to connection {self.connection_id}: {e}")
            self.errors += 1
            
        return False
    
    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics update to this connection."""
        if not self.filter.include_metrics:
            return False
            
        try:
            message = {
                "type": "metrics",
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket.send_json(message)
            return True
            
        except Exception as e:
            logger.error(f"Error sending metrics to connection {self.connection_id}: {e}")
            self.errors += 1
            
        return False
    
    async def ping(self) -> bool:
        """Send a ping message to check connection health."""
        try:
            await self.websocket.send_json({
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            })
            self.last_ping = datetime.utcnow()
            return True
        except:
            return False


class StreamManager:
    """
    Manages WebSocket connections for real-time log streaming.
    
    Features:
    - Connection lifecycle management
    - Dynamic filter updates
    - Pattern-based alerts
    - Metrics streaming
    - Connection health monitoring
    """
    
    def __init__(self, pattern_detector=None):
        """Initialize the stream manager."""
        self.connections: Dict[str, StreamConnection] = {}
        self.pattern_detector = pattern_detector
        self._connection_counter = 0
        self._running = False
        self._tasks: Set[asyncio.Task] = set()
        self._metrics_cache = {}
        self._log_buffer = asyncio.Queue(maxsize=10000)
        
        logger.info("StreamManager initialized")
    
    async def start(self):
        """Start the stream manager background tasks."""
        if self._running:
            return
            
        self._running = True
        
        # Start background tasks
        self._tasks.add(asyncio.create_task(self._health_check_loop()))
        self._tasks.add(asyncio.create_task(self._metrics_update_loop()))
        self._tasks.add(asyncio.create_task(self._log_distribution_loop()))
        
        logger.info("StreamManager started")
    
    async def stop(self):
        """Stop the stream manager and close all connections."""
        self._running = False
        
        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self.remove_connection(conn_id)
            
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
            
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("StreamManager stopped")
    
    async def add_connection(self, 
                           websocket: WebSocket, 
                           filter_config: Dict[str, Any]) -> str:
        """
        Add a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            filter_config: Filter configuration
            
        Returns:
            Connection ID
        """
        self._connection_counter += 1
        conn_id = f"stream_{self._connection_counter}_{datetime.utcnow().timestamp()}"
        
        # Create filter from config
        stream_filter = StreamFilter(
            services=filter_config.get("services"),
            severity_threshold=filter_config.get("severity_threshold", "info"),
            pattern_alerts=filter_config.get("pattern_alerts"),
            include_metrics=filter_config.get("include_metrics", True),
            correlation_id=filter_config.get("correlation_id"),
            conversation_id=filter_config.get("conversation_id"),
            workspace_id=filter_config.get("workspace_id")
        )
        
        # Create connection
        connection = StreamConnection(
            websocket=websocket,
            filter=stream_filter,
            connection_id=conn_id,
            pattern_detector=self.pattern_detector
        )
        
        self.connections[conn_id] = connection
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "data": {
                "connection_id": conn_id,
                "filter": filter_config,
                "server_time": datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"Added connection {conn_id} with filter: {filter_config}")
        
        return conn_id
    
    async def remove_connection(self, connection_id: str):
        """Remove a connection."""
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            
            try:
                await conn.websocket.close()
            except:
                pass
                
            del self.connections[connection_id]
            logger.info(f"Removed connection {connection_id}")
    
    async def update_filter(self, 
                          connection_id: str, 
                          filter_config: Dict[str, Any]) -> bool:
        """Update filter for a connection."""
        if connection_id not in self.connections:
            return False
            
        conn = self.connections[connection_id]
        
        # Update filter
        conn.filter = StreamFilter(
            services=filter_config.get("services", conn.filter.services),
            severity_threshold=filter_config.get("severity_threshold", conn.filter.severity_threshold),
            pattern_alerts=filter_config.get("pattern_alerts", conn.filter.pattern_alerts),
            include_metrics=filter_config.get("include_metrics", conn.filter.include_metrics),
            correlation_id=filter_config.get("correlation_id", conn.filter.correlation_id),
            conversation_id=filter_config.get("conversation_id", conn.filter.conversation_id),
            workspace_id=filter_config.get("workspace_id", conn.filter.workspace_id)
        )
        
        # Send confirmation
        try:
            await conn.websocket.send_json({
                "type": "filter_updated",
                "data": filter_config,
                "timestamp": datetime.utcnow().isoformat()
            })
            return True
        except:
            return False
    
    async def broadcast_log(self, log_entry: Dict[str, Any]):
        """Broadcast a log entry to all matching connections."""
        if not self._running:
            return
            
        # Add to buffer for async distribution
        try:
            self._log_buffer.put_nowait(log_entry)
        except asyncio.QueueFull:
            # Drop oldest log if buffer is full
            try:
                self._log_buffer.get_nowait()
                self._log_buffer.put_nowait(log_entry)
            except:
                pass
    
    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics to all connections that want them."""
        self._metrics_cache = metrics
        
        # Send to all connections with metrics enabled
        tasks = []
        for conn in self.connections.values():
            if conn.filter.include_metrics:
                tasks.append(conn.send_metrics(metrics))
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _health_check_loop(self):
        """Periodically check connection health."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check each connection
                dead_connections = []
                
                for conn_id, conn in list(self.connections.items()):
                    # Check if connection is stale
                    if (datetime.utcnow() - conn.last_ping).total_seconds() > 120:
                        if not await conn.ping():
                            dead_connections.append(conn_id)
                            
                    # Check error rate
                    if conn.errors > 10 and conn.messages_sent > 0:
                        error_rate = conn.errors / (conn.messages_sent + conn.errors)
                        if error_rate > 0.5:
                            logger.warning(f"High error rate for connection {conn_id}: {error_rate:.1%}")
                            dead_connections.append(conn_id)
                
                # Remove dead connections
                for conn_id in dead_connections:
                    await self.remove_connection(conn_id)
                    
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _metrics_update_loop(self):
        """Periodically send metrics updates."""
        while self._running:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                # Calculate connection metrics
                metrics = {
                    "active_connections": len(self.connections),
                    "total_messages_sent": sum(c.messages_sent for c in self.connections.values()),
                    "total_errors": sum(c.errors for c in self.connections.values()),
                    "buffer_size": self._log_buffer.qsize(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Broadcast to connections
                await self.broadcast_metrics(metrics)
                
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
    
    async def _log_distribution_loop(self):
        """Distribute logs from buffer to connections."""
        while self._running:
            try:
                # Get log from buffer (with timeout to allow graceful shutdown)
                try:
                    log_entry = await asyncio.wait_for(
                        self._log_buffer.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Send to all matching connections
                tasks = []
                for conn in self.connections.values():
                    tasks.append(conn.send_log(log_entry))
                    
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            except Exception as e:
                logger.error(f"Error in log distribution loop: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        if not self.connections:
            return {
                "total_connections": 0,
                "connections": []
            }
            
        connection_stats = []
        for conn in self.connections.values():
            uptime = (datetime.utcnow() - conn.connected_at).total_seconds()
            
            connection_stats.append({
                "connection_id": conn.connection_id,
                "connected_at": conn.connected_at.isoformat(),
                "uptime_seconds": uptime,
                "messages_sent": conn.messages_sent,
                "errors": conn.errors,
                "error_rate": conn.errors / (conn.messages_sent + conn.errors) if conn.messages_sent + conn.errors > 0 else 0,
                "filter": {
                    "services": conn.filter.services,
                    "severity_threshold": conn.filter.severity_threshold,
                    "has_pattern_alerts": bool(conn.filter.pattern_alerts),
                    "includes_metrics": conn.filter.include_metrics
                }
            })
        
        return {
            "total_connections": len(self.connections),
            "connections": connection_stats,
            "buffer_size": self._log_buffer.qsize(),
            "is_running": self._running
        }


# Global stream manager instance
stream_manager = StreamManager()