# PRD-006: GitHub Repository Client

## Overview
Specifies the client for interacting with the GitHub REST API. Discovers documentation repositories, lists file contents, and downloads files. Handles authentication, rate limiting, and error handling.

## Technical Boundaries
- Called by Content Acquisition Engine.
- Makes outbound HTTP requests to GitHub API.
- Depends on Configuration Management for API keys.
- Uses Database Layer for technology-to-repository mappings.

## Success Criteria
- Downloads all markdown files from a specified repository's documentation folder.
- Adheres to GitHub API rate limits.
- Handles common errors gracefully.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads GitHub API config |
| PRD-002: Database & Caching Layer | Stores technology mappings, caches file listings |
| PRD-008: Content Processing Pipeline | Processes downloaded files |
| PRD-010: Knowledge Enrichment System | Triggers bulk imports and enrichment |

## Cross-References
- Uses `DatabaseManager` from PRD-002 for technology mappings.
- Caches file listings using `CacheManager` from PRD-002.
- Called by PRD-010 for enrichment and bulk import.
- Provides files to PRD-008 for processing.

## Client Interface

```python
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from circuitbreaker import circuit

class GitHubClient:
    def __init__(self, config: GitHubConfig, db_manager: DatabaseManager):
        self.circuit_breaker = circuit(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes for GitHub API
            expected_exception=(aiohttp.ClientError, aiohttp.ClientResponseError)
        )
    
    @circuit_breaker
    async def _make_github_request(self, endpoint: str, **kwargs): ...
    async def get_rate_limit_status(self) -> RateLimitStatus: ...
    async def find_repo_for_technology(self, technology: str) -> Optional[RepositoryInfo]: ...
    async def list_files_recursively(self, owner: str, repo: str, path: str, file_patterns: List[str]) -> List[FileInfo]: ...
    async def download_file_content(self, owner: str, repo: str, file_path: str) -> Optional[FileContent]: ...

class RateLimitStatus(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    limit: int
    remaining: int
    reset_timestamp: datetime
    used: int

class RepositoryInfo(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    owner: str
    repo: str
    docs_path: str
    file_patterns: List[str]

class FileInfo(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    path: str
    name: str
    type: str
    size: int
    sha: str
    download_url: Optional[str]

class FileContent(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    path: str
    content: str
    sha: str
```

## Error Response Handling

All GitHub API calls return standardized error responses following [`ProblemDetail`](PRD-001_HTTP_API_Foundation.md:51) format:

| GitHub Status | Internal Error Code | Description |
|---------------|-------------------|-------------|
| 403 (Rate Limited) | GITHUB_RATE_LIMITED | Rate limit exceeded |
| 404 | GITHUB_NOT_FOUND | Repository or file not found |
| 401 | GITHUB_AUTH_FAILED | Authentication failed |
| 500+ | GITHUB_SERVER_ERROR | GitHub server issues |

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| GH-001  | Implement GitHubClient with aiohttp.ClientSession |
| GH-002  | Implement get_rate_limit_status method |
| GH-003  | Implement find_repo_for_technology method |
| GH-004  | Implement list_files_recursively method |
| GH-005  | Implement download_file_content method |
| GH-006  | Integrate rate-limiting check within client |
| GH-007  | Implement comprehensive error handling for API responses |
| GH-008  | Implement Redis cache for file listings |
| GH-009  | Write unit tests for all methods |
| GH-010  | Integrate get_rate_limit_status into /api/v1/health endpoint |

## Integration Contracts
- Accepts a technology string to identify repository.
- Returns lists of FileInfo and FileContent objects.
- Raises custom exceptions for errors.

## Summary Tables

### Endpoints Table

| Method | Endpoint/Action         | Description                        |
|--------|------------------------|------------------------------------|
| GET    | /rate_limit            | Checks GitHub API rate limit       |
| GET    | /repos/{owner}/{repo}  | Lists repo content                 |
| GET    | /repos/{owner}/{repo}/contents/{path} | Gets file/directory content |

### Data Models Table

| Model Name      | Description                       | Used In Method(s)                |
|-----------------|-----------------------------------|----------------------------------|
| RateLimitStatus | GitHub API rate limit info         | get_rate_limit_status            |
| RepositoryInfo  | Repo mapping for a technology      | find_repo_for_technology         |
| FileInfo        | File or directory metadata         | list_files_recursively           |
| FileContent     | Raw file content                  | download_file_content            |

### Implementation Tasks Table
(see Implementation Tasks above)

---