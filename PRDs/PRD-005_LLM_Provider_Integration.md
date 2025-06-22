# PRD-005: LLM Provider Integration Layer

## Overview
Specifies a unified client for interacting with multiple Large Language Model (LLM) providers. Abstracts provider differences, manages structured prompting, parses JSON responses, and handles errors and failover.

## Technical Boundaries
- Called by the AI Decision Engine.
- Makes outbound HTTP requests to configured LLM providers (Ollama, OpenAI).
- Depends on Configuration Management for provider details, API keys, and prompt templates.

## Success Criteria
- Seamless switching between providers.
- Reliable JSON parsing from LLM output.
- Correct failover logic and error handling.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads provider config and prompt templates |
| PRD-002: Database & Caching Layer | Caches LLM responses |
| PRD-009: Search Orchestration Engine | Calls evaluation and enrichment methods |

## Cross-References
- Uses [`AIConfig`](PRD-003_Config_Mgmt_System.md), [`OllamaConfig`](PRD-003_Config_Mgmt_System.md), [`OpenAIConfig`](PRD-003_Config_Mgmt_System.md) from [Configuration Management](PRD-003_Config_Mgmt_System.md).
- Caches responses using [`CacheManager`](PRD-002_DB_and_Caching_Layer.md) from [Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md).
- Called by [Search Orchestration Engine](PRD-009_search_orchestration_engine.md) for search evaluation and enrichment.
- Prompt templates referenced in this PRD are stored as files in the configuration directory.

## Prompt Templates

### 1. evaluation.prompt

**Purpose**: Evaluates the sufficiency and quality of search results against a user query to determine if enrichment is needed.

**Input Variables**:
- `query`: The original user search query
- `results`: List of search results with titles, snippets, and URLs
- `context`: Additional context about the search domain or requirements

**Prompt Template**:
```
You are an expert information analyst. Evaluate whether the provided search results sufficiently answer the user's query.

USER QUERY: {query}

SEARCH RESULTS:
{results}

CONTEXT: {context}

Analyze the search results and provide a structured evaluation. Consider:
1. Coverage: Do the results comprehensively address the query?
2. Quality: Are the sources authoritative and relevant?
3. Completeness: Are there obvious gaps or missing information?
4. Recency: Is the information current enough for the query?

Provide your assessment as a JSON object with the following structure:
{{
  "model_version": "1.0.0",
  "sufficiency_score": <float between 0.0 and 1.0>,
  "confidence": <float between 0.0 and 1.0>,
  "missing_aspects": [<list of strings describing missing information>],
  "should_enrich": <boolean>,
  "reasoning": "<detailed explanation of your assessment>",
  "created_at": "<current UTC timestamp>"
}}

Be precise and objective in your evaluation.
```

**Expected Output Schema**: [`EvaluationResult`](PRD-005_LLM_Provider_Integration.md:266)

**Example Usage**:
```python
evaluation_prompt = prompt_manager.format_template(
    "evaluation.prompt",
    query="How to implement OAuth2 in FastAPI",
    results=[{"title": "FastAPI OAuth2", "snippet": "...", "url": "..."}],
    context="API development documentation search"
)
```

---

### 2. strategy.prompt

**Purpose**: Generates a strategic enrichment plan for knowledge gaps identified in search results.

**Input Variables**:
- `original_query`: The original user search query
- `missing_aspects`: List of identified missing information
- `current_results`: Summary of existing search results
- `domain`: The subject domain or technology area

**Prompt Template**:
```
You are a knowledge enrichment strategist. Based on the identified gaps in search results, create a targeted enrichment strategy.

ORIGINAL QUERY: {original_query}

MISSING ASPECTS:
{missing_aspects}

CURRENT RESULTS SUMMARY:
{current_results}

DOMAIN: {domain}

Create an enrichment strategy that identifies:
1. High-value repositories to search
2. Specific search queries to fill gaps
3. Prioritized information sources
4. Expected value of the enrichment effort

Provide your strategy as a JSON object with the following structure:
{{
  "model_version": "1.0.0",
  "target_repositories": [
    {{
      "owner": "<repository owner>",
      "repo": "<repository name>",
      "path": "<specific path if applicable>",
      "priority": <float between 0.0 and 1.0>
    }}
  ],
  "search_queries": [<list of specific search terms/phrases>],
  "priority_sources": [<ordered list from: "github", "official_docs", "web">],
  "estimated_value": <float between 0.0 and 1.0>,
  "created_at": "<current UTC timestamp>"
}}

Focus on actionable, specific targets that will maximize information gain.
```

**Expected Output Schema**: [`EnrichmentStrategy`](PRD-005_LLM_Provider_Integration.md:281)

**Example Usage**:
```python
strategy_prompt = prompt_manager.format_template(
    "strategy.prompt",
    original_query="FastAPI middleware implementation",
    missing_aspects=["error handling", "async middleware patterns"],
    current_results="Basic middleware setup found",
    domain="Python web frameworks"
)
```

---

### 3. quality.prompt

**Purpose**: Assesses the quality and relevance of content to determine if it should be stored in the knowledge base.

**Input Variables**:
- `content`: The content to be assessed (text, code, documentation)
- `source_url`: URL of the content source
- `query_context`: The original search context that led to this content
- `content_metadata`: Additional metadata about the content (author, date, etc.)

**Prompt Template**:
```
You are a content quality assessor. Evaluate the provided content for relevance, quality, and value for storage in a knowledge base.

CONTENT:
{content}

SOURCE URL: {source_url}

QUERY CONTEXT: {query_context}

CONTENT METADATA:
{content_metadata}

Assess the content based on:
1. Relevance: How well does this content address the search context?
2. Quality: Is the content well-written, accurate, and authoritative?
3. Uniqueness: Does this provide unique value not found elsewhere?
4. Completeness: Is the content complete and self-contained?
5. Currency: Is the content current and not outdated?

Classify the content type and provide your assessment as a JSON object:
{{
  "model_version": "1.0.0",
  "relevance_score": <float between 0.0 and 1.0>,
  "quality_score": <float between 0.0 and 1.0>,
  "should_store": <boolean>,
  "content_type": "<one of: tutorial, reference, guide, example, api, other>",
  "confidence": <float between 0.0 and 1.0>,
  "created_at": "<current UTC timestamp>"
}}

Be objective and consider long-term value for future searches.
```

**Expected Output Schema**: [`QualityAssessment`](PRD-005_LLM_Provider_Integration.md:289)

**Example Usage**:
```python
quality_prompt = prompt_manager.format_template(
    "quality.prompt",
    content="# FastAPI Middleware Guide\n\nMiddleware in FastAPI...",
    source_url="https://github.com/example/fastapi-guide",
    query_context="FastAPI middleware implementation patterns",
    content_metadata={"author": "fastapi-team", "last_updated": "2024-01-15"}
)
```

---

### Template Validation Requirements

All prompt templates must:
1. Include the `model_version` field in expected JSON output for compatibility tracking
2. Use consistent variable naming conventions with `{variable_name}` syntax
3. Specify expected data types and ranges for numeric fields
4. Include the `created_at` timestamp field for audit trails
5. Align output schemas exactly with the Pydantic models defined in this PRD
6. Provide clear instructions for objective, structured analysis
7. Include example values or ranges to guide LLM responses

### Template Storage and Management

Templates are stored as individual `.prompt` files in the configuration directory and loaded by the [`PromptManager`](PRD-005_LLM_Provider_Integration.md:307) utility class. Each template file contains only the prompt text with variable placeholders, while metadata and schemas are defined in this PRD.

## Circuit Breaker Implementation

**Service Category**: Mixed - OpenAI (External API), Ollama (Internal Service)
**Rationale**: OpenAI is an external API requiring higher tolerance due to rate limiting and variable response times, while Ollama runs as a local Docker container with predictable behavior and faster recovery capabilities. Each provider requires different circuit breaker configurations based on their deployment model and reliability characteristics.

```python
from circuitbreaker import circuit
import asyncio

class LLMProviderClient:
    def __init__(self, config: AIConfig):
        # OpenAI (External API) - Higher tolerance for rate limits and external issues
        self.openai_circuit_breaker = circuit(
            failure_threshold=5,
            recovery_timeout=300,
            timeout=30,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
        )
        
        # Ollama (Internal Service) - Lower tolerance for predictable local service
        self.ollama_circuit_breaker = circuit(
            failure_threshold=3,
            recovery_timeout=60,
            timeout=30,
            expected_exception=(aiohttp.ClientError)
        )
    
    @circuit_breaker
    async def _make_llm_request(self, provider: str, prompt: str, **kwargs):
        # Protected LLM request with timeout and retry logic
        pass
```

## Data Models

```python
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class EvaluationResult(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    sufficiency_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    missing_aspects: List[str]
    should_enrich: bool
    reasoning: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RepositoryTarget(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    owner: str
    repo: str
    path: str
    priority: float

class EnrichmentStrategy(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    target_repositories: List[RepositoryTarget]
    search_queries: List[str]
    priority_sources: List[Literal["github", "official_docs", "web"]]
    estimated_value: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QualityAssessment(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    should_store: bool
    content_type: Literal["tutorial", "reference", "guide", "example", "api", "other"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| LLM-001 | Create BaseLLMProvider abstract class with async generate_structured |
| LLM-002 | Implement OllamaProvider class (POST to /api/generate) |
| LLM-003 | Implement OpenAIProvider class (uses openai.ChatCompletion.acreate) |
| LLM-004 | Implement LLMProviderClient class, instantiates correct provider |
| LLM-005 | Create PromptManager utility for loading/formatting templates |
| LLM-006 | Implement robust JSON parsing utility in BaseLLMProvider |
| LLM-007 | Implement failover logic in LLMProviderClient |
| LLM-008 | Implement Redis-based cache for LLM responses |
| LLM-009 | Implement structured logging after every LLM interaction |
| LLM-010 | Write unit tests for JSON parsing logic |

## Integration Contracts
- Accepts Python primitives to format into prompt templates.
- Returns validated Pydantic models parsed from LLM responses.
- Raises specific errors for parsing or provider failures.

## Summary Tables

### Endpoints Table

| Method | Endpoint/Action         | Description                        |
|--------|------------------------|------------------------------------|
| POST   | /api/generate (Ollama) | Generates LLM response             |
| POST   | OpenAI API             | Generates LLM response             |

### Data Models Table

| Model Name         | Description                        | Used In                         |
|--------------------|------------------------------------|---------------------------------|
| EvaluationResult   | Search result evaluation           | evaluate_search_results         |
| RepositoryTarget   | Target repo for enrichment         | generate_enrichment_strategy    |
| EnrichmentStrategy | Enrichment strategy                | generate_enrichment_strategy    |
| QualityAssessment  | Content quality assessment         | assess_content_quality          |

### Implementation Tasks Table
(see Implementation Tasks above)

---