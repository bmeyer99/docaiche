"""GitHub Repository Client (PRD-006)
Architectural scaffolding for async GitHub API integration with circuit breaker, configuration, and error handling.

Responsibilities:
- Async GitHub API access with aiohttp
- Circuit breaker integration (see PRD-006 lines 32-51)
- Dependency injection for config and database
- Structured error handling via clients/exceptions.py
- Data models for rate limit, repo, file info, and file content

Implementation Engineer: Fill in all TODOs per docstrings and PRD-006 requirements.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import aiohttp
import base64

from src.core.config.models import GitHubConfig
from src.database.manager import DatabaseManager
from src.clients.exceptions import GitHubClientError, CircuitBreakerError

# Redis cache manager import
try:
    from src.cache.manager import CacheManager
except ImportError:
    CacheManager = None

logger = logging.getLogger(__name__)

# --- Data Models ---

class RateLimitStatus(BaseModel):
    """GitHub API rate limit status model.
    
    Attributes:
        limit: Maximum number of requests allowed in the current window.
        remaining: Number of requests remaining in the current window.
        reset: Time at which the current rate limit window resets (epoch seconds).
    """
    limit: int
    remaining: int
    reset: int

class RepositoryInfo(BaseModel):
    """Repository metadata model.
    
    Attributes:
        id: Repository unique identifier.
        name: Repository name.
        full_name: Full repository name (owner/name).
        private: Whether the repository is private.
        description: Repository description.
        url: Repository URL.
        default_branch: Default branch name.
        owner: Owner username.
        metadata: Additional metadata.
    """
    id: int
    name: str
    full_name: str
    private: bool
    description: Optional[str]
    url: str
    default_branch: str
    owner: str
    metadata: Optional[Dict[str, Any]] = None

class FileInfo(BaseModel):
    """File metadata model for repository contents.
    
    Attributes:
        path: File path in the repository.
        type: File type (file, dir, symlink, submodule).
        size: File size in bytes.
        sha: File SHA hash.
        url: API URL for file.
    """
    path: str
    type: str
    size: Optional[int]
    sha: str
    url: str

class FileContent(BaseModel):
    """File content model.
    
    Attributes:
        path: File path in the repository.
        content: Decoded file content (UTF-8).
        encoding: Content encoding (e.g., 'utf-8').
        sha: File SHA hash.
    """
    path: str
    content: str
    encoding: str
    sha: str

# --- Circuit Breaker Helper ---

class CircuitBreaker:
    """Simple circuit breaker for GitHub API requests.
    
    Args:
        failure_threshold: Number of failures before opening the circuit.
        recovery_timeout: Seconds to wait before attempting recovery.
    
    Usage:
        Use as a decorator or context manager for API calls.
    """
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            import time
            # Check if circuit is open
            if self.state == "OPEN":
                if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                    # Move to HALF-OPEN, try the request
                    self.state = "HALF-OPEN"
                else:
                    raise CircuitBreakerError("Circuit breaker is open")
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.error(f"Circuit breaker opened after {self.failure_count} failures.")
                    raise CircuitBreakerError("Circuit breaker is open due to repeated failures")
                logger.warning(f"Circuit breaker failure count: {self.failure_count}")
                raise
            else:
                # Success: reset breaker if in HALF-OPEN or CLOSED
                if self.state in ("OPEN", "HALF-OPEN"):
                    self.state = "CLOSED"
                self.failure_count = 0
                self.last_failure_time = None
                return result
        return wrapper

# --- GitHub Client ---

class GitHubClient:
    """Async GitHub API client with circuit breaker and dependency injection.
    
    Args:
        config: GitHubConfig instance (PRD-003)
        db_manager: DatabaseManager instance (PRD-002)
    
    Attributes:
        session: aiohttp.ClientSession for HTTP requests
        circuit_breaker: CircuitBreaker instance for API calls
        logger: Logger for structured logging
    """

    def __init__(
        self,
        config: GitHubConfig,
        db_manager: DatabaseManager,
        session: Optional[aiohttp.ClientSession] = None,
        cache_manager: Optional[Any] = None,
    ):
        self.config = config
        self.db_manager = db_manager
        self.session = session or aiohttp.ClientSession()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.cache_manager = cache_manager

    async def __aenter__(self):
        """Async context manager entry. Initializes aiohttp session if needed."""
        if self.session.closed:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit. Closes aiohttp session."""
        if not self.session.closed:
            await self.session.close()

    async def get_rate_limit_status(self) -> RateLimitStatus:
        """Fetch current GitHub API rate limit status.
        
        Returns:
            RateLimitStatus: Current rate limit info.
        
        Raises:
            GitHubClientError: On API or network failure.
            CircuitBreakerError: If circuit is open.
        """
        async def api_call():
            url = "https://api.github.com/rate_limit"
            headers = {
                "Authorization": f"token {self.config.api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DocaicheBot/1.0"
            }
            
            try:
                async with self.session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status == 401:
                        self.logger.error("GitHub authentication failed")
                        raise GitHubClientError("Authentication failed", status_code=401)
                    
                    if resp.status == 403:
                        # Rate limit exceeded or forbidden
                        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                        limit = int(resp.headers.get("X-RateLimit-Limit", "0"))
                        self.logger.warning("GitHub API rate limit exceeded or forbidden")
                        raise GitHubClientError(
                            "Rate limit exceeded or forbidden",
                            status_code=403,
                            error_context={"limit": limit, "remaining": remaining, "reset": reset}
                        )
                    
                    if resp.status >= 500:
                        self.logger.error(f"GitHub server error: {resp.status}")
                        raise GitHubClientError("GitHub server error", status_code=resp.status)
                    
                    if resp.status != 200:
                        self.logger.error(f"Unexpected GitHub API status: {resp.status}")
                        raise GitHubClientError("Unexpected GitHub API status", status_code=resp.status)
                    
                    data = await resp.json()
                    core = data.get("resources", {}).get("core", {})
                    return RateLimitStatus(
                        limit=core.get("limit", 0),
                        remaining=core.get("remaining", 0),
                        reset=core.get("reset", 0)
                    )
                    
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error during rate limit check: {e}")
                raise GitHubClientError("Network error during rate limit check", status_code=503)
            except Exception as e:
                self.logger.error(f"Unexpected error during rate limit check: {e}")
                raise GitHubClientError("Unexpected error during rate limit check", status_code=500)
        
        return await self.circuit_breaker(api_call)()

    async def get_repository_info(self, owner: str, repo: str) -> RepositoryInfo:
        """Fetch repository metadata.
        
        Args:
            owner: Repository owner username.
            repo: Repository name.
        
        Returns:
            RepositoryInfo: Repository metadata.
        
        Raises:
            GitHubClientError: On API or network failure.
            CircuitBreakerError: If circuit is open.
        
        TODO: IMPLEMENTATION ENGINEER - Implement GitHub repo info API call with circuit breaker.
        """
        async def api_call():
            url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {
                "Authorization": f"token {self.config.api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DocaicheBot/1.0"
            }
            try:
                async with self.session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status == 401:
                        self.logger.error("GitHub authentication failed")
                        raise GitHubClientError("Authentication failed", status_code=401)
                    if resp.status == 403:
                        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                        limit = int(resp.headers.get("X-RateLimit-Limit", "0"))
                        self.logger.warning("GitHub API rate limit exceeded or forbidden")
                        raise GitHubClientError(
                            "Rate limit exceeded or forbidden",
                            status_code=403,
                            error_context={"limit": limit, "remaining": remaining, "reset": reset}
                        )
                    if resp.status == 404:
                        self.logger.error("Repository not found")
                        raise GitHubClientError("Repository not found", status_code=404)
                    if resp.status >= 500:
                        self.logger.error(f"GitHub server error: {resp.status}")
                        raise GitHubClientError("GitHub server error", status_code=resp.status)
                    if resp.status != 200:
                        self.logger.error(f"Unexpected GitHub API status: {resp.status}")
                        raise GitHubClientError("Unexpected GitHub API status", status_code=resp.status)
                    data = await resp.json()
                    return RepositoryInfo(
                        id=data.get("id"),
                        name=data.get("name"),
                        full_name=data.get("full_name"),
                        private=data.get("private"),
                        description=data.get("description"),
                        url=data.get("html_url"),
                        default_branch=data.get("default_branch"),
                        owner=data.get("owner", {}).get("login"),
                        metadata={
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "pushed_at": data.get("pushed_at"),
                            "language": data.get("language"),
                            "topics": data.get("topics"),
                        }
                    )
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error during repository info fetch: {e}")
                raise GitHubClientError("Network error during repository info fetch", status_code=503)
            except Exception as e:
                self.logger.error(f"Unexpected error during repository info fetch: {e}")
                raise GitHubClientError("Unexpected error during repository info fetch", status_code=500)
        return await self.circuit_breaker(api_call)()

    async def list_repository_contents(
        self, 
        owner: str, 
        repo: str, 
        path: str = "", 
        ref: Optional[str] = None
    ) -> List[FileInfo]:
        """List contents of a repository directory.
        
        Args:
            owner: Repository owner username.
            repo: Repository name.
            path: Directory path (empty for root).
            ref: Git reference (branch/tag/commit).
        
        Returns:
            List[FileInfo]: List of files and directories.
        
        Raises:
            GitHubClientError: On API or network failure.
            CircuitBreakerError: If circuit is open.
        
        TODO: IMPLEMENTATION ENGINEER - Implement GitHub contents API call with circuit breaker.
        """
        async def api_call():
            # Caching key
            cache_key = f"github:contents:{owner}/{repo}:{path or 'root'}:{ref or 'default'}"
            if self.cache_manager:
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    try:
                        return [FileInfo(**item) for item in cached]
                    except Exception as e:
                        self.logger.warning(f"Cache decode error: {e}")

            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}" if path else f"https://api.github.com/repos/{owner}/{repo}/contents"
            headers = {
                "Authorization": f"token {self.config.api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DocaicheBot/1.0"
            }
            params = {}
            if ref:
                params["ref"] = ref

            try:
                async with self.session.get(url, headers=headers, params=params, timeout=30) as resp:
                    if resp.status == 401:
                        self.logger.error("GitHub authentication failed")
                        raise GitHubClientError("Authentication failed", status_code=401)
                    if resp.status == 403:
                        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                        limit = int(resp.headers.get("X-RateLimit-Limit", "0"))
                        self.logger.warning("GitHub API rate limit exceeded or forbidden")
                        raise GitHubClientError(
                            "Rate limit exceeded or forbidden",
                            status_code=403,
                            error_context={"limit": limit, "remaining": remaining, "reset": reset}
                        )
                    if resp.status == 404:
                        self.logger.error("Repository or path not found")
                        raise GitHubClientError("Repository or path not found", status_code=404)
                    if resp.status >= 500:
                        self.logger.error(f"GitHub server error: {resp.status}")
                        raise GitHubClientError("GitHub server error", status_code=resp.status)
                    if resp.status != 200:
                        self.logger.error(f"Unexpected GitHub API status: {resp.status}")
                        raise GitHubClientError("Unexpected GitHub API status", status_code=resp.status)
                    data = await resp.json()
                    # If it's a file, wrap in a list
                    if isinstance(data, dict) and data.get("type") == "file":
                        data = [data]
                    result = []
                    for item in data:
                        result.append(FileInfo(
                            path=item.get("path"),
                            type=item.get("type"),
                            size=item.get("size"),
                            sha=item.get("sha"),
                            url=item.get("url"),
                        ))
                    # Cache result
                    if self.cache_manager:
                        try:
                            await self.cache_manager.set(cache_key, [f.dict() for f in result], ttl=600)
                        except Exception as e:
                            self.logger.warning(f"Cache set error: {e}")
                    return result
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error during repository contents listing: {e}")
                raise GitHubClientError("Network error during repository contents listing", status_code=503)
            except Exception as e:
                self.logger.error(f"Unexpected error during repository contents listing: {e}")
                raise GitHubClientError("Unexpected error during repository contents listing", status_code=500)
        return await self.circuit_breaker(api_call)()

    async def get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str, 
        ref: Optional[str] = None
    ) -> FileContent:
        """Fetch file content from repository.
        
        Args:
            owner: Repository owner username.
            repo: Repository name.
            path: File path in repository.
            ref: Git reference (branch/tag/commit).
        
        Returns:
            FileContent: File content and metadata.
        
        Raises:
            GitHubClientError: On API or network failure.
            CircuitBreakerError: If circuit is open.
        
        TODO: IMPLEMENTATION ENGINEER - Implement GitHub file content API call with circuit breaker.
        """
        async def api_call():
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            headers = {
                "Authorization": f"token {self.config.api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DocaicheBot/1.0"
            }
            params = {}
            if ref:
                params["ref"] = ref
            try:
                async with self.session.get(url, headers=headers, params=params, timeout=30) as resp:
                    if resp.status == 401:
                        self.logger.error("GitHub authentication failed")
                        raise GitHubClientError("Authentication failed", status_code=401)
                    if resp.status == 403:
                        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        remaining = int(resp.headers.get("X-RateLimit-Remaining", "0"))
                        limit = int(resp.headers.get("X-RateLimit-Limit", "0"))
                        self.logger.warning("GitHub API rate limit exceeded or forbidden")
                        raise GitHubClientError(
                            "Rate limit exceeded or forbidden",
                            status_code=403,
                            error_context={"limit": limit, "remaining": remaining, "reset": reset}
                        )
                    if resp.status == 404:
                        self.logger.error("File not found")
                        raise GitHubClientError("File not found", status_code=404)
                    if resp.status >= 500:
                        self.logger.error(f"GitHub server error: {resp.status}")
                        raise GitHubClientError("GitHub server error", status_code=resp.status)
                    if resp.status != 200:
                        self.logger.error(f"Unexpected GitHub API status: {resp.status}")
                        raise GitHubClientError("Unexpected GitHub API status", status_code=resp.status)
                    data = await resp.json()
                    if data.get("encoding") == "base64":
                        try:
                            decoded = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                        except Exception as e:
                            self.logger.error(f"Base64 decode error: {e}")
                            raise GitHubClientError("File content decode error", status_code=500)
                        encoding = "utf-8"
                    else:
                        decoded = data.get("content", "")
                        encoding = data.get("encoding", "utf-8")
                    return FileContent(
                        path=data.get("path"),
                        content=decoded,
                        encoding=encoding,
                        sha=data.get("sha"),
                    )
            except aiohttp.ClientError as e:
                self.logger.error(f"Network error during file content fetch: {e}")
                raise GitHubClientError("Network error during file content fetch", status_code=503)
            except Exception as e:
                self.logger.error(f"Unexpected error during file content fetch: {e}")
                raise GitHubClientError("Unexpected error during file content fetch", status_code=500)
        return await self.circuit_breaker(api_call)()

    async def close(self):
        """Close aiohttp session if open."""
        if not self.session.closed:
            await self.session.close()