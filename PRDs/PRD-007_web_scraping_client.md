# PRD-007: Web Scraping Client

## Overview
Specifies the web scraping client responsible for fetching and extracting content from HTML documentation websites. Handles HTTP requests, HTML parsing, markdown extraction, and robots.txt compliance.

## Technical Boundaries
- Invoked by Content Acquisition Engine for non-repository sources.
- Makes outbound HTTP requests to public websites.
- Depends on Configuration Management for rate limits and user-agent.

## Success Criteria
- Extracts clean, readable markdown from major documentation sites.
- Strictly adheres to robots.txt and rate limits.
- Handles network and HTTP errors gracefully.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads scraping config and user-agent |
| PRD-008: Content Processing Pipeline | Processes scraped content |
| PRD-010: Knowledge Enrichment System | Triggers scraping for enrichment |

## Cross-References
- Uses `ScrapingConfig` from PRD-003.
- Called by PRD-010 for enrichment.
- Provides `ScrapedContent` to PRD-008 for processing.

## Client Interface

```python
from typing import List, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime
from circuitbreaker import circuit

class WebScrapingClient:
    def __init__(self, config: ScrapingConfig):
        self.circuit_breaker = circuit(
            failure_threshold=3,
            recovery_timeout=120,  # 2 minutes for web scraping
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
        )
    
    @circuit_breaker
    async def _make_web_request(self, url: str, **kwargs): ...
    async def is_url_allowed(self, url: str) -> bool: ...
    async def scrape_page(self, url: str) -> Optional[ScrapedContent]: ...
    async def extract_links(self, page_url: str, base_url: str) -> Set[str]: ...

class ScrapedContent(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    url: str
    title: str
    content_markdown: str
    word_count: int
    headings: List[str]
    links: Set[str]
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
```

## Error Response Handling

Web scraping operations follow standardized error patterns:

| HTTP Status | Internal Error Code | Description |
|-------------|-------------------|-------------|
| 403 | WEB_SCRAPING_FORBIDDEN | robots.txt disallows scraping |
| 404 | WEB_CONTENT_NOT_FOUND | Page not found |
| 429 | WEB_RATE_LIMITED | Rate limit exceeded |
| 500+ | WEB_SERVER_ERROR | Target server issues |
| Timeout | WEB_SCRAPING_TIMEOUT | Request timeout exceeded |

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| WS-001  | Implement WebScrapingClient with aiohttp.ClientSession |
| WS-002  | Implement robots.txt parsing logic and is_url_allowed |
| WS-003  | Implement scrape_page method (calls is_url_allowed, fetches HTML) |
| WS-004  | Use BeautifulSoup4 for HTML parsing and element removal |
| WS-005  | Convert cleaned HTML to markdown using markdownify |
| WS-006  | Implement link extraction logic |
| WS-007  | Enforce rate_limit_delay_seconds between requests |
| WS-008  | Add error handling for network/HTTP errors |
| WS-009  | Write unit tests for content extraction logic |
| WS-010  | Implement extract_links utility for efficient crawling |

## Integration Contracts
- Accepts a URL string to scrape.
- Returns a validated ScrapedContent model or None.
- Logs warnings for non-critical errors.

## Summary Tables

### Methods Table

| Method Name      | Description                                 | Returns           |
|------------------|---------------------------------------------|-------------------|
| is_url_allowed   | Checks robots.txt for scraping permission   | bool              |
| scrape_page      | Scrapes and extracts markdown content       | ScrapedContent    |
| extract_links    | Extracts same-origin links from a page      | Set[str]          |

### Data Models Table

| Model Name      | Description                       | Used In Method(s)                |
|-----------------|-----------------------------------|----------------------------------|
| ScrapedContent  | Extracted content and metadata    | scrape_page                      |

### Implementation Tasks Table
(see Implementation Tasks above)

---