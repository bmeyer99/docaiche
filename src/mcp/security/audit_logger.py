"""
Audit Logger Implementation
==========================

Secure audit logging for MCP security events with persistence,
rotation, and compliance features.
"""

import asyncio
import json
import logging
import hashlib
import hmac
import time
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import aiofiles
from collections import deque
import threading

from ..exceptions import SecurityError

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_LOGOUT = "auth_logout"
    TOKEN_ISSUED = "token_issued"
    TOKEN_REVOKED = "token_revoked"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    
    # Security events
    THREAT_DETECTED = "threat_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    SECURITY_VIOLATION = "security_violation"
    
    # Data events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    ERROR_OCCURRED = "error_occurred"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    client_id: Optional[str]
    session_id: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    result: str  # success, failure
    details: Dict[str, Any]
    correlation_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return json.dumps(data, sort_keys=True)


class AuditLogger:
    """
    Secure audit logger with persistence and compliance features.
    
    Features:
    - Tamper-proof logging with HMAC signatures
    - Automatic log rotation and archival
    - Async write buffering for performance
    - Search and query capabilities
    - Compliance report generation
    """
    
    def __init__(
        self,
        log_dir: str = "logs/audit",
        max_file_size: int = 104857600,  # 100MB
        retention_days: int = 90,
        hmac_key: Optional[bytes] = None,
        buffer_size: int = 1000
    ):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self.hmac_key = hmac_key or os.urandom(32)
        self.buffer_size = buffer_size
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file
        self.current_log_file = self._get_current_log_file()
        
        # Write buffer
        self._buffer: deque = deque(maxlen=buffer_size)
        self._buffer_lock = threading.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_severity": {}
        }
        
        logger.info(f"Audit logger initialized: {self.log_dir}")
    
    async def initialize(self) -> None:
        """Initialize audit logger and start background tasks."""
        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        # Clean old logs
        await self._cleanup_old_logs()
        
        logger.info("Audit logger background tasks started")
    
    async def close(self) -> None:
        """Close audit logger and flush remaining events."""
        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_buffer()
        
        logger.info("Audit logger closed")
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        client_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Log a security event.
        
        Returns:
            Event ID for tracking
        """
        # Generate event ID
        event_id = self._generate_event_id()
        
        # Create event
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow(),
            event_type=AuditEventType(event_type) if isinstance(event_type, str) else event_type,
            severity=AuditSeverity(severity) if isinstance(severity, str) else severity,
            client_id=client_id,
            session_id=session_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Add to buffer
        with self._buffer_lock:
            self._buffer.append(event)
        
        # Update statistics
        self.stats["total_events"] += 1
        event_type_str = event.event_type.value
        self.stats["events_by_type"][event_type_str] = \
            self.stats["events_by_type"].get(event_type_str, 0) + 1
        severity_str = event.severity.value
        self.stats["events_by_severity"][severity_str] = \
            self.stats["events_by_severity"].get(severity_str, 0) + 1
        
        # Log critical events immediately
        if event.severity == AuditSeverity.CRITICAL:
            await self._write_event(event)
        
        return event_id
    
    async def log_auth_event(
        self,
        success: bool,
        client_id: str,
        method: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Log authentication event."""
        return await self.log_security_event(
            event_type=AuditEventType.AUTH_SUCCESS if success else AuditEventType.AUTH_FAILURE,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            client_id=client_id,
            action=f"auth_{method}",
            result="success" if success else "failure",
            details=details,
            **kwargs
        )
    
    async def log_access_event(
        self,
        granted: bool,
        client_id: str,
        resource: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Log access control event."""
        return await self.log_security_event(
            event_type=AuditEventType.ACCESS_GRANTED if granted else AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            client_id=client_id,
            resource=resource,
            action=action,
            result="granted" if granted else "denied",
            details=details,
            **kwargs
        )
    
    async def log_threat_event(
        self,
        threat_type: str,
        client_id: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Log threat detection event."""
        return await self.log_security_event(
            event_type=AuditEventType.THREAT_DETECTED,
            severity=severity,
            client_id=client_id,
            action=f"threat_{threat_type}",
            result="detected",
            details=details,
            **kwargs
        )
    
    async def search_events(
        self,
        event_type: Optional[str] = None,
        client_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Search audit events.
        
        Returns:
            List of matching events
        """
        events = []
        
        # Search in buffer first
        with self._buffer_lock:
            for event in self._buffer:
                if self._matches_criteria(
                    event, event_type, client_id, start_time, end_time, severity
                ):
                    events.append(event)
        
        # Search in log files
        log_files = sorted(self.log_dir.glob("audit_*.log"), reverse=True)
        
        for log_file in log_files:
            if len(events) >= limit:
                break
                
            # Check file date range
            file_date = self._get_file_date(log_file)
            if start_time and file_date < start_time.date():
                continue
            if end_time and file_date > end_time.date():
                continue
            
            # Read and search file
            async with aiofiles.open(log_file, 'r') as f:
                async for line in f:
                    if len(events) >= limit:
                        break
                    
                    try:
                        # Parse and verify event
                        event_data, signature = line.strip().split('|', 1)
                        
                        # Verify signature
                        if not self._verify_signature(event_data, signature):
                            logger.warning(f"Invalid signature in {log_file}: {line[:50]}")
                            continue
                        
                        # Parse event
                        data = json.loads(event_data)
                        event = self._parse_event(data)
                        
                        if self._matches_criteria(
                            event, event_type, client_id, start_time, end_time, severity
                        ):
                            events.append(event)
                            
                    except Exception as e:
                        logger.error(f"Error parsing audit log line: {e}")
        
        return events[:limit]
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "security"
    ) -> Dict[str, Any]:
        """Generate compliance report for date range."""
        events = await self.search_events(
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_events": len(events),
                "auth_failures": 0,
                "access_denials": 0,
                "threats_detected": 0,
                "critical_events": 0
            },
            "details": {
                "events_by_type": {},
                "events_by_client": {},
                "events_by_day": {}
            }
        }
        
        # Analyze events
        for event in events:
            # Update summary
            if event.event_type == AuditEventType.AUTH_FAILURE:
                report["summary"]["auth_failures"] += 1
            elif event.event_type == AuditEventType.ACCESS_DENIED:
                report["summary"]["access_denials"] += 1
            elif event.event_type == AuditEventType.THREAT_DETECTED:
                report["summary"]["threats_detected"] += 1
            if event.severity == AuditSeverity.CRITICAL:
                report["summary"]["critical_events"] += 1
            
            # Events by type
            event_type = event.event_type.value
            report["details"]["events_by_type"][event_type] = \
                report["details"]["events_by_type"].get(event_type, 0) + 1
            
            # Events by client
            if event.client_id:
                report["details"]["events_by_client"][event.client_id] = \
                    report["details"]["events_by_client"].get(event.client_id, 0) + 1
            
            # Events by day
            day = event.timestamp.date().isoformat()
            report["details"]["events_by_day"][day] = \
                report["details"]["events_by_day"].get(day, 0) + 1
        
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit logger statistics."""
        return {
            **self.stats,
            "buffer_size": len(self._buffer),
            "log_files": len(list(self.log_dir.glob("audit_*.log"))),
            "log_dir_size_mb": sum(
                f.stat().st_size for f in self.log_dir.glob("audit_*.log")
            ) / 1048576
        }
    
    # Private methods
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        timestamp = int(time.time() * 1000000)
        random_bytes = os.urandom(8)
        return f"evt_{timestamp}_{random_bytes.hex()}"
    
    def _get_current_log_file(self) -> Path:
        """Get current log file path."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return self.log_dir / f"audit_{date_str}.log"
    
    def _get_file_date(self, log_file: Path) -> datetime:
        """Extract date from log file name."""
        try:
            date_str = log_file.stem.split('_')[1]
            return datetime.strptime(date_str, "%Y%m%d").date()
        except:
            return datetime.utcnow().date()
    
    def _sign_event(self, event_data: str) -> str:
        """Generate HMAC signature for event."""
        return hmac.new(
            self.hmac_key,
            event_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_signature(self, event_data: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign_event(event_data)
        return hmac.compare_digest(expected, signature)
    
    async def _write_event(self, event: AuditEvent) -> None:
        """Write single event to log file."""
        # Check file rotation
        await self._rotate_log_if_needed()
        
        # Prepare log line
        event_json = event.to_json()
        signature = self._sign_event(event_json)
        log_line = f"{event_json}|{signature}\n"
        
        # Write to file
        async with aiofiles.open(self.current_log_file, 'a') as f:
            await f.write(log_line)
    
    async def _flush_buffer(self) -> None:
        """Flush event buffer to disk."""
        events_to_write = []
        
        with self._buffer_lock:
            while self._buffer:
                events_to_write.append(self._buffer.popleft())
        
        if events_to_write:
            # Check file rotation
            await self._rotate_log_if_needed()
            
            # Write all events
            lines = []
            for event in events_to_write:
                event_json = event.to_json()
                signature = self._sign_event(event_json)
                lines.append(f"{event_json}|{signature}\n")
            
            async with aiofiles.open(self.current_log_file, 'a') as f:
                await f.writelines(lines)
    
    async def _flush_loop(self) -> None:
        """Background task to flush buffer periodically."""
        while True:
            try:
                await asyncio.sleep(5)  # Flush every 5 seconds
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}", exc_info=True)
    
    async def _rotate_log_if_needed(self) -> None:
        """Rotate log file if it exceeds size limit."""
        if not self.current_log_file.exists():
            return
        
        file_size = self.current_log_file.stat().st_size
        if file_size >= self.max_file_size:
            # Rotate file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated_file = self.log_dir / f"audit_{timestamp}_rotated.log"
            self.current_log_file.rename(rotated_file)
            
            # Update current file
            self.current_log_file = self._get_current_log_file()
            
            logger.info(f"Rotated audit log to {rotated_file}")
    
    async def _cleanup_old_logs(self) -> None:
        """Clean up old log files."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        for log_file in self.log_dir.glob("audit_*.log"):
            try:
                file_date = self._get_file_date(log_file)
                if file_date < cutoff_date.date():
                    log_file.unlink()
                    logger.info(f"Deleted old audit log: {log_file}")
            except Exception as e:
                logger.error(f"Error cleaning up {log_file}: {e}")
    
    def _matches_criteria(
        self,
        event: AuditEvent,
        event_type: Optional[str],
        client_id: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        severity: Optional[str]
    ) -> bool:
        """Check if event matches search criteria."""
        if event_type and event.event_type.value != event_type:
            return False
        if client_id and event.client_id != client_id:
            return False
        if start_time and event.timestamp < start_time:
            return False
        if end_time and event.timestamp > end_time:
            return False
        if severity and event.severity.value != severity:
            return False
        return True
    
    def _parse_event(self, data: Dict[str, Any]) -> AuditEvent:
        """Parse event from JSON data."""
        return AuditEvent(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            severity=AuditSeverity(data["severity"]),
            client_id=data.get("client_id"),
            session_id=data.get("session_id"),
            resource=data.get("resource"),
            action=data.get("action"),
            result=data["result"],
            details=data.get("details", {}),
            correlation_id=data.get("correlation_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent")
        )