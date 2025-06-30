# MCP Search Workflow Process Document

## Overview

This document describes the complete search workflow for the MCP (Model Context Protocol) system, including the integration of AnythingLLM for vector search, Text AI for decision making, and external search providers for comprehensive documentation retrieval.

## Core Components

1. **MCP Endpoint**: Interface for AI agents to request information
2. **SearchOrchestrator**: Central component managing the search workflow
3. **AnythingLLM**: Vector database for similarity search against indexed documents
4. **Text AI Model**: Decision-making component for relevance assessment and search strategies
5. **External Search Providers**: Configurable web search engines (Brave, Google, etc.)
6. **Content Extraction System**: Intelligent retrieval of documentation from web sources
7. **Ingestion Pipeline**: Process for adding new documentation to AnythingLLM

## Workflow Phases

### Phase 1: Request Handling

1. **Request Reception**
   - AI agent sends search request to MCP endpoint
   - Request contains query and optional parameters (response_type, technology focus, etc.)
   - MCP validates request and authentication (future)

2. **Query Understanding**
   - Text AI analyzes query to determine:
     - Query intent (information seeking, problem solving, etc.)
     - Technical domain
     - Expected answer type
     - Key concepts and entities
   - SearchOrchestrator normalizes query (cleaning, tokenization, stemming)

### Phase 2: Cache Check

1. **Cache Lookup**
   - Generate cache key from normalized query
   - Check Redis cache with circuit breaker pattern
   - If cache hit, retrieve results and proceed to evaluation
   - If cache miss or circuit open, proceed to vector search

### Phase 3: Vector Search

1. **Workspace Selection**
   - Identify relevant workspaces in AnythingLLM based on:
     - Technology mentioned in query
     - Workspace metadata
     - Previous search success patterns

2. **Parallel Search Execution**
   - Send query to selected workspaces (max 5 concurrent)
   - Each search has 2-second timeout
   - Collect results from successful searches
   - Handle partial failures gracefully

3. **Result Aggregation**
   - Combine results from all workspaces
   - Deduplicate by content hash
   - Apply initial relevance ranking

### Phase 4: Result Evaluation

1. **Relevance Assessment**
   - Text AI evaluates search results against original query
   - Determines overall relevance score (0-1)
   - Assesses whether results answer the query completely
   - Identifies any missing information

2. **Decision Point**
   - If results are highly relevant (score > 0.8), proceed to response formation
   - If results are partially relevant (score 0.4-0.8), attempt query refinement
   - If results are irrelevant (score < 0.4), proceed to external search

### Phase 5: Query Refinement (if needed)

1. **Refined Query Generation**
   - Text AI generates improved query based on:
     - Original query
     - Initial results
     - Missing information
     - Domain knowledge

2. **Secondary Vector Search**
   - Execute search with refined query
   - Evaluate results again
   - If improved, proceed to response formation
   - If still insufficient, proceed to external search

### Phase 6: External Search (if needed)

1. **Search Provider Selection**
   - Text AI selects appropriate search provider based on:
     - Query characteristics
     - Domain specificity
     - Provider performance history
     - Rate limit considerations

2. **Search Query Optimization**
   - Text AI generates optimized search query for selected provider
   - Adds specific terms, quotes, or operators as appropriate
   - Focuses query on documentation sources

3. **Search Execution**
   - Send optimized query to selected provider
   - Process search results (URLs, snippets)
   - Rank by estimated relevance

4. **Content Retrieval**
   - For top-ranked results (up to 5):
     - Fetch full content, prioritizing:
       1. GitHub raw content
       2. Official documentation
       3. Technical blogs/articles
     - Handle different content types (HTML, Markdown, PDF)
     - Extract main content, removing navigation/ads

5. **Content Processing**
   - Text AI extracts relevant sections based on query
   - Preserves code examples and formatting
   - Maintains necessary context
   - Removes irrelevant information

### Phase 7: Knowledge Ingestion

1. **Content Preparation**
   - Format extracted content for AnythingLLM
   - Add metadata (source, timestamp, relevance)
   - Assign to appropriate workspace(s)

2. **Ingestion Process**
   - Submit content to AnythingLLM ingestion pipeline
   - Generate embeddings
   - Index in vector database
   - Update workspace metadata

3. **Learning Loop**
   - Text AI identifies knowledge gaps
   - Prioritizes content for future ingestion
   - Updates search heuristics based on outcomes

### Phase 8: Response Formation

1. **Response Type Selection**
   - Check requested response_type parameter:
     - "raw": Provide relevant documentation sections
     - "answer": Generate AI-synthesized answer
     - Default based on query characteristics if not specified

2. **Response Generation**
   - For "raw" responses:
     - Format documentation with proper attribution
     - Maintain code formatting
     - Include source links

   - For "answer" responses:
     - Text AI synthesizes information into direct answer
     - Includes code examples if applicable
     - Cites sources
     - Ensures completeness

3. **Metadata Inclusion**
   - Add performance metrics (search time, sources used)
   - Include confidence score
   - Add recommendations for related queries

### Phase 9: Result Caching

1. **Cache Storage**
   - If results are high quality, store in Redis cache
   - Set appropriate TTL based on content type:
     - Technical documentation: 1 week
     - Recent technology: 1 day
     - General information: 1 month

2. **Cache Management**
   - Apply circuit breaker pattern for resilience
   - Implement cache eviction policies
   - Track cache hit rates for optimization

### Phase 10: Response Delivery

1. **Final Packaging**
   - Format according to MCP protocol
   - Include required metadata
   - Add debugging information if requested

2. **Delivery to Agent**
   - Send response through MCP endpoint
   - Log transaction completion
   - Update performance metrics

## Error Handling

### Timeout Management
- Overall search timeout: 30 seconds
- Per-workspace timeout: 2 seconds
- External search timeout: 5 seconds
- Content retrieval timeout: 10 seconds

### Fallback Mechanisms
1. **Vector Search Failures**
   - Return partial results if some workspaces succeed
   - Proceed to external search if all workspaces fail

2. **External Search Failures**
   - Try alternative providers if primary fails
   - Degrade gracefully to best available information
   - Include failure information in response

3. **Text AI Failures**
   - Implement simpler heuristics as fallback
   - Use default strategies when AI is unavailable
   - Log failures for improvement

## Performance Optimization

1. **Concurrency Control**
   - Limit to 5 parallel workspace searches
   - Limit to 3 parallel content retrievals
   - Implement connection pooling

2. **Caching Strategy**
   - Multi-level caching (results, embeddings, content)
   - Adaptive TTL based on content type
   - Circuit breaker pattern for resilience

3. **Resource Management**
   - Text AI token usage optimization
   - Search provider quota management
   - Adaptive timeout based on query complexity

## Observability

1. **Logging Points**
   - Query reception and normalization
   - Cache operations
   - Search decisions and execution
   - AI evaluations
   - External content retrieval
   - Response generation

2. **Metrics Collection**
   - Search latency by phase
   - Cache hit rates
   - Result relevance scores
   - External provider performance
   - Knowledge gap identification rate

3. **Distributed Tracing**
   - End-to-end request tracking
   - Component-level performance analysis
   - Bottleneck identification

## Implementation Considerations

1. **Text AI Integration**
   - Ensure prompts stay within context limits
   - Balance response quality with latency
   - Implement retries for transient failures
   - Version prompt templates for iteration

2. **AnythingLLM Optimization**
   - Fine-tune embedding models for domain
   - Optimize workspace organization
   - Implement regular reindexing for quality

3. **External Search Providers**
   - Implement provider-specific query optimizations
   - Respect rate limits and quotas
   - Track performance metrics per provider
   - Implement cost management

4. **Security Measures**
   - Sanitize all external content
   - Validate and authenticate requests (future)
   - Implement rate limiting per client
   - Monitor for abuse patterns

## Future Enhancements

1. **Personalization**
   - User-specific relevance models
   - Organization-specific knowledge prioritization
   - Learning from user feedback

2. **Advanced Content Processing**
   - Multi-modal content understanding (code, diagrams)
   - Semantic chunking for better context
   - Cross-document knowledge synthesis

3. **Proactive Knowledge Acquisition**
   - Automated discovery of relevant documentation
   - Continuous ingestion of high-value sources
   - Knowledge gap analysis and filling

4. **Federated Search**
   - Integration with organization-specific knowledge bases
   - Secure access to private repositories
   - Cross-organization knowledge sharing with permissions