"""
Pydantic models for AI Logs API.

This module defines the request and response models for the AI logging system.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class QueryMode(str, Enum):
    """Query modes for AI-optimized log retrieval"""
    TROUBLESHOOT = "troubleshoot"
    PERFORMANCE = "performance"
    ERRORS = "errors"
    AUDIT = "audit"
    CONVERSATION = "conversation"


class AggregationType(str, Enum):
    """Aggregation types for log results"""
    NONE = "none"
    BY_SERVICE = "by_service"
    BY_ERROR = "by_error"
    BY_PATTERN = "by_pattern"


class ResponseFormat(str, Enum):
    """Response format options"""
    STRUCTURED = "structured"
    NARRATIVE = "narrative"
    TIMELINE = "timeline"


class VerbosityLevel(str, Enum):
    """Verbosity levels for responses"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"


class SeverityLevel(str, Enum):
    """Log severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class ExportFormat(str, Enum):
    """Export format options"""
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    PARQUET = "parquet"
    MARKDOWN = "markdown"


class AILogQuery(BaseModel):
    """Model for AI log query parameters"""
    
    mode: QueryMode = Field(..., description="Query mode for AI-optimized results")
    services: List[str] = Field(default=["all"], description="Services to query")
    time_range: str = Field("1h", pattern="^[0-9]+[smhd]$", description="Time range (e.g., 1h, 30m, 7d)")
    
    # Correlation fields
    correlation_id: Optional[str] = Field(None, min_length=1, max_length=64)
    conversation_id: Optional[str] = Field(None, min_length=1, max_length=64)
    session_id: Optional[str] = Field(None, min_length=1, max_length=64)
    workspace_id: Optional[str] = Field(None, min_length=1, max_length=64)
    
    # Filtering options
    severity_threshold: SeverityLevel = Field(SeverityLevel.INFO)
    include_context: int = Field(5, ge=0, le=50, description="Number of context lines")
    exclude_patterns: Optional[List[str]] = Field(None, max_items=10)
    
    # Processing options
    aggregation: AggregationType = Field(AggregationType.NONE)
    format: ResponseFormat = Field(ResponseFormat.STRUCTURED)
    deduplicate: bool = Field(True)
    highlight: Optional[List[str]] = Field(None, max_items=10)
    context_window: Optional[str] = Field(None, pattern="^[0-9]+[smh]$")
    
    # Output options
    verbosity: VerbosityLevel = Field(VerbosityLevel.STANDARD)
    limit: int = Field(1000, ge=1, le=10000)
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "mode": "troubleshoot",
                "services": ["api", "anythingllm"],
                "time_range": "2h",
                "severity_threshold": "error",
                "include_context": 10,
                "format": "structured"
            }
        }


class LogEntry(BaseModel):
    """Model for a single log entry"""
    
    timestamp: datetime
    level: str
    service: str
    message: str
    
    # Optional fields
    correlation_id: Optional[str] = None
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # AI-specific fields
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    duration: Optional[float] = None
    request_type: Optional[str] = None
    error: Optional[str] = None
    
    # Additional context
    context: Optional[Dict[str, Any]] = None
    highlights: Optional[List[str]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2025-01-30T10:30:00Z",
                "level": "error",
                "service": "api",
                "message": "Failed to process AI request",
                "correlation_id": "req-123",
                "conversation_id": "conv-456",
                "model": "gpt-4",
                "tokens_used": 1500,
                "duration": 2.5
            }
        }


class LogSummary(BaseModel):
    """Summary of log analysis results"""
    
    mode: str
    time_range: str
    total_logs: int
    services_affected: List[str]
    patterns_detected: List[str]
    
    # Mode-specific summaries
    error_summary: Optional[Dict[str, Any]] = None
    performance_summary: Optional[Dict[str, Any]] = None
    audit_summary: Optional[Dict[str, Any]] = None
    
    # Key findings
    key_issues: Optional[List[str]] = None
    severity_distribution: Optional[Dict[str, int]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "mode": "errors",
                "time_range": "1h",
                "total_logs": 150,
                "services_affected": ["api", "anythingllm"],
                "patterns_detected": ["connection_timeout", "token_limit_exceeded"],
                "error_summary": {
                    "total_errors": 25,
                    "error_types": {"timeout": 15, "rate_limit": 10},
                    "most_common_error": "timeout"
                }
            }
        }


class LogInsight(BaseModel):
    """Insights derived from log analysis"""
    
    type: str = Field(..., description="Type of insight (anomaly, pattern, recommendation)")
    severity: str = Field(..., description="Severity of the insight")
    title: str = Field(..., description="Brief title of the insight")
    description: str = Field(..., description="Detailed description")
    
    # Supporting data
    evidence: Optional[List[Dict[str, Any]]] = None
    affected_services: Optional[List[str]] = None
    occurrence_count: Optional[int] = None
    
    # Recommendations
    recommended_actions: Optional[List[str]] = None
    related_documentation: Optional[List[str]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "type": "anomaly",
                "severity": "high",
                "title": "Spike in connection timeouts",
                "description": "Detected 10x increase in connection timeouts to AnythingLLM service",
                "affected_services": ["api", "anythingllm"],
                "occurrence_count": 45,
                "recommended_actions": [
                    "Check AnythingLLM service health",
                    "Review network connectivity",
                    "Consider increasing timeout values"
                ]
            }
        }


class AILogResponse(BaseModel):
    """Response model for AI log queries"""
    
    summary: LogSummary
    logs: List[LogEntry]
    insights: Dict[str, List[LogInsight]]
    metadata: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "summary": {
                    "mode": "troubleshoot",
                    "time_range": "1h",
                    "total_logs": 250,
                    "services_affected": ["api", "anythingllm"],
                    "patterns_detected": ["connection_timeout", "rate_limit_exceeded"]
                },
                "logs": [
                    {
                        "timestamp": "2025-01-30T10:30:00Z",
                        "level": "error",
                        "service": "api",
                        "message": "Connection timeout to AnythingLLM",
                        "correlation_id": "req-123"
                    }
                ],
                "insights": {
                    "anomalies": [
                        {
                            "type": "anomaly",
                            "severity": "high",
                            "title": "Service degradation detected",
                            "description": "AnythingLLM response times increased by 300%"
                        }
                    ],
                    "patterns": [],
                    "recommendations": []
                },
                "metadata": {
                    "query_time": "2025-01-30T11:00:00Z",
                    "from_cache": False,
                    "query_duration_ms": 250
                }
            }
        }


class CorrelationResult(BaseModel):
    """Result of cross-service correlation"""
    
    correlation_id: str
    request_flow: Dict[str, Any]  # Graph representation
    service_timeline: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_duration_ms: float
    service_durations: Dict[str, float]
    recommendations: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "correlation_id": "req-123",
                "request_flow": {
                    "nodes": [
                        {"id": "api_1", "service": "api", "timestamp": "2025-01-30T10:00:00Z"},
                        {"id": "llm_1", "service": "anythingllm", "timestamp": "2025-01-30T10:00:01Z"}
                    ],
                    "edges": [
                        {"source": "api_1", "target": "llm_1"}
                    ]
                },
                "service_timeline": [
                    {"service": "api", "start": "10:00:00", "end": "10:00:01", "duration_ms": 1000}
                ],
                "bottlenecks": [
                    {"service": "anythingllm", "duration_ms": 5000, "severity": "high"}
                ],
                "errors": [],
                "total_duration_ms": 6000,
                "service_durations": {"api": 1000, "anythingllm": 5000},
                "recommendations": ["Consider caching AI responses", "Increase AnythingLLM timeout"]
            }
        }


class ConversationLogs(BaseModel):
    """Logs for a specific AI conversation"""
    
    conversation_id: str
    metadata: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]] = None
    prompts: Optional[List[Dict[str, Any]]] = None
    responses: Optional[List[Dict[str, Any]]] = None
    related_logs: Optional[List[LogEntry]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv-456",
                "metadata": {
                    "start_time": "2025-01-30T10:00:00Z",
                    "end_time": "2025-01-30T10:05:00Z",
                    "duration_seconds": 300,
                    "workspace_id": "ws-789"
                },
                "timeline": [
                    {
                        "timestamp": "10:00:00",
                        "event": "conversation_start",
                        "details": {"model": "gpt-4"}
                    }
                ],
                "metrics": {
                    "total_tokens": 5000,
                    "total_cost": 0.15,
                    "average_response_time": 2.5,
                    "error_rate": 0.0
                }
            }
        }


class WorkspaceAISummary(BaseModel):
    """AI usage summary for a workspace"""
    
    workspace_id: str
    time_range: str
    total_conversations: int
    total_requests: int
    total_tokens: int
    models_used: Dict[str, int]
    error_count: int
    average_response_time: float
    peak_usage_times: List[str]
    top_error_patterns: List[Dict[str, Any]]
    cost_breakdown: Optional[Dict[str, float]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "workspace_id": "ws-123",
                "time_range": "24h",
                "total_conversations": 150,
                "total_requests": 500,
                "total_tokens": 250000,
                "models_used": {"gpt-4": 300, "gpt-3.5-turbo": 200},
                "error_count": 5,
                "average_response_time": 2.1,
                "peak_usage_times": ["09:00-10:00", "14:00-15:00"],
                "top_error_patterns": [
                    {"pattern": "rate_limit", "count": 3},
                    {"pattern": "timeout", "count": 2}
                ],
                "cost_breakdown": {
                    "gpt-4": 7.50,
                    "gpt-3.5-turbo": 0.50,
                    "total": 8.00
                }
            }
        }


class ExportRequest(BaseModel):
    """Request model for log export"""
    
    format: str = Field(..., pattern="^(json|jsonl|csv|parquet|markdown)$")
    query_params: AILogQuery
    include_metadata: bool = Field(True)
    compress: bool = Field(False)
    
    class Config:
        schema_extra = {
            "example": {
                "format": "parquet",
                "query_params": {
                    "mode": "troubleshoot",
                    "time_range": "24h",
                    "services": ["all"]
                },
                "include_metadata": True,
                "compress": True
            }
        }


class ExportResponse(BaseModel):
    """Response model for log export"""
    
    export_id: str
    format: str
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "export_id": "export-789",
                "format": "parquet",
                "status": "completed",
                "download_url": "/api/v1/ai_logs/exports/export-789/download",
                "expires_at": "2025-01-31T12:00:00Z",
                "size_bytes": 1048576
            }
        }


class StreamConfig(BaseModel):
    """Configuration for log streaming"""
    
    services: Optional[List[str]] = Field(None, description="Services to stream")
    severity_threshold: Optional[str] = Field("info", pattern="^(debug|info|warn|error|fatal)$")
    pattern_alerts: Optional[List[str]] = Field(None, description="Patterns to alert on")
    include_metrics: bool = Field(True, description="Include real-time metrics")
    
    class Config:
        schema_extra = {
            "example": {
                "services": ["api", "anythingllm"],
                "severity_threshold": "warn",
                "pattern_alerts": ["timeout", "error"],
                "include_metrics": True
            }
        }


class PatternLibrary(BaseModel):
    """Library of available patterns"""
    
    categories: Dict[str, List[str]]
    total_patterns: int
    
    class Config:
        schema_extra = {
            "example": {
                "categories": {
                    "connectivity": ["connection_timeout", "connection_refused"],
                    "performance": ["slow_query", "high_latency"],
                    "ai": ["token_limit_exceeded", "model_timeout"],
                    "security": ["auth_failure", "rate_limit_exceeded"]
                },
                "total_patterns": 12
            }
        }


# Additional models for documentation alignment

class CorrelationRequest(BaseModel):
    """Request model for correlation analysis"""
    
    correlation_id: str = Field(..., min_length=1, max_length=64, description="Correlation ID to trace")
    include_metrics: bool = Field(True, description="Include performance metrics")
    include_errors: bool = Field(True, description="Include error analysis")
    service_graph: bool = Field(True, description="Include service flow graph")
    
    class Config:
        schema_extra = {
            "example": {
                "correlation_id": "req_abc123def456",
                "include_metrics": True,
                "include_errors": True,
                "service_graph": True
            }
        }


class CorrelationResponse(BaseModel):
    """Response model for correlation analysis"""
    
    correlation_id: str
    service_flow: List[Dict[str, Any]]
    total_duration_ms: float
    services_involved: List[str]
    bottlenecks: List[Dict[str, Any]]
    error_propagation: List[Dict[str, Any]]
    recommendations: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "correlation_id": "req_abc123def456",
                "service_flow": [
                    {
                        "service": "api",
                        "timestamp": "2025-06-30T14:30:00.123Z",
                        "duration_ms": 50,
                        "status": "success",
                        "operation": "receive_request"
                    }
                ],
                "total_duration_ms": 1150,
                "services_involved": ["api", "anythingllm"],
                "bottlenecks": [
                    {
                        "service": "anythingllm",
                        "avg_duration_ms": 1100,
                        "percentage_of_total": 95.7
                    }
                ],
                "error_propagation": [],
                "recommendations": [
                    "Consider implementing caching for AnythingLLM vector searches"
                ]
            }
        }


class PatternRequest(BaseModel):
    """Request model for pattern detection"""
    
    time_range: str = Field("24h", pattern="^[0-9]+[smhd]$", description="Time range for analysis")
    services: List[str] = Field(default=["all"], description="Services to analyze")
    min_confidence: float = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence threshold")
    pattern_types: List[str] = Field(default=["errors", "performance"], description="Types of patterns to detect")
    custom_patterns: Optional[List[Dict[str, str]]] = Field(None, description="Custom pattern definitions")
    
    class Config:
        schema_extra = {
            "example": {
                "time_range": "24h",
                "services": ["api", "anythingllm"],
                "min_confidence": 0.8,
                "pattern_types": ["errors", "performance", "security", "rate_limiting"],
                "custom_patterns": [
                    {
                        "name": "custom_timeout",
                        "regex": "timeout.*connection",
                        "description": "Custom timeout pattern"
                    }
                ]
            }
        }


class PatternResponse(BaseModel):
    """Response model for pattern detection"""
    
    patterns_found: List[Dict[str, Any]]
    recommendations: List[str]
    analysis_duration_ms: float
    
    class Config:
        schema_extra = {
            "example": {
                "patterns_found": [
                    {
                        "pattern_type": "rate_limiting",
                        "confidence": 0.95,
                        "occurrences": 15,
                        "description": "Rate limiting events detected on API endpoint",
                        "affected_services": ["api"],
                        "time_distribution": {
                            "peak_hour": "14:00-15:00",
                            "frequency": "every 4 minutes"
                        }
                    }
                ],
                "recommendations": [
                    "Consider implementing request batching for high-volume clients"
                ],
                "analysis_duration_ms": 850
            }
        }


class ConversationTracking(BaseModel):
    """Response model for conversation tracking"""
    
    conversation_id: str
    logs: List[Dict[str, Any]]
    summary: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv_789xyz",
                "logs": [
                    {
                        "timestamp": "2025-06-30T14:30:00Z",
                        "message": "Conversation started",
                        "turn_number": 1,
                        "user_input": "How do I implement React hooks?",
                        "ai_response_preview": "React hooks are functions that...",
                        "tokens_used": 145,
                        "model": "gpt-4"
                    }
                ],
                "summary": {
                    "total_turns": 3,
                    "total_tokens": 450,
                    "average_response_time_ms": 1200,
                    "errors_encountered": 0,
                    "workspace": "react-docs"
                }
            }
        }


class WorkspaceSummary(BaseModel):
    """Response model for workspace summary"""
    
    workspace_id: str
    time_range: str
    metrics: Dict[str, Any]
    top_queries: List[str]
    error_breakdown: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "workspace_id": "ws_react_docs",
                "time_range": "24h",
                "metrics": {
                    "total_requests": 1250,
                    "successful_requests": 1200,
                    "error_rate": 0.04,
                    "average_response_time_ms": 800,
                    "total_tokens_used": 125000,
                    "unique_users": 45
                },
                "top_queries": [
                    "React hooks implementation",
                    "State management patterns",
                    "Component lifecycle"
                ],
                "error_breakdown": [
                    {
                        "error_type": "timeout",
                        "count": 30,
                        "percentage": 60
                    }
                ]
            }
        }