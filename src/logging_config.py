"""
Structured logging configuration for Loki integration
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging to Loki"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for Loki ingestion"""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'method'):
            log_obj['method'] = record.method
        if hasattr(record, 'path'):
            log_obj['path'] = record.path
        if hasattr(record, 'status_code'):
            log_obj['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_obj['duration'] = record.duration
        if hasattr(record, 'user_id'):
            log_obj['user_id'] = record.user_id
        if hasattr(record, 'search_query'):
            log_obj['search_query'] = record.search_query
        if hasattr(record, 'cache_hit'):
            log_obj['cache_hit'] = record.cache_hit
            
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)


def setup_structured_logging(level: str = "INFO"):
    """Configure structured logging for the application"""
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce noise
    
    return root_logger


class MetricsLogger:
    """Helper class for logging metrics that can be extracted by Loki"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_api_request(self, request_id: str, method: str, path: str, 
                       status_code: int, duration: float, **kwargs):
        """Log API request with metrics"""
        extra = {
            'request_id': request_id,
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration': duration,
            **kwargs
        }
        self.logger.info(
            f"API_REQUEST method={method} path={path} status={status_code} duration={duration:.3f}s",
            extra=extra
        )
        
    def log_search_query(self, query: str, result_count: int, cache_hit: bool, 
                        duration: float, **kwargs):
        """Log search query with metrics"""
        extra = {
            'search_query': query,
            'result_count': result_count,
            'cache_hit': cache_hit,
            'duration': duration,
            **kwargs
        }
        self.logger.info(
            f"SEARCH_QUERY query=\"{query}\" results={result_count} cache_hit={cache_hit} duration={duration:.3f}s",
            extra=extra
        )
        
    def log_error(self, error_type: str, error_message: str, **kwargs):
        """Log error with context"""
        extra = {
            'error_type': error_type,
            **kwargs
        }
        self.logger.error(f"ERROR {error_type}: {error_message}", extra=extra)
        
    def log_cache_operation(self, operation: str, key: str, hit: bool, **kwargs):
        """Log cache operation"""
        extra = {
            'cache_operation': operation,
            'cache_key': key,
            'cache_hit': hit,
            **kwargs
        }
        self.logger.info(
            f"CACHE_{operation.upper()} key={key} hit={hit}",
            extra=extra
        )