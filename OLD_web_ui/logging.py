"""Structured logging setup for Web UI Service."""

import logging
import sys
import json
import uuid

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        # Attach a correlation ID if not present
        if not hasattr(record, "correlation_id"):
            record.correlation_id = str(uuid.uuid4())
        return True

def setup_logging():
    """Configure structured logging for the Web UI Service."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
    root_logger.addFilter(CorrelationIdFilter())
    # TODO: IMPLEMENTATION ENGINEER - Add correlation ID, JSON formatting, and external log sinks as needed

setup_logging()
import subprocess

class DBWriteAlertHandler(logging.Handler):
    """
    Custom log handler to trigger alert script on DB write failures.
    """
    def emit(self, record):
        msg = self.format(record)
        if (
            record.levelno >= logging.ERROR and (
                "Failed to update configuration" in msg or
                "Failed to write audit log" in msg or
                "Failed to perform bulk configuration update" in msg or
                "CRITICAL: Failed to write bulk audit log" in msg
            )
        ):
            try:
                subprocess.Popen(
                    ["bash", "ops/scripts/db_write_alert.sh", msg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass  # Avoid recursion on logging failure

# Attach handler to root logger if not already present
if not any(isinstance(h, DBWriteAlertHandler) for h in logging.getLogger().handlers):
    logging.getLogger().addHandler(DBWriteAlertHandler())