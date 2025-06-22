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
- Uses `AIConfig`, `OllamaConfig`, `OpenAIConfig` from PRD-003.
- Caches responses using `CacheManager` from PRD-002.
- Called by PRD-009 for search evaluation and enrichment.
- Prompt templates referenced in this PRD are stored as files.

## Prompt Templates

| Template Name      | Description                                 |
|--------------------|---------------------------------------------|
| evaluation.prompt  | Evaluates sufficiency and quality of results|
| strategy.prompt    | Generates enrichment strategy               |
| quality.prompt     | Assesses content quality                    |

## Circuit Breaker Implementation

```python
from circuitbreaker import circuit
import asyncio

class LLMProviderClient:
    def __init__(self, config: AIConfig):
        self.circuit_breaker = circuit(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
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