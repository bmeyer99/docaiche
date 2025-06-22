# Circuit Breaker Configuration Standards

## Overview
This document defines the standardized circuit breaker configurations used across all PRDs in the DocAI Cache system. These standards ensure consistent reliability behavior and predictable system responses.

## Service Categories and Standards

### 1. External APIs
**Services**: GitHub API, OpenAI API, External LLM Providers  
**Configuration**:
- `failure_threshold=5`
- `recovery_timeout=300` (5 minutes)
- `timeout=30` seconds

**Rationale**: External APIs have rate limiting, variable response times, and occasional outages. Higher tolerance prevents unnecessary circuit opening due to temporary issues, while longer recovery accommodates provider-side rate limit resets and service restoration.

**Applied to**:
- [`PRD-005: LLM Provider Integration`](PRD-005_LLM_Provider_Integration.md) (OpenAI, Ollama)
- [`PRD-006: GitHub Repository Client`](PRD-006_Github_repo_client.md) (GitHub API)
- [`PRD-003: Configuration Management`](PRD-003_Config_Mgmt_System.md) (OpenAIConfig, OllamaConfig, GitHubConfig)

### 2. Internal Services
**Services**: AnythingLLM Integration  
**Configuration**:
- `failure_threshold=3`
- `recovery_timeout=60` (1 minute)
- `timeout=30` seconds

**Rationale**: Internal services have predictable behavior and faster recovery capabilities. Medium tolerance with shorter recovery allows for quick failover while maintaining reasonable availability without overwhelming internal infrastructure.

**Applied to**:
- [`PRD-004: AnythingLLM Integration`](PRD-004_AnythingLLM_Integration.md) (AnythingLLM API)
- [`PRD-003: Configuration Management`](PRD-003_Config_Mgmt_System.md) (AnythingLLMConfig)

### 3. Web Scraping
**Services**: Web Content Scraping  
**Configuration**:
- `failure_threshold=3`
- `recovery_timeout=120` (2 minutes)
- `timeout=15` seconds

**Rationale**: Web scraping targets have high variability in response times, availability, and anti-scraping measures. Lower tolerance prevents wasting resources on unreliable sites, while moderate recovery timeout allows for temporary issues to resolve. Shorter timeout prevents hanging on slow responses.

**Applied to**:
- [`PRD-007: Web Scraping Client`](PRD-007_web_scraping_client.md) (Web content scraping)
- [`PRD-003: Configuration Management`](PRD-003_Config_Mgmt_System.md) (ScrapingConfig)

## Implementation Guidelines

### Standard Configuration Pattern
```python
from circuitbreaker import circuit

class ServiceClient:
    def __init__(self, config):
        self.circuit_breaker = circuit(
            failure_threshold=<category_threshold>,
            recovery_timeout=<category_timeout>,
            timeout=<category_request_timeout>,
            expected_exception=(<appropriate_exceptions>)
        )
    
    @circuit_breaker
    async def _make_request(self, **kwargs):
        # Protected request implementation
        pass
```

### Exception Handling
- **External APIs**: `(aiohttp.ClientError, aiohttp.ClientResponseError, asyncio.TimeoutError)`
- **Internal Services**: `(aiohttp.ClientError)`
- **Web Scraping**: `(aiohttp.ClientError, asyncio.TimeoutError)`

## Validation Checklist

When implementing or reviewing circuit breaker configurations:

- [ ] Service is categorized correctly (External API, Internal Service, Web Scraping)
- [ ] Configuration values match the category standards
- [ ] Timeout value is included in configuration
- [ ] Appropriate exceptions are specified
- [ ] Circuit breaker decorates the main request method
- [ ] Documentation includes service category and rationale

## Change History

| Date | Change | Rationale |
|------|--------|-----------|
| 2025-06-22 | Initial standardization | Resolved inconsistent configurations across PRD-004, PRD-005, PRD-006, PRD-007 |
| 2025-06-22 | Added timeout configurations | Standardized request timeout behavior across all services |

## Future Considerations

- Monitor circuit breaker metrics to validate threshold effectiveness
- Consider adaptive thresholds based on service-specific SLA requirements
- Evaluate need for additional service categories as system grows
- Review configurations quarterly for optimization opportunities