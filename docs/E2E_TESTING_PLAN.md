# End-to-End Testing Plan for MCP Implementation

## Overview

This document outlines the comprehensive E2E testing plan for the DocaiChe MCP implementation. The testing will be conducted through the admin-ui `/mcp` endpoint to ensure full integration testing of all services working together.

## Testing Objectives

1. **Complete Tool Coverage**: Test every MCP tool with various scenarios
2. **Cache Validation**: Verify caching behavior for repeated queries
3. **Integration Validation**: Ensure all services communicate correctly
4. **Performance Monitoring**: Track latency through the pipeline
5. **Error Handling**: Test edge cases and error scenarios
6. **Security Validation**: Verify authentication and authorization

## MCP Tools and Resources Inventory

### Tools (Active Operations)
1. **docaiche/search** - Search documentation with intelligent ranking
2. **docaiche/ingest** - Ingest new documentation with consent
3. **docaiche/feedback** - Submit feedback on search results or documents

### Resources (Data Access)
1. **docaiche://collections** - List available documentation collections
2. **docaiche://status** - Get system health and metrics

## Testing Environment Setup

### Prerequisites
1. Admin UI running and accessible
2. MCP server integrated with FastAPI backend
3. Test data prepared for ingestion
4. Monitoring dashboards accessible
5. Log aggregation configured

### Test Data
```
Test Query 1: "quantum computing algorithms" (Unknown query - not in cache)
Test Query 2: "authentication OAuth2" (May exist in system)
Test Query 3: "machine learning tensorflow" (Complex multi-term query)
Test Document: A new technical document about "Quantum Computing Basics"
```

## Detailed Test Plan

### Phase 1: Authentication and Initial Setup

#### Test 1.1: OAuth Token Acquisition
```
Endpoint: POST /oauth/token
Purpose: Get access token for MCP operations
Expected: Valid JWT token with correct scopes
Tracing: Monitor auth service logs
```

#### Test 1.2: Token Validation
```
Purpose: Verify token is accepted by MCP endpoints
Expected: 200 OK with valid token, 401 with invalid
Tracing: Check JWT validation logs
```

### Phase 2: Resource Testing

#### Test 2.1: Get Collections
```
Tool: docaiche://collections
Purpose: List all available documentation collections
Expected: JSON array of collections with metadata
Tracing:
- Request flow through adapter
- FastAPI endpoint hit
- Response formatting
```

#### Test 2.2: Get System Status
```
Tool: docaiche://status
Purpose: Check system health and component status
Expected: Health status with all components
Tracing:
- Health check execution
- Metric aggregation
- Cache statistics
```

### Phase 3: Search Tool Testing

#### Test 3.1: Unknown Query (Cache Miss)
```
Tool: docaiche/search
Query: "quantum computing algorithms"
Purpose: Test new query that's not in cache
Expected:
- Cache miss
- External search execution
- Results returned and cached
Tracing:
- Cache lookup (miss)
- Search engine invocation
- Result caching
- Pipeline latency
```

#### Test 3.2: Repeated Query (Cache Hit)
```
Tool: docaiche/search
Query: "quantum computing algorithms" (same as 3.1)
Purpose: Verify cache hit behavior
Expected:
- Cache hit
- No external search
- Faster response time
Tracing:
- Cache lookup (hit)
- Cache retrieval time
- No search engine call
```

#### Test 3.3: Known Query Testing
```
Tool: docaiche/search
Query: "authentication OAuth2"
Purpose: Test query that may have existing results
Expected:
- Relevant results
- Proper ranking
- Metadata included
Tracing:
- Full pipeline execution
- Relevance scoring
```

#### Test 3.4: Complex Query
```
Tool: docaiche/search
Query: "machine learning tensorflow gpu optimization"
Purpose: Test multi-term complex query
Expected:
- Relevant results
- Proper term handling
- Performance acceptable
```

#### Test 3.5: Edge Cases
```
Queries:
- Empty query: ""
- Special characters: "test@#$%"
- Very long query: 500+ characters
- Injection attempt: "'; DROP TABLE--"
Expected: Proper error handling and validation
```

### Phase 4: Ingest Tool Testing

#### Test 4.1: Document Ingestion with Consent
```
Tool: docaiche/ingest
Document: Quantum Computing Basics article
Purpose: Add new document to collection
Expected:
- Consent validated
- Document indexed
- Available in search
Tracing:
- Consent validation
- Content validation
- Indexing pipeline
- Cache invalidation
```

#### Test 4.2: Search for Ingested Document
```
Tool: docaiche/search
Query: "quantum computing basics"
Purpose: Verify newly ingested document is searchable
Expected:
- New document in results
- Proper ranking
- Fresh index
```

#### Test 4.3: Ingest Error Cases
```
Scenarios:
- Missing consent
- Invalid metadata
- Malformed content
- Duplicate URI
Expected: Appropriate error messages
```

### Phase 5: Feedback Tool Testing

#### Test 5.1: Search Result Feedback
```
Tool: docaiche/feedback
Type: search_relevance
Purpose: Rate search result quality
Expected:
- Feedback recorded
- Audit log entry
- Analytics updated
Tracing:
- Feedback processing
- Audit logging
- Analytics pipeline
```

#### Test 5.2: Document Quality Feedback
```
Tool: docaiche/feedback
Type: doc_quality
Purpose: Rate document quality
Expected:
- Feedback linked to document
- Metrics updated
```

#### Test 5.3: General Feedback
```
Tool: docaiche/feedback
Type: general
Purpose: Submit general system feedback
Expected:
- Feedback stored
- Available for analysis
```

### Phase 6: Performance and Load Testing

#### Test 6.1: Concurrent Requests
```
Scenario: 10 concurrent search requests
Purpose: Test system under load
Metrics:
- Response times
- Error rates
- Resource usage
```

#### Test 6.2: Rate Limiting
```
Scenario: Exceed rate limits
Purpose: Verify rate limiting works
Expected:
- 429 responses after limit
- Proper headers
- Recovery after cooldown
```

### Phase 7: Security Testing

#### Test 7.1: Invalid Authentication
```
Scenarios:
- No token
- Expired token
- Invalid signature
- Wrong scopes
Expected: Proper 401/403 responses
```

#### Test 7.2: Authorization Boundaries
```
Scenarios:
- Access without required scope
- Cross-tenant access attempt
Expected: Proper authorization enforcement
```

### Phase 8: Integration Testing

#### Test 8.1: Full Workflow
```
Flow:
1. Get collections
2. Search for topic
3. Ingest related document
4. Search again (verify new doc)
5. Submit feedback
6. Check status
Purpose: Validate complete user journey
```

#### Test 8.2: Error Recovery
```
Scenarios:
- Backend service down
- Database connection lost
- Cache unavailable
Expected: Graceful degradation
```

## Monitoring and Tracing Plan

### Log Points to Monitor

1. **Admin UI Logs**
   - Request reception
   - MCP client initialization
   - Response handling

2. **MCP Server Logs**
   - Request processing
   - Tool execution
   - Cache operations
   - Error handling

3. **FastAPI Backend Logs**
   - Endpoint hits
   - Database queries
   - Search operations

4. **Cache Logs**
   - Hit/miss ratios
   - Eviction events
   - Size changes

### Metrics to Track

1. **Latency Metrics**
   - Total request time
   - Cache lookup time
   - Search execution time
   - Database query time

2. **Success Metrics**
   - Success/failure rates
   - Cache hit rates
   - Error types and frequencies

3. **Resource Metrics**
   - Memory usage
   - CPU utilization
   - Connection pool usage

### Trace Points

```
Request Flow:
Admin UI → MCP Client → MCP Server → Transport Layer → 
Protocol Handler → Tool/Resource → Adapter → FastAPI → 
Database/Search → Response Path
```

## Test Execution Order

1. **Setup Phase**
   - Verify all services running
   - Clear caches
   - Reset test data

2. **Authentication Tests** (Phase 1)
   - Establish valid session

3. **Resource Tests** (Phase 2)
   - Verify basic connectivity

4. **Search Tests** (Phase 3)
   - Primary functionality validation
   - Cache behavior verification

5. **Ingest Tests** (Phase 4)
   - Data modification capabilities

6. **Feedback Tests** (Phase 5)
   - User interaction features

7. **Performance Tests** (Phase 6)
   - System limits and behavior

8. **Security Tests** (Phase 7)
   - Security boundary validation

9. **Integration Tests** (Phase 8)
   - Complete workflow validation

## Success Criteria

1. **Functional Success**
   - All tools respond correctly
   - Cache behavior as expected
   - Error handling appropriate

2. **Performance Success**
   - Search latency < 200ms (cached)
   - Search latency < 2s (uncached)
   - Ingest latency < 5s

3. **Security Success**
   - No unauthorized access
   - Proper error messages
   - Audit trail complete

4. **Integration Success**
   - All services communicate
   - Data consistency maintained
   - Graceful error handling

## Test Report Template

```markdown
## E2E Test Results

### Test Environment
- Date: [Date]
- Version: [Version]
- Environment: [Dev/Staging/Prod]

### Test Summary
- Total Tests: X
- Passed: X
- Failed: X
- Skipped: X

### Detailed Results
[Per test results]

### Performance Metrics
[Latency, throughput, resource usage]

### Issues Found
[List of issues with severity]

### Recommendations
[Next steps and improvements]
```

## Next Steps

1. Review and approve this test plan
2. Prepare test environment
3. Execute tests systematically
4. Document all findings
5. Create issues for any bugs
6. Performance optimization based on results

This comprehensive testing plan ensures thorough validation of the MCP implementation with extensive tracing and monitoring to identify any integration issues.