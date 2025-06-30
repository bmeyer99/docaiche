# Comprehensive Production Deployment Plan: AI Logging API for DocAIche

## Executive Summary

This deployment plan outlines the implementation of a sophisticated AI-focused logging API endpoint system that integrates seamlessly with DocAIche's existing infrastructure. The system leverages the current Loki 3.5.0, Promtail 3.5.0, Grafana 12.0.2, and Redis setup while adding AI-specific capabilities for intelligent log analysis, correlation, and troubleshooting.

## 1. Architecture Integration

### 1.1 Current State Analysis

**Existing Infrastructure:**
- **Loki 3.5.0**: Centralized log storage with 7-day retention, 16MB/s ingestion rate
- **Promtail 3.5.0**: Log collection from Docker containers, system journals, and file paths
- **Grafana 12.0.2**: Visualization and dashboards
- **Redis 7**: Caching and session management
- **Structured JSON Logging**: Implemented across all services with specialized loggers
- **Browser Logging**: Already capturing and forwarding to Loki

### 1.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI LOGGING API SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐     ┌──────────────────┐    ┌─────────────────┐  │
│  │  AI Agents  │────▶│ AI Logs API      │───▶│ Loki Backend    │  │
│  └─────────────┘     │ (/api/v1/ai_logs)│    └─────────────────┘  │
│                      └──────────────────┘            │             │
│                               │                      │             │
│                               ▼                      ▼             │
│  ┌─────────────┐     ┌──────────────────┐    ┌─────────────────┐  │
│  │   Redis     │◀────│ Cache Layer      │    │   Grafana       │  │
│  │   Cache     │     │ & Rate Limiter   │    │  Dashboards     │  │
│  └─────────────┘     └──────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Existing Services                         │   │
│  │  ┌────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────┐ │   │
│  │  │  API   │  │ Admin UI │  │ AnythingLLM│  │   Browser   │ │   │
│  │  └────────┘  └──────────┘  └───────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Detailed Implementation Plan

### Phase 1: Foundation (Days 1-5)

#### Day 1-2: Enhanced Logging Infrastructure

**Task 1.1: Update Promtail Configuration**
```yaml
# promtail-config.yaml additions
- job_name: ai_agent_logs
  pipeline_stages:
    - json:
        expressions:
          correlation_id: correlation_id
          conversation_id: conversation_id
          model: model
          tokens_used: tokens_used
          request_type: request_type
          workspace_id: workspace_id
    - labels:
        correlation_id:
        conversation_id:
        model:
        request_type:
        workspace_id:
    - timestamp:
        source: timestamp
        format: RFC3339Nano
    - metrics:
        token_usage:
          type: Counter
          description: "AI tokens used"
          source: tokens_used
          config:
            action: add
        ai_request_duration:
          type: Histogram
          description: "AI request duration"
          source: duration
          config:
            buckets: [0.1, 0.5, 1, 2, 5, 10]
```

**Task 1.2: Update Application Logging**
```python
# src/api/utils/logging_config.py - Add AI-specific logger
class AIOperationLogger:
    """Logger for AI-specific operations"""
    
    def __init__(self):
        self.logger = logging.getLogger("ai_operations")
        
    def log_ai_request(self, 
                      correlation_id: str,
                      conversation_id: str,
                      model: str,
                      prompt: str,
                      tokens: int,
                      duration: float,
                      workspace_id: str,
                      user_id: str,
                      success: bool,
                      error: Optional[str] = None):
        """Log AI operation with full context"""
        self.logger.info(
            "AI Request",
            extra={
                "correlation_id": correlation_id,
                "conversation_id": conversation_id,
                "model": model,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
                "tokens_used": tokens,
                "duration": duration,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "success": success,
                "error": error,
                "request_type": "ai_completion"
            }
        )
```

#### Day 3-4: Core API Structure

**Task 1.3: Create AI Logs API Router**
```python
# src/api/v1/ai_logs_endpoints.py
from fastapi import APIRouter, Query, HTTPException, Depends, WebSocket
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import httpx
from pydantic import BaseModel, Field
from ...dependencies import get_current_user, verify_api_key
from ...utils.ai_log_processor import AILogProcessor
from ...utils.log_correlator import LogCorrelator
from ...utils.pattern_detector import PatternDetector
from ...utils.cache_manager import get_cache_manager
from ...security.rate_limiter import RateLimiter
from ...models.ai_logs import AILogQuery, AILogResponse

router = APIRouter(
    prefix="/ai_logs",
    tags=["AI Logs"],
    dependencies=[Depends(verify_api_key)]
)

# Initialize components
log_processor = AILogProcessor()
correlator = LogCorrelator()
pattern_detector = PatternDetector()
rate_limiter = RateLimiter()

class QueryMode(str, Enum):
    TROUBLESHOOT = "troubleshoot"
    PERFORMANCE = "performance"
    ERRORS = "errors"
    AUDIT = "audit"
    CONVERSATION = "conversation"

@router.get("/query", response_model=AILogResponse)
@rate_limiter.limit("ai_logs:query", max_requests=100, window=3600)
async def query_ai_logs(
    mode: QueryMode = Query(..., description="Query mode for AI-optimized results"),
    services: Optional[List[str]] = Query(None, description="Services to query"),
    time_range: str = Query("1h", regex="^[0-9]+[smhd]$"),
    correlation_id: Optional[str] = Query(None, min_length=1, max_length=64),
    conversation_id: Optional[str] = Query(None, min_length=1, max_length=64),
    session_id: Optional[str] = Query(None, min_length=1, max_length=64),
    workspace_id: Optional[str] = Query(None, min_length=1, max_length=64),
    severity_threshold: str = Query("info", regex="^(debug|info|warn|error|fatal)$"),
    include_context: int = Query(5, ge=0, le=50),
    aggregation: str = Query("none", regex="^(none|by_service|by_error|by_pattern)$"),
    format: str = Query("structured", regex="^(structured|narrative|timeline)$"),
    deduplicate: bool = Query(True),
    highlight: Optional[List[str]] = Query(None, max_items=10),
    context_window: Optional[str] = Query(None, regex="^[0-9]+[smh]$"),
    exclude_patterns: Optional[List[str]] = Query(None, max_items=10),
    verbosity: str = Query("standard", regex="^(minimal|standard|detailed)$"),
    limit: int = Query(1000, ge=1, le=10000),
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
        # Build query parameters
        query_params = AILogQuery(
            mode=mode,
            services=services or ["all"],
            time_range=time_range,
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            session_id=session_id,
            workspace_id=workspace_id,
            severity_threshold=severity_threshold,
            include_context=include_context,
            aggregation=aggregation,
            format=format,
            deduplicate=deduplicate,
            highlight=highlight,
            context_window=context_window,
            exclude_patterns=exclude_patterns,
            verbosity=verbosity,
            limit=limit
        )
        
        # Process query
        result = await log_processor.process_query(query_params, use_cache=cache)
        
        return result
        
    except httpx.TimeoutException:
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
```

**Task 1.4: Implement AI Log Processor**
```python
# src/api/utils/ai_log_processor.py
import asyncio
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from ..models.ai_logs import AILogQuery, AILogResponse, LogInsight
from .loki_client import LokiClient
from .log_analyzer import LogAnalyzer
from .cache_manager import CacheManager
from .query_optimizer import QueryOptimizer

class AILogProcessor:
    def __init__(self):
        self.loki_client = LokiClient()
        self.analyzer = LogAnalyzer()
        self.cache = CacheManager()
        self.optimizer = QueryOptimizer()
        
    async def process_query(self, 
                          query: AILogQuery, 
                          use_cache: bool = True) -> AILogResponse:
        """Process AI log query with intelligent optimization"""
        
        # Generate cache key
        cache_key = self._generate_cache_key(query)
        
        # Check cache
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                cached_result["metadata"]["from_cache"] = True
                return AILogResponse(**cached_result)
        
        # Build optimized LogQL query
        logql_query = await self._build_intelligent_query(query)
        
        # Execute query with timeout and retries
        logs = await self._execute_query_with_retry(logql_query, query)
        
        # Process and analyze logs
        processed_logs = await self._process_logs(logs, query)
        
        # Generate insights
        insights = await self.analyzer.generate_insights(processed_logs, query)
        
        # Build response
        response = AILogResponse(
            summary=self._generate_summary(processed_logs, insights, query),
            logs=self._format_logs(processed_logs, query),
            insights=insights,
            metadata={
                "query_time": datetime.utcnow().isoformat(),
                "total_logs": len(processed_logs),
                "services_queried": query.services,
                "time_range": query.time_range,
                "query_mode": query.mode,
                "from_cache": False,
                "logql_query": logql_query if query.verbosity == "detailed" else None
            }
        )
        
        # Cache result
        if use_cache:
            await self.cache.set(
                cache_key, 
                response.dict(), 
                ttl=self._calculate_cache_ttl(query)
            )
        
        return response
    
    async def _build_intelligent_query(self, query: AILogQuery) -> str:
        """Build optimized LogQL query based on mode and parameters"""
        
        # Base query
        base_selector = self._build_stream_selector(query)
        
        # Mode-specific optimizations
        mode_filters = self._get_mode_filters(query.mode)
        
        # Build filter pipeline
        filters = []
        
        # Add severity filter
        if query.severity_threshold != "debug":
            severity_levels = ["fatal", "error", "warn", "info", "debug"]
            threshold_index = severity_levels.index(query.severity_threshold)
            allowed_levels = severity_levels[:threshold_index + 1]
            filters.append(f'|~ "level=({"|".join(allowed_levels)})"')
        
        # Add correlation filters
        if query.correlation_id:
            filters.append(f'|> "correlation_id={query.correlation_id}"')
        if query.conversation_id:
            filters.append(f'|> "conversation_id={query.conversation_id}"')
        if query.session_id:
            filters.append(f'|> "session_id={query.session_id}"')
        if query.workspace_id:
            filters.append(f'|> "workspace_id={query.workspace_id}"')
        
        # Add mode-specific filters
        filters.extend(mode_filters)
        
        # Add exclude patterns
        if query.exclude_patterns:
            for pattern in query.exclude_patterns:
                filters.append(f'!~ "{pattern}"')
        
        # Combine query parts
        logql_query = base_selector + " " + " ".join(filters)
        
        # Add time range
        time_range = self._parse_time_range(query.time_range)
        logql_query = f'{logql_query} | __timestamp__ > {time_range}'
        
        # Optimize query
        return self.optimizer.optimize(logql_query, query)
```

#### Day 5: Database Schema Updates

**Task 1.5: Add AI Logging Tables**
```python
# src/api/alembic/versions/xxx_add_ai_logging_tables.py
"""Add AI logging tables

Revision ID: xxx
Revises: previous_revision
Create Date: 2025-01-30
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # AI query history table
    op.create_table(
        'ai_query_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('query_params', sa.JSON, nullable=False),
        sa.Column('result_summary', sa.JSON),
        sa.Column('execution_time_ms', sa.Integer),
        sa.Column('cache_hit', sa.Boolean, default=False),
        sa.Column('user_id', sa.String(36)),
        sa.Column('api_key_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Index('idx_ai_query_user', 'user_id'),
        sa.Index('idx_ai_query_created', 'created_at')
    )
    
    # Pattern detection results
    op.create_table(
        'detected_patterns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('occurrence_count', sa.Integer, default=1),
        sa.Column('first_seen', sa.DateTime, nullable=False),
        sa.Column('last_seen', sa.DateTime, nullable=False),
        sa.Column('affected_services', sa.JSON),
        sa.Column('sample_logs', sa.JSON),
        sa.Column('resolved', sa.Boolean, default=False),
        sa.Column('resolution_notes', sa.Text),
        sa.Index('idx_pattern_type', 'pattern_type'),
        sa.Index('idx_pattern_severity', 'severity'),
        sa.Index('idx_pattern_resolved', 'resolved')
    )
    
    # AI conversation tracking
    op.create_table(
        'ai_conversations',
        sa.Column('conversation_id', sa.String(36), primary_key=True),
        sa.Column('workspace_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36)),
        sa.Column('model', sa.String(50)),
        sa.Column('total_tokens', sa.Integer, default=0),
        sa.Column('total_cost', sa.Float, default=0.0),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
        sa.Index('idx_conversation_workspace', 'workspace_id'),
        sa.Index('idx_conversation_user', 'user_id')
    )

def downgrade():
    op.drop_table('ai_conversations')
    op.drop_table('detected_patterns')
    op.drop_table('ai_query_history')
```

### Phase 2: Advanced Features (Days 6-10)

#### Day 6-7: Correlation System

**Task 2.1: Implement Log Correlator**
```python
# src/api/utils/log_correlator.py
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import networkx as nx
from .loki_client import LokiClient

class LogCorrelator:
    def __init__(self):
        self.loki = LokiClient()
        
    async def correlate_request(self, 
                               correlation_id: str,
                               time_window: Optional[str] = None) -> Dict[str, Any]:
        """Correlate logs across all services for a specific request"""
        
        # Define services to query
        services = [
            "api",
            "admin-ui",
            "anythingllm",
            "browser",
            "redis",
            "promtail"
        ]
        
        # Build correlation queries for each service
        correlation_tasks = []
        for service in services:
            query = self._build_correlation_query(service, correlation_id, time_window)
            correlation_tasks.append(
                self._query_service_logs(service, query)
            )
        
        # Execute queries in parallel
        service_logs = await asyncio.gather(*correlation_tasks, return_exceptions=True)
        
        # Build request flow
        flow = self._build_request_flow(correlation_id, service_logs)
        
        # Analyze flow for issues
        analysis = self._analyze_request_flow(flow)
        
        return {
            "correlation_id": correlation_id,
            "request_flow": flow,
            "service_timeline": self._build_timeline(service_logs),
            "bottlenecks": analysis["bottlenecks"],
            "errors": analysis["errors"],
            "total_duration_ms": analysis["total_duration"],
            "service_durations": analysis["service_durations"],
            "recommendations": self._generate_recommendations(analysis)
        }
    
    def _build_request_flow(self, 
                           correlation_id: str, 
                           service_logs: List[Dict]) -> Dict[str, Any]:
        """Build a directed graph of request flow"""
        
        G = nx.DiGraph()
        
        # Process logs from each service
        for service_data in service_logs:
            if isinstance(service_data, Exception):
                continue
                
            service = service_data["service"]
            logs = service_data["logs"]
            
            for log in logs:
                # Extract relevant information
                timestamp = log.get("timestamp")
                message = log.get("message", "")
                
                # Add node
                node_id = f"{service}_{timestamp}"
                G.add_node(node_id, 
                          service=service,
                          timestamp=timestamp,
                          message=message,
                          level=log.get("level", "info"))
                
                # Try to identify connections
                if "calling" in message.lower() or "request to" in message.lower():
                    # Extract target service
                    target = self._extract_target_service(message)
                    if target:
                        # Find corresponding node in target service
                        target_node = self._find_target_node(G, target, timestamp)
                        if target_node:
                            G.add_edge(node_id, target_node)
        
        # Convert to serializable format
        return {
            "nodes": [
                {
                    "id": node,
                    **G.nodes[node]
                }
                for node in G.nodes()
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1]
                }
                for edge in G.edges()
            ]
        }
```

**Task 2.2: Pattern Detection System**
```python
# src/api/utils/pattern_detector.py
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import numpy as np
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

class PatternDetector:
    def __init__(self):
        self.patterns = self._load_patterns()
        self.vectorizer = TfidfVectorizer(max_features=100)
        
    def _load_patterns(self) -> Dict[str, Dict]:
        """Load predefined patterns for detection"""
        return {
            # Connection issues
            "connection_timeout": {
                "regex": r"(timeout|timed out|connection.*failed|unable to connect)",
                "severity": "high",
                "category": "connectivity",
                "suggestion": "Check network connectivity and service health"
            },
            "connection_refused": {
                "regex": r"(connection refused|ECONNREFUSED|port.*closed)",
                "severity": "high",
                "category": "connectivity",
                "suggestion": "Verify service is running and port is open"
            },
            
            # Rate limiting
            "rate_limit_exceeded": {
                "regex": r"(rate limit|too many requests|429|throttled)",
                "severity": "medium",
                "category": "rate_limiting",
                "suggestion": "Implement exponential backoff or increase rate limits"
            },
            
            # Memory issues
            "out_of_memory": {
                "regex": r"(out of memory|memory exhausted|OOM|heap space)",
                "severity": "critical",
                "category": "resources",
                "suggestion": "Increase memory allocation or optimize memory usage"
            },
            "memory_leak": {
                "regex": r"(memory leak|growing memory|memory not released)",
                "severity": "high",
                "category": "resources",
                "suggestion": "Profile memory usage and fix leaks"
            },
            
            # Database issues
            "db_connection_pool": {
                "regex": r"(connection pool.*exhausted|no available connections|pool timeout)",
                "severity": "high",
                "category": "database",
                "suggestion": "Increase connection pool size or optimize queries"
            },
            "slow_query": {
                "regex": r"(slow query|query took|execution time.*exceeded)",
                "severity": "medium",
                "category": "database",
                "suggestion": "Optimize query or add appropriate indexes"
            },
            
            # AI-specific patterns
            "token_limit_exceeded": {
                "regex": r"(token limit|max tokens|context length exceeded)",
                "severity": "medium",
                "category": "ai",
                "suggestion": "Reduce prompt size or use a model with larger context"
            },
            "model_timeout": {
                "regex": r"(model timeout|inference timeout|prediction timeout)",
                "severity": "high",
                "category": "ai",
                "suggestion": "Increase timeout or optimize model inference"
            },
            "hallucination_detected": {
                "regex": r"(hallucination|factual error|inconsistent response)",
                "severity": "medium",
                "category": "ai",
                "suggestion": "Implement fact-checking or use more reliable model"
            },
            
            # Security patterns
            "auth_failure": {
                "regex": r"(authentication failed|unauthorized|invalid credentials|401)",
                "severity": "medium",
                "category": "security",
                "suggestion": "Verify credentials and authentication flow"
            },
            "permission_denied": {
                "regex": r"(permission denied|access denied|forbidden|403)",
                "severity": "medium",
                "category": "security",
                "suggestion": "Check user permissions and access controls"
            },
            
            # File processing
            "file_parsing_error": {
                "regex": r"(parsing error|invalid format|malformed|corrupt file)",
                "severity": "medium",
                "category": "file_processing",
                "suggestion": "Validate file format and implement error handling"
            },
            "file_size_limit": {
                "regex": r"(file too large|size limit|exceeds maximum)",
                "severity": "low",
                "category": "file_processing",
                "suggestion": "Implement file chunking or increase size limits"
            }
        }
    
    async def detect_patterns(self, logs: List[Dict]) -> List[Dict]:
        """Detect patterns in logs using multiple techniques"""
        
        # 1. Regex-based pattern detection
        regex_patterns = self._detect_regex_patterns(logs)
        
        # 2. Anomaly detection using clustering
        anomalies = await self._detect_anomalies(logs)
        
        # 3. Temporal pattern detection
        temporal_patterns = self._detect_temporal_patterns(logs)
        
        # 4. Error cascade detection
        cascades = self._detect_error_cascades(logs)
        
        # Combine all detected patterns
        all_patterns = {
            "known_patterns": regex_patterns,
            "anomalies": anomalies,
            "temporal_patterns": temporal_patterns,
            "error_cascades": cascades
        }
        
        # Generate insights
        return self._generate_pattern_insights(all_patterns, logs)
```

#### Day 8: Real-time Streaming

**Task 2.3: WebSocket Streaming Endpoint**
```python
# src/api/v1/ai_logs_endpoints.py (addition)
@router.websocket("/stream")
async def stream_logs(
    websocket: WebSocket,
    api_key: str = Query(...),
):
    """Real-time log streaming with intelligent filtering and alerts"""
    
    # Verify API key
    if not await verify_api_key(api_key):
        await websocket.close(code=4001, reason="Invalid API key")
        return
    
    await websocket.accept()
    
    stream_manager = StreamManager(websocket)
    
    try:
        # Receive initial configuration
        config_data = await websocket.receive_json()
        config = StreamConfig(**config_data)
        
        # Validate rate limits
        if not await rate_limiter.check_streaming_limit(api_key):
            await websocket.send_json({
                "type": "error",
                "data": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Streaming rate limit exceeded"
                }
            })
            await websocket.close(code=4029)
            return
        
        # Start streaming
        await stream_manager.start_streaming(config)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for API key: {api_key}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)}
        })
    finally:
        await stream_manager.cleanup()

class StreamManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.loki_client = LokiClient()
        self.pattern_detector = PatternDetector()
        self.alert_manager = AlertManager()
        self.active = True
        
    async def start_streaming(self, config: StreamConfig):
        """Start streaming logs based on configuration"""
        
        # Build streaming query
        query = self._build_stream_query(config)
        
        # Create Loki tail connection
        async with self.loki_client.tail(query) as stream:
            # Send connection confirmation
            await self.websocket.send_json({
                "type": "connected",
                "data": {
                    "query": query,
                    "filters": config.dict()
                }
            })
            
            # Process incoming logs
            async for log_batch in stream:
                if not self.active:
                    break
                
                # Process logs
                processed_logs = await self._process_stream_batch(log_batch, config)
                
                # Send to client
                for log in processed_logs:
                    await self.websocket.send_json({
                        "type": "log",
                        "data": log
                    })
                    
                    # Check for alerts
                    if alerts := await self.alert_manager.check_alerts(log, config):
                        await self.websocket.send_json({
                            "type": "alert",
                            "data": alerts
                        })
```

#### Day 9-10: AI-Specific Features

**Task 2.4: Conversation Tracking**
```python
# src/api/v1/ai_logs_endpoints.py (addition)
@router.get("/conversations/{conversation_id}")
async def get_conversation_logs(
    conversation_id: str,
    include_prompts: bool = Query(True),
    include_responses: bool = Query(True),
    include_metrics: bool = Query(True),
    include_related_logs: bool = Query(False),
    time_buffer: str = Query("5m", description="Time buffer around conversation")
) -> Dict[str, Any]:
    """Get comprehensive logs for a specific AI conversation"""
    
    try:
        # Query conversation logs
        conversation_logs = await log_processor.get_conversation_logs(
            conversation_id=conversation_id,
            time_buffer=time_buffer
        )
        
        # Extract conversation data
        conversation_data = {
            "conversation_id": conversation_id,
            "metadata": await _get_conversation_metadata(conversation_id),
            "timeline": _build_conversation_timeline(conversation_logs),
            "metrics": None,
            "prompts": None,
            "responses": None,
            "related_logs": None
        }
        
        # Include metrics if requested
        if include_metrics:
            conversation_data["metrics"] = {
                "total_tokens": _calculate_total_tokens(conversation_logs),
                "total_cost": _calculate_conversation_cost(conversation_logs),
                "average_response_time": _calculate_avg_response_time(conversation_logs),
                "error_rate": _calculate_error_rate(conversation_logs),
                "model_distribution": _get_model_distribution(conversation_logs)
            }
        
        # Include prompts/responses if requested
        if include_prompts:
            conversation_data["prompts"] = _extract_prompts(conversation_logs)
        if include_responses:
            conversation_data["responses"] = _extract_responses(conversation_logs)
        
        # Include related logs if requested
        if include_related_logs:
            # Find logs from same session/user around the conversation
            related = await _get_related_logs(conversation_logs)
            conversation_data["related_logs"] = related
        
        return conversation_data
        
    except Exception as e:
        logger.error(f"Failed to get conversation logs: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to retrieve conversation logs", "message": str(e)}
        )

@router.get("/workspace/{workspace_id}/summary")
async def get_workspace_ai_summary(
    workspace_id: str,
    time_range: str = Query("24h"),
    include_costs: bool = Query(True)
) -> Dict[str, Any]:
    """Get AI usage summary for a workspace"""
    
    # Query all AI-related logs for workspace
    logs = await log_processor.get_workspace_ai_logs(workspace_id, time_range)
    
    summary = {
        "workspace_id": workspace_id,
        "time_range": time_range,
        "total_conversations": len(set(log.get("conversation_id") for log in logs)),
        "total_requests": len([l for l in logs if l.get("request_type") == "ai_completion"]),
        "total_tokens": sum(log.get("tokens_used", 0) for log in logs),
        "models_used": Counter(log.get("model") for log in logs if log.get("model")),
        "error_count": len([l for l in logs if l.get("level") == "error"]),
        "average_response_time": _calculate_avg_response_time(logs),
        "peak_usage_times": _identify_peak_usage(logs),
        "top_error_patterns": _get_top_errors(logs, limit=5)
    }
    
    if include_costs:
        summary["cost_breakdown"] = _calculate_cost_breakdown(logs)
    
    return summary
```

### Phase 3: Integration & Testing (Days 11-15)

#### Day 11-12: Service Integration

**Task 3.1: Update API Service for Trace Propagation**
```python
# src/api/middleware/trace_propagation.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from ..utils.logging_config import logger

class TracePropagationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Extract other tracking headers
        session_id = request.headers.get("X-Session-ID")
        user_id = request.headers.get("X-User-ID")
        
        # Store in request state
        request.state.correlation_id = correlation_id
        request.state.session_id = session_id
        request.state.user_id = user_id
        
        # Log request with correlation
        logger.info(
            "Incoming request",
            extra={
                "correlation_id": correlation_id,
                "session_id": session_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response

# Update main.py to use middleware
app.add_middleware(TracePropagationMiddleware)
```

**Task 3.2: Update AnythingLLM Integration**
```python
# src/api/utils/anythingllm_client.py (update)
class AnythingLLMClient:
    async def query(self, 
                   prompt: str, 
                   workspace_id: str,
                   correlation_id: Optional[str] = None,
                   conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Query AnythingLLM with enhanced logging"""
        
        # Generate IDs if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Log request
        start_time = time.time()
        ai_logger.log_ai_request(
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            model="anythingllm",  # Will be updated with actual model
            prompt=prompt,
            tokens=self._estimate_tokens(prompt),
            duration=0,  # Will be updated
            workspace_id=workspace_id,
            user_id=get_current_user_id(),
            success=False,  # Will be updated
            error=None
        )
        
        try:
            # Make request with correlation headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Correlation-ID": correlation_id,
                "X-Conversation-ID": conversation_id
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/workspace/{workspace_id}/chat",
                json={"message": prompt},
                headers=headers
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Log success
            duration = time.time() - start_time
            ai_logger.log_ai_request(
                correlation_id=correlation_id,
                conversation_id=conversation_id,
                model=result.get("model", "unknown"),
                prompt=prompt,
                tokens=result.get("tokens", {}).get("total", 0),
                duration=duration,
                workspace_id=workspace_id,
                user_id=get_current_user_id(),
                success=True,
                error=None
            )
            
            return result
            
        except Exception as e:
            # Log failure
            duration = time.time() - start_time
            ai_logger.log_ai_request(
                correlation_id=correlation_id,
                conversation_id=conversation_id,
                model="unknown",
                prompt=prompt,
                tokens=self._estimate_tokens(prompt),
                duration=duration,
                workspace_id=workspace_id,
                user_id=get_current_user_id(),
                success=False,
                error=str(e)
            )
            raise
```

#### Day 13: Testing Framework

**Task 3.3: Comprehensive Test Suite**
```python
# tests/test_ai_logs_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import asyncio
from datetime import datetime, timedelta

class TestAILogsAPI:
    @pytest.fixture
    def client(self):
        from src.main import app
        return TestClient(app)
    
    @pytest.fixture
    def api_headers(self):
        return {
            "X-API-Key": "test-api-key",
            "X-Correlation-ID": "test-correlation-123"
        }
    
    def test_query_basic(self, client, api_headers):
        """Test basic AI log query"""
        response = client.get(
            "/api/v1/ai_logs/query",
            params={
                "mode": "troubleshoot",
                "time_range": "1h",
                "services": ["api", "anythingllm"]
            },
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "logs" in data
        assert "insights" in data
        assert "metadata" in data
    
    def test_correlation_tracking(self, client, api_headers):
        """Test cross-service correlation"""
        correlation_id = "test-correlation-456"
        
        response = client.get(
            f"/api/v1/ai_logs/correlate",
            params={"correlation_id": correlation_id},
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == correlation_id
        assert "request_flow" in data
        assert "service_timeline" in data
        assert "bottlenecks" in data
    
    @pytest.mark.asyncio
    async def test_websocket_streaming(self, client, api_headers):
        """Test WebSocket log streaming"""
        with client.websocket_connect(
            f"/api/v1/ai_logs/stream?api_key=test-api-key"
        ) as websocket:
            # Send configuration
            websocket.send_json({
                "services": ["api"],
                "severity_threshold": "error",
                "pattern_alerts": ["timeout", "error"]
            })
            
            # Receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
            
            # Simulate receiving logs
            # In real test, mock Loki responses
    
    def test_conversation_logs(self, client, api_headers):
        """Test conversation-specific log retrieval"""
        conversation_id = "conv-789"
        
        response = client.get(
            f"/api/v1/ai_logs/conversations/{conversation_id}",
            params={
                "include_prompts": True,
                "include_metrics": True
            },
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert "metrics" in data
        assert "timeline" in data
    
    def test_rate_limiting(self, client, api_headers):
        """Test rate limiting enforcement"""
        # Make multiple requests
        for i in range(101):  # Exceed limit of 100
            response = client.get(
                "/api/v1/ai_logs/query",
                params={"mode": "errors", "time_range": "1h"},
                headers=api_headers
            )
            
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()
```

#### Day 14-15: Documentation & Monitoring

**Task 3.4: API Documentation**
```python
# src/api/docs/ai_logs_api.py
from typing import Dict, Any
from pydantic import BaseModel, Field

class AILogsAPIDocumentation:
    """
    AI Logs API Documentation
    
    The AI Logs API provides intelligent log querying and analysis capabilities
    specifically designed for AI agents and automated troubleshooting.
    """
    
    EXAMPLES = {
        "troubleshoot_ingestion": {
            "description": "Troubleshoot document ingestion failures",
            "request": {
                "method": "GET",
                "endpoint": "/api/v1/ai_logs/query",
                "params": {
                    "mode": "troubleshoot",
                    "services": ["api", "anythingllm"],
                    "time_range": "2h",
                    "severity_threshold": "error",
                    "include_context": 10,
                    "format": "structured"
                }
            },
            "response": {
                "summary": {
                    "issue": "Document parsing timeout",
                    "affected_count": 5,
                    "pattern": "PDF processing timeout after 30s",
                    "first_seen": "2025-01-30T10:00:00Z"
                },
                "insights": {
                    "root_cause": "Large PDF files exceeding processing limits",
                    "recommendation": "Implement chunked processing for files >10MB"
                }
            }
        },
        
        "track_conversation": {
            "description": "Track AI conversation performance",
            "request": {
                "method": "GET",
                "endpoint": "/api/v1/ai_logs/conversations/{conversation_id}",
                "params": {
                    "include_metrics": True,
                    "include_prompts": False
                }
            },
            "response": {
                "conversation_id": "conv-123",
                "metrics": {
                    "total_tokens": 1500,
                    "total_cost": 0.03,
                    "average_response_time": 2.5,
                    "error_rate": 0.0
                }
            }
        }
    }
    
    PATTERNS = {
        "connection_issues": [
            "connection_timeout",
            "connection_refused", 
            "network_unreachable"
        ],
        "performance_issues": [
            "slow_query",
            "high_latency",
            "resource_exhaustion"
        ],
        "ai_specific": [
            "token_limit_exceeded",
            "model_timeout",
            "context_overflow"
        ]
    }
```

**Task 3.5: Grafana Dashboards**
```json
// grafana/dashboards/ai-logs-dashboard.json
{
  "dashboard": {
    "title": "AI Logs Analysis Dashboard",
    "panels": [
      {
        "title": "AI Query Volume",
        "targets": [{
          "expr": "sum(rate(ai_logs_queries_total[5m])) by (mode)"
        }]
      },
      {
        "title": "Pattern Detection Rate",
        "targets": [{
          "expr": "sum(rate(detected_patterns_total[5m])) by (pattern_type, severity)"
        }]
      },
      {
        "title": "AI Conversation Metrics",
        "targets": [{
          "expr": "histogram_quantile(0.95, sum(rate(ai_request_duration_bucket[5m])) by (le))"
        }]
      },
      {
        "title": "Error Patterns",
        "targets": [{
          "expr": "topk(10, sum(rate(log_errors_total[5m])) by (error_pattern))"
        }]
      }
    ]
  }
}
```

### Phase 4: Deployment & Optimization (Days 16-20)

#### Day 16-17: Deployment Configuration

**Task 4.1: Update Docker Configuration**
```dockerfile
# src/api/Dockerfile (additions)
# Add AI logs dependencies
RUN pip install --no-cache-dir \
    scikit-learn==1.3.0 \
    networkx==3.1 \
    numpy==1.24.3 \
    httpx[http2]==0.24.1

# Add AI logs module
COPY src/api/v1/ai_logs_endpoints.py /app/src/api/v1/
COPY src/api/utils/ai_log_processor.py /app/src/api/utils/
COPY src/api/utils/log_correlator.py /app/src/api/utils/
COPY src/api/utils/pattern_detector.py /app/src/api/utils/
```

**Task 4.2: Environment Configuration**
```yaml
# docker-compose.yml (additions)
services:
  api:
    environment:
      # Add AI logs configuration
      - AI_LOGS_ENABLED=true
      - AI_LOGS_CACHE_TTL=300
      - AI_LOGS_MAX_QUERY_TIME=30
      - AI_LOGS_PATTERN_DETECTION=true
      - AI_LOGS_RATE_LIMIT_PER_HOUR=100
      - TRACE_PROPAGATION_ENABLED=true
```

#### Day 18: Performance Optimization

**Task 4.3: Query Optimization**
```python
# src/api/utils/query_optimizer.py
class QueryOptimizer:
    def __init__(self):
        self.query_cache = {}
        self.performance_stats = defaultdict(list)
    
    def optimize(self, query: str, params: AILogQuery) -> str:
        """Optimize LogQL query for performance"""
        
        # 1. Time range optimization
        query = self._optimize_time_range(query, params.time_range)
        
        # 2. Service filtering optimization
        if params.services and params.services != ["all"]:
            query = self._add_service_filter_early(query, params.services)
        
        # 3. Add sampling for large time ranges
        if self._should_sample(params):
            query = self._add_sampling(query, params)
        
        # 4. Optimize regex patterns
        query = self._optimize_regex_patterns(query)
        
        # 5. Add index hints
        query = self._add_index_hints(query, params)
        
        # Track performance
        self._track_query_performance(query, params)
        
        return query
    
    def _should_sample(self, params: AILogQuery) -> bool:
        """Determine if sampling should be applied"""
        time_range_seconds = self._parse_time_to_seconds(params.time_range)
        
        # Sample if querying more than 6 hours of data
        if time_range_seconds > 21600:
            return True
            
        # Sample if no specific filters
        if not any([params.correlation_id, params.conversation_id, 
                   params.session_id, params.workspace_id]):
            return True
            
        return False
```

#### Day 19-20: Monitoring & Alerting

**Task 4.4: Prometheus Metrics**
```python
# src/api/metrics/ai_logs_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Query metrics
ai_logs_queries_total = Counter(
    'ai_logs_queries_total',
    'Total number of AI log queries',
    ['mode', 'cache_hit']
)

ai_logs_query_duration = Histogram(
    'ai_logs_query_duration_seconds',
    'AI log query duration',
    ['mode'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Pattern detection metrics
detected_patterns_total = Counter(
    'detected_patterns_total',
    'Total patterns detected',
    ['pattern_type', 'severity']
)

# Streaming metrics
active_websocket_connections = Gauge(
    'ai_logs_active_websocket_connections',
    'Active WebSocket connections for log streaming'
)

# Error metrics
ai_logs_errors_total = Counter(
    'ai_logs_errors_total',
    'Total errors in AI logs API',
    ['error_type', 'endpoint']
)
```

**Task 4.5: Alert Rules**
```yaml
# prometheus/alerts/ai_logs_alerts.yml
groups:
  - name: ai_logs_alerts
    rules:
      - alert: HighAILogQueryLatency
        expr: |
          histogram_quantile(0.95, 
            sum(rate(ai_logs_query_duration_seconds_bucket[5m])) by (le)
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High AI log query latency"
          description: "95th percentile query latency is {{ $value }}s"
      
      - alert: AILogPatternDetectionSpike
        expr: |
          sum(rate(detected_patterns_total{severity="critical"}[5m])) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical pattern detection spike"
          description: "Detecting {{ $value }} critical patterns per second"
```

## 3. Rollout Strategy

### Stage 1: Development Environment (Week 1)
1. Deploy foundation components
2. Run integration tests
3. Validate pattern detection

### Stage 2: Staging Environment (Week 2)
1. Full feature deployment
2. Load testing
3. Security audit
4. Documentation review

### Stage 3: Production Rollout (Week 3)
1. Canary deployment (10% traffic)
2. Monitor metrics and errors
3. Gradual rollout to 100%
4. Enable all features

### Stage 4: Optimization (Week 4)
1. Performance tuning based on metrics
2. Pattern library expansion
3. Cache optimization
4. Cost analysis

## 4. Success Criteria

### Performance Metrics
- Query response time p95 < 1s
- Pattern detection accuracy > 90%
- Cache hit rate > 80%
- System availability > 99.9%

### Business Metrics
- Reduced troubleshooting time by 50%
- Automated issue detection > 75%
- AI agent efficiency improvement > 40%

## 5. Risk Mitigation

### Technical Risks
- **Loki overload**: Implement query complexity scoring and rejection
- **Memory issues**: Set hard limits on query results and processing
- **Network failures**: Circuit breakers and fallback mechanisms

### Operational Risks
- **Rollback plan**: Feature flags for instant disable
- **Data privacy**: PII masking at ingestion and query time
- **Cost overrun**: Usage monitoring and automatic throttling

## 6. Maintenance Plan

### Daily Tasks
- Monitor error rates and latencies
- Review detected patterns
- Check resource usage

### Weekly Tasks
- Pattern library updates
- Performance optimization
- Security audit

### Monthly Tasks
- Cost analysis
- Feature usage review
- Architecture review

This comprehensive deployment plan provides a production-ready implementation of the AI Logging API that integrates seamlessly with DocAIche's existing infrastructure while adding powerful AI-specific capabilities for troubleshooting and analysis.