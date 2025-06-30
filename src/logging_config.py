"""
Structured logging configuration for Loki integration
"""

import logging
import json
import sys
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional


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
            
        # Add AI-specific fields
        if hasattr(record, 'correlation_id'):
            log_obj['correlation_id'] = record.correlation_id
        if hasattr(record, 'conversation_id'):
            log_obj['conversation_id'] = record.conversation_id
        if hasattr(record, 'workspace_id'):
            log_obj['workspace_id'] = record.workspace_id
        if hasattr(record, 'model'):
            log_obj['model'] = record.model
        if hasattr(record, 'tokens_used'):
            log_obj['tokens_used'] = record.tokens_used
        if hasattr(record, 'request_type'):
            log_obj['request_type'] = record.request_type
        if hasattr(record, 'session_id'):
            log_obj['session_id'] = record.session_id
        if hasattr(record, 'prompt_hash'):
            log_obj['prompt_hash'] = record.prompt_hash
            
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


class DatabaseLogger:
    """Comprehensive database operation logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_query_performance(self, operation: str, table: str, duration_ms: float, 
                            rows_affected: int = 0, **kwargs):
        """Log database query with performance metrics"""
        performance_tier = self._classify_performance(duration_ms)
        severity = "warning" if duration_ms > 1000 else "info"
        
        extra = {
            'db_operation': operation,
            'table_name': table,
            'duration_ms': duration_ms,
            'rows_affected': rows_affected,
            'performance_tier': performance_tier,
            'optimization_needed': duration_ms > 1000,
            **kwargs
        }
        
        getattr(self.logger, severity)(
            f"DB_QUERY {operation} table={table} duration={duration_ms:.1f}ms rows={rows_affected}",
            extra=extra
        )
    
    def log_connection_event(self, event_type: str, pool_stats: dict = None, **kwargs):
        """Log database connection events"""
        extra = {
            'connection_event': event_type,
            **kwargs
        }
        
        if pool_stats:
            utilization = (pool_stats.get("active", 0) / pool_stats.get("size", 1)) * 100
            extra.update({
                'pool_size': pool_stats.get("size", 0),
                'active_connections': pool_stats.get("active", 0),
                'idle_connections': pool_stats.get("idle", 0),
                'utilization_percent': utilization,
                'pressure_level': "high" if utilization > 80 else "normal"
            })
        
        severity = "warning" if event_type in ["connection_failed", "pool_exhausted"] else "info"
        getattr(self.logger, severity)(
            f"DB_CONNECTION {event_type}",
            extra=extra
        )
    
    def log_transaction_event(self, event_type: str, transaction_id: str, **kwargs):
        """Log database transaction events"""
        extra = {
            'transaction_event': event_type,
            'transaction_id': transaction_id,
            **kwargs
        }
        
        severity = "error" if event_type in ["rollback", "deadlock"] else "debug"
        getattr(self.logger, severity)(
            f"DB_TRANSACTION {event_type} tx_id={transaction_id}",
            extra=extra
        )
    
    def _classify_performance(self, duration_ms: float) -> str:
        """Classify query performance tier"""
        if duration_ms < 100:
            return "excellent"
        elif duration_ms < 500:
            return "good"
        elif duration_ms < 1000:
            return "acceptable"
        elif duration_ms < 5000:
            return "slow"
        else:
            return "critical"


class ExternalServiceLogger:
    """Comprehensive external service monitoring"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_service_call(self, service: str, endpoint: str, method: str,
                        duration_ms: float, status_code: int, **kwargs):
        """Log external service API call"""
        success = status_code < 400
        severity = "warning" if not success else "info"
        
        extra = {
            'service_name': service,
            'service_endpoint': endpoint,
            'method': method,
            'duration_ms': duration_ms,
            'status_code': status_code,
            'success': success,
            'service_health': self._assess_health(duration_ms, status_code),
            **kwargs
        }
        
        getattr(self.logger, severity)(
            f"EXTERNAL_SERVICE {service.upper()} {method} {endpoint} status={status_code} duration={duration_ms:.1f}ms",
            extra=extra
        )
    
    def log_rate_limit_event(self, service: str, remaining: int, total: int, reset_time: str = None, **kwargs):
        """Log rate limiting status for external services"""
        utilization = ((total - remaining) / total * 100) if total > 0 else 0
        severity = "warning" if utilization > 80 else "info"
        
        extra = {
            'service_name': service,
            'rate_limit_remaining': remaining,
            'rate_limit_total': total,
            'rate_limit_utilization': utilization,
            'rate_limit_reset': reset_time,
            'rate_limit_pressure': "high" if utilization > 80 else "normal",
            **kwargs
        }
        
        getattr(self.logger, severity)(
            f"RATE_LIMIT {service.upper()} remaining={remaining}/{total} ({utilization:.1f}%)",
            extra=extra
        )
    
    def log_circuit_breaker_event(self, service: str, state: str, failure_count: int, **kwargs):
        """Log circuit breaker state changes"""
        extra = {
            'service_name': service,
            'circuit_state': state,
            'failure_count': failure_count,
            'circuit_event': f"state_change_to_{state}",
            **kwargs
        }
        
        severity = "error" if state == "open" else "warning" if state == "half_open" else "info"
        getattr(self.logger, severity)(
            f"CIRCUIT_BREAKER {service.upper()} state={state} failures={failure_count}",
            extra=extra
        )
    
    def _assess_health(self, duration_ms: float, status_code: int) -> str:
        """Assess service health based on response"""
        if status_code >= 500:
            return "unhealthy"
        elif status_code >= 400:
            return "degraded"
        elif duration_ms > 5000:
            return "slow"
        elif duration_ms > 2000:
            return "acceptable"
        else:
            return "healthy"


class SecurityLogger:
    """Security and admin action logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_admin_action(self, action: str, target: str, impact_level: str, 
                        client_ip: str = None, **kwargs):
        """Log administrative actions"""
        extra = {
            'admin_action': action,
            'target_resource': target,
            'impact_level': impact_level,
            'client_ip': client_ip,
            'requires_audit': True,
            'security_event': "admin_action",
            **kwargs
        }
        
        self.logger.warning(
            f"ADMIN_ACTION {action} target={target} impact={impact_level}",
            extra=extra
        )
    
    def log_rate_limit_violation(self, endpoint: str, client_ip: str, current_rate: int,
                                limit: int, window: str, **kwargs):
        """Log rate limiting violations"""
        violation_severity = self._assess_violation_severity(current_rate, limit)
        
        extra = {
            'security_event': 'rate_limit_violation',
            'endpoint': endpoint,
            'client_ip': client_ip,
            'current_rate': current_rate,
            'rate_limit': limit,
            'time_window': window,
            'violation_severity': violation_severity,
            'potential_abuse': current_rate > (limit * 1.5),
            **kwargs
        }
        
        severity = "error" if violation_severity == "severe" else "warning"
        getattr(self.logger, severity)(
            f"RATE_LIMIT_VIOLATION endpoint={endpoint} ip={client_ip} rate={current_rate}/{limit}",
            extra=extra
        )
    
    def log_sensitive_operation(self, operation: str, resource: str, client_ip: str = None, **kwargs):
        """Log access to sensitive operations or data"""
        extra = {
            'security_event': 'sensitive_operation',
            'operation': operation,
            'resource': resource,
            'client_ip': client_ip,
            'requires_review': True,
            **kwargs
        }
        
        self.logger.warning(
            f"SENSITIVE_OPERATION {operation} resource={resource}",
            extra=extra
        )
    
    def log_configuration_change(self, key: str, old_value: str, new_value: str,
                                client_ip: str = None, **kwargs):
        """Log configuration changes with security context"""
        # Mask sensitive values
        masked_old = self._mask_sensitive_value(key, old_value)
        masked_new = self._mask_sensitive_value(key, new_value)
        
        extra = {
            'security_event': 'configuration_change',
            'config_key': key,
            'old_value': masked_old,
            'new_value': masked_new,
            'client_ip': client_ip,
            'sensitive_config': self._is_sensitive_key(key),
            **kwargs
        }
        
        severity = "warning" if self._is_sensitive_key(key) else "info"
        getattr(self.logger, severity)(
            f"CONFIG_CHANGE key={key} old={masked_old} new={masked_new}",
            extra=extra
        )
    
    def _assess_violation_severity(self, current: int, limit: int) -> str:
        """Assess rate limit violation severity"""
        ratio = current / limit if limit > 0 else float('inf')
        if ratio > 5:
            return "severe"
        elif ratio > 2:
            return "moderate"
        else:
            return "minor"
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if configuration key is sensitive"""
        sensitive_patterns = ['password', 'secret', 'key', 'token', 'credential', 'url']
        return any(pattern in key.lower() for pattern in sensitive_patterns)
    
    def _mask_sensitive_value(self, key: str, value: str) -> str:
        """Mask sensitive configuration values"""
        if self._is_sensitive_key(key) and value:
            if len(value) <= 4:
                return "***"
            return value[:2] + "***" + value[-2:]
        return value


class BusinessMetricsLogger:
    """Business intelligence and operational metrics logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_content_operation(self, operation: str, content_id: str, 
                            content_type: str, **kwargs):
        """Log content management operations"""
        extra = {
            'business_event': 'content_operation',
            'content_operation': operation,
            'content_id': content_id,
            'content_type': content_type,
            **kwargs
        }
        
        self.logger.info(
            f"CONTENT_OPERATION {operation} id={content_id} type={content_type}",
            extra=extra
        )
    
    def log_user_behavior(self, behavior_type: str, user_session: str, **kwargs):
        """Log user behavior for analytics"""
        extra = {
            'business_event': 'user_behavior',
            'behavior_type': behavior_type,
            'user_session': user_session,
            **kwargs
        }
        
        self.logger.info(
            f"USER_BEHAVIOR {behavior_type} session={user_session}",
            extra=extra
        )
    
    def log_system_capacity(self, metric_type: str, current_value: float, 
                           threshold: float, **kwargs):
        """Log system capacity and scaling metrics"""
        utilization = (current_value / threshold * 100) if threshold > 0 else 0
        severity = "warning" if utilization > 80 else "info"
        
        extra = {
            'business_event': 'system_capacity',
            'capacity_metric': metric_type,
            'current_value': current_value,
            'threshold': threshold,
            'utilization_percent': utilization,
            'scaling_needed': utilization > 80,
            **kwargs
        }
        
        getattr(self.logger, severity)(
            f"SYSTEM_CAPACITY {metric_type} usage={current_value}/{threshold} ({utilization:.1f}%)",
            extra=extra
        )


class AIOperationLogger:
    """Logger for AI-specific operations with comprehensive tracking"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_ai_request(self, 
                      correlation_id: str,
                      conversation_id: str,
                      model: str,
                      prompt: str,
                      tokens: int,
                      duration: float,
                      workspace_id: str,
                      user_id: Optional[str] = None,
                      session_id: Optional[str] = None,
                      success: bool = True,
                      error: Optional[str] = None,
                      **kwargs):
        """Log AI operation with full context for troubleshooting"""
        # Hash the prompt for privacy while maintaining traceability
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        extra = {
            'correlation_id': correlation_id,
            'conversation_id': conversation_id,
            'model': model,
            'prompt_hash': prompt_hash,
            'prompt_length': len(prompt),
            'tokens_used': tokens,
            'duration': duration,
            'workspace_id': workspace_id,
            'user_id': user_id,
            'session_id': session_id,
            'success': success,
            'error': error,
            'request_type': 'ai_completion',
            'ai_event': 'request',
            **kwargs
        }
        
        severity = "error" if not success else "info"
        message = f"AI_REQUEST model={model} tokens={tokens} duration={duration:.3f}s"
        if error:
            message += f" error={error}"
            
        getattr(self.logger, severity)(message, extra=extra)
    
    def log_ai_response(self,
                       correlation_id: str,
                       conversation_id: str,
                       response_tokens: int,
                       response_hash: Optional[str] = None,
                       confidence_score: Optional[float] = None,
                       **kwargs):
        """Log AI response details"""
        extra = {
            'correlation_id': correlation_id,
            'conversation_id': conversation_id,
            'response_tokens': response_tokens,
            'response_hash': response_hash,
            'confidence_score': confidence_score,
            'ai_event': 'response',
            **kwargs
        }
        
        self.logger.info(
            f"AI_RESPONSE tokens={response_tokens} confidence={confidence_score}",
            extra=extra
        )
    
    def log_token_usage(self,
                       workspace_id: str,
                       model: str,
                       input_tokens: int,
                       output_tokens: int,
                       total_tokens: int,
                       estimated_cost: Optional[float] = None,
                       **kwargs):
        """Log token usage for cost tracking and monitoring"""
        extra = {
            'workspace_id': workspace_id,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'estimated_cost': estimated_cost,
            'ai_event': 'token_usage',
            **kwargs
        }
        
        self.logger.info(
            f"TOKEN_USAGE model={model} total={total_tokens} cost=${estimated_cost:.4f}",
            extra=extra
        )
    
    def log_model_performance(self,
                            model: str,
                            latency_ms: float,
                            throughput_tps: Optional[float] = None,
                            queue_depth: Optional[int] = None,
                            **kwargs):
        """Log model performance metrics"""
        performance_tier = self._classify_latency(latency_ms)
        severity = "warning" if latency_ms > 5000 else "info"
        
        extra = {
            'model': model,
            'latency_ms': latency_ms,
            'throughput_tps': throughput_tps,
            'queue_depth': queue_depth,
            'performance_tier': performance_tier,
            'ai_event': 'model_performance',
            **kwargs
        }
        
        getattr(self.logger, severity)(
            f"MODEL_PERFORMANCE model={model} latency={latency_ms:.1f}ms tier={performance_tier}",
            extra=extra
        )
    
    def log_context_overflow(self,
                           model: str,
                           context_size: int,
                           max_context: int,
                           truncation_strategy: str,
                           **kwargs):
        """Log context window overflow events"""
        overflow_percent = ((context_size - max_context) / max_context * 100)
        
        extra = {
            'model': model,
            'context_size': context_size,
            'max_context': max_context,
            'overflow_percent': overflow_percent,
            'truncation_strategy': truncation_strategy,
            'ai_event': 'context_overflow',
            **kwargs
        }
        
        self.logger.warning(
            f"CONTEXT_OVERFLOW model={model} size={context_size}/{max_context} overflow={overflow_percent:.1f}%",
            extra=extra
        )
    
    def log_conversation_summary(self,
                               conversation_id: str,
                               workspace_id: str,
                               message_count: int,
                               total_tokens: int,
                               duration_seconds: float,
                               model_switches: int = 0,
                               error_count: int = 0,
                               **kwargs):
        """Log conversation summary for analysis"""
        avg_response_time = duration_seconds / message_count if message_count > 0 else 0
        
        extra = {
            'conversation_id': conversation_id,
            'workspace_id': workspace_id,
            'message_count': message_count,
            'total_tokens': total_tokens,
            'duration_seconds': duration_seconds,
            'avg_response_time': avg_response_time,
            'model_switches': model_switches,
            'error_count': error_count,
            'ai_event': 'conversation_summary',
            **kwargs
        }
        
        self.logger.info(
            f"CONVERSATION_SUMMARY id={conversation_id} messages={message_count} tokens={total_tokens} errors={error_count}",
            extra=extra
        )
    
    def log_prompt_injection_attempt(self,
                                   correlation_id: str,
                                   pattern_detected: str,
                                   risk_score: float,
                                   blocked: bool,
                                   **kwargs):
        """Log potential prompt injection attempts"""
        extra = {
            'correlation_id': correlation_id,
            'security_event': 'prompt_injection_attempt',
            'pattern_detected': pattern_detected,
            'risk_score': risk_score,
            'blocked': blocked,
            'ai_event': 'security',
            **kwargs
        }
        
        self.logger.error(
            f"PROMPT_INJECTION pattern={pattern_detected} risk={risk_score:.2f} blocked={blocked}",
            extra=extra
        )
    
    def _classify_latency(self, latency_ms: float) -> str:
        """Classify AI response latency"""
        if latency_ms < 500:
            return "excellent"
        elif latency_ms < 1000:
            return "good"
        elif latency_ms < 3000:
            return "acceptable"
        elif latency_ms < 5000:
            return "slow"
        else:
            return "critical"