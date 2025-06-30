# MCP Architecture Documentation

## Overview

The DocaiChe MCP (Model Context Protocol) implementation provides a standardized interface for AI agents to interact with documentation systems. This document describes the architectural design, component interactions, and key design decisions.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Clients                              │
│                    (AI Agents, SDKs)                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ MCP Protocol (JSON-RPC 2.0)
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                    MCP Server Layer                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Transport  │  │    Auth      │  │    Protocol        │    │
│  │  Manager    │  │   Handler    │  │    Handler         │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │    Tool     │  │   Resource   │  │    Security        │    │
│  │  Registry   │  │   Registry   │  │    Manager         │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Adapter Layer
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                 DocaiChe Core System                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │   FastAPI   │  │   Search     │  │    Document        │    │
│  │   Backend   │  │   Engine     │  │    Storage         │    │
│  └─────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Transport Layer

The transport layer handles protocol-level communication between MCP clients and the server.

```python
BaseTransport (Abstract)
├── HTTPTransport
│   ├── HTTP/2 Support
│   ├── HTTP/1.1 Fallback
│   └── Compression (gzip, br)
└── WebSocketTransport
    ├── Real-time Updates
    ├── Heartbeat Management
    └── Reconnection Logic
```

**Key Features:**
- Protocol negotiation (HTTP/2 preferred)
- Automatic compression
- Connection pooling
- Circuit breaker pattern for resilience

### 2. Authentication Layer

Implements OAuth 2.1 with Resource Indicators (RFC 8707).

```python
AuthenticationHandler
├── OAuthHandler
│   ├── Client Credentials Flow
│   ├── Token Validation
│   └── Resource Indicators
└── JWTValidator
    ├── RS256 Signature Verification
    ├── Token Expiry Check
    └── Scope Validation
```

**Security Features:**
- JWT with RSA signatures
- Token introspection
- Scope-based authorization
- Rate limiting per client

### 3. Protocol Handler

Manages MCP protocol operations and message routing.

```python
MCPProtocolHandler
├── MessageParser
│   ├── JSON-RPC 2.0 Parsing
│   └── Schema Validation
├── MethodRouter
│   ├── Tool Invocation
│   ├── Resource Access
│   └── System Methods
└── ResponseFormatter
    ├── Success Responses
    └── Error Responses
```

### 4. Tool System

Extensible tool framework for documentation operations.

```python
BaseTool (Abstract)
├── SearchTool
│   ├── Query Processing
│   ├── Result Ranking
│   └── Metadata Enrichment
├── IngestTool
│   ├── Content Validation
│   ├── Consent Management
│   └── Indexing Pipeline
└── FeedbackTool
    ├── Feedback Collection
    ├── Analytics Integration
    └── Quality Metrics
```

**Tool Lifecycle:**
1. Request validation
2. Authentication check
3. Rate limiting
4. Tool execution
5. Response caching
6. Audit logging

### 5. Resource System

Provides access to system resources and metadata.

```python
BaseResource (Abstract)
├── CollectionsResource
│   ├── Collection Enumeration
│   ├── Access Control
│   └── Metadata Aggregation
└── StatusResource
    ├── Health Checks
    ├── Component Status
    └── Performance Metrics
```

### 6. Security Framework

Cross-cutting security concerns implemented as middleware.

```python
SecurityManager
├── RateLimiter
│   ├── Token Bucket Algorithm
│   ├── Client-specific Limits
│   └── Burst Handling
├── ConsentManager
│   ├── Consent Tracking
│   ├── Purpose Validation
│   └── Audit Trail
└── ThreatDetector
    ├── Pattern Analysis
    ├── Anomaly Detection
    └── Automated Response
```

### 7. Monitoring & Observability

Comprehensive monitoring across all layers.

```python
ObservabilityService
├── StructuredLogging
│   ├── JSON Format
│   ├── Correlation IDs
│   └── Log Levels
├── MetricsCollection
│   ├── Prometheus Format
│   ├── Custom Metrics
│   └── Aggregation
├── DistributedTracing
│   ├── W3C Trace Context
│   ├── Span Management
│   └── Export (Jaeger/Zipkin)
└── HealthMonitoring
    ├── Component Checks
    ├── Dependency Status
    └── SLA Tracking
```

## Data Flow Architecture

### Request Flow

```
Client Request
    │
    ▼
[Transport Layer]
    │ Parse & Validate
    ▼
[Authentication]
    │ Verify Token & Scopes
    ▼
[Rate Limiting]
    │ Check Limits
    ▼
[Security Checks]
    │ Threat Detection
    ▼
[Protocol Handler]
    │ Route Request
    ▼
[Tool/Resource Execution]
    │ Process Request
    ▼
[Cache Layer]
    │ Check/Update Cache
    ▼
[Response Formatting]
    │ Format Response
    ▼
[Audit Logging]
    │ Log Transaction
    ▼
Client Response
```

### Caching Architecture

Multi-level caching for optimal performance:

```
┌─────────────────┐
│  Client Cache   │  (Browser/SDK)
└────────┬────────┘
         │
┌────────▼────────┐
│   CDN Cache     │  (Static Resources)
└────────┬────────┘
         │
┌────────▼────────┐
│ Response Cache  │  (Redis)
└────────┬────────┘
         │
┌────────▼────────┐
│ Application     │  (In-Memory)
│    Cache        │
└────────┬────────┘
         │
┌────────▼────────┐
│ Database Cache  │  (Query Cache)
└─────────────────┘
```

## Scalability Architecture

### Horizontal Scaling

```
                    Load Balancer
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   MCP Server 1     MCP Server 2     MCP Server N
        │                │                │
        └────────────────┼────────────────┘
                         │
                 Shared Services
              (Redis, Database)
```

### Service Mesh Integration

```yaml
apiVersion: v1
kind: Service
metadata:
  name: docaiche-mcp
  labels:
    app: docaiche
    service: mcp
spec:
  ports:
  - port: 8000
    name: http
  - port: 8001
    name: grpc
  selector:
    app: docaiche-mcp
```

## Security Architecture

### Defense in Depth

```
Layer 1: Network Security
├── TLS 1.3
├── Certificate Pinning
└── DDoS Protection

Layer 2: Application Security
├── OAuth 2.1 Authentication
├── JWT with RSA Signatures
└── Scope-based Authorization

Layer 3: Data Security
├── Encryption at Rest
├── Field-level Encryption
└── PII Tokenization

Layer 4: Operational Security
├── Audit Logging
├── Anomaly Detection
└── Incident Response
```

### Zero Trust Model

1. **Never Trust**: All requests authenticated
2. **Always Verify**: Continuous validation
3. **Least Privilege**: Minimal required access
4. **Assume Breach**: Detection and response ready

## Integration Patterns

### 1. Direct Integration

```python
# Python SDK
from docaiche_mcp import MCPClient

client = MCPClient(endpoint="...", credentials=...)
results = await client.search("query")
```

### 2. Proxy Pattern

```
AI Agent → Corporate Proxy → MCP Server → DocaiChe
```

### 3. Sidecar Pattern

```yaml
# Kubernetes sidecar
containers:
- name: app
  image: ai-agent:latest
- name: mcp-sidecar
  image: docaiche-mcp-proxy:latest
  ports:
  - containerPort: 8000
```

## Performance Optimization

### 1. Connection Pooling

- HTTP/2 multiplexing
- Persistent connections
- Connection reuse

### 2. Request Batching

```json
{
  "batch": [
    {"method": "search", "params": {...}},
    {"method": "collections", "params": {...}}
  ]
}
```

### 3. Response Streaming

- Server-sent events for real-time updates
- Chunked transfer encoding
- Progressive rendering

## Deployment Architecture

### Container Architecture

```
┌─────────────────────────────┐
│      Docker Container       │
│  ┌────────────────────┐     │
│  │   Python Runtime   │     │
│  └────────────────────┘     │
│  ┌────────────────────┐     │
│  │    MCP Server      │     │
│  └────────────────────┘     │
│  ┌────────────────────┐     │
│  │   Dependencies     │     │
│  └────────────────────┘     │
└─────────────────────────────┘
```

### Kubernetes Architecture

```yaml
Deployment
├── ReplicaSet (3 replicas)
├── HorizontalPodAutoscaler
├── Service (LoadBalancer)
├── ConfigMap (Configuration)
├── Secret (Credentials)
└── PodDisruptionBudget
```

## Monitoring Architecture

### Metrics Pipeline

```
Application Metrics
    │
    ▼
Prometheus Scraper
    │
    ▼
Prometheus Server
    │
    ▼
Grafana Dashboards
    │
    ▼
Alert Manager
```

### Logging Pipeline

```
Structured Logs (JSON)
    │
    ▼
Filebeat/Fluentd
    │
    ▼
Elasticsearch
    │
    ▼
Kibana
```

## Design Decisions

### 1. Why OAuth 2.1?

- Industry standard
- Extensible with Resource Indicators
- Strong security properties
- Wide client support

### 2. Why JSON-RPC 2.0?

- MCP specification requirement
- Simple and lightweight
- Batch request support
- Clear error handling

### 3. Why Streamable HTTP?

- Better performance than WebSocket for most use cases
- HTTP/2 multiplexing
- Works with existing infrastructure
- Progressive enhancement

### 4. Why FastAPI Integration?

- Leverage existing backend
- Consistent API surface
- Shared authentication
- Code reuse

## Future Architecture

### Planned Enhancements

1. **GraphQL Support**: Alternative query interface
2. **gRPC Transport**: For high-performance scenarios
3. **Event Sourcing**: Complete audit trail
4. **Multi-Region**: Global deployment
5. **ML Integration**: Smart caching and ranking

### Extension Points

1. **Custom Tools**: Plugin architecture
2. **Custom Resources**: Dynamic resource registration
3. **Custom Transports**: Protocol extensions
4. **Custom Security**: Pluggable auth providers

## Conclusion

The MCP architecture for DocaiChe is designed to be:

- **Scalable**: Horizontal scaling ready
- **Secure**: Defense in depth
- **Performant**: Optimized data flow
- **Maintainable**: Clear separation of concerns
- **Extensible**: Plugin architecture
- **Observable**: Comprehensive monitoring

This architecture supports the current requirements while providing flexibility for future enhancements.