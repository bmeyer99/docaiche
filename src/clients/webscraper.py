import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, HttpUrl
import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import asyncio
from urllib.parse import urlparse, urljoin

from src.core.config.models import ScrapingConfig
from src.clients.exceptions import WebScrapingError, CircuitBreakerError

logger = logging.getLogger(__name__)


class ScrapedContent(BaseModel):
    """
    Data model for scraped web content and metadata.

    Attributes:
        url: The URL of the scraped page.
        title: The page title, if available.
        text: The extracted main text content.
        html: The raw HTML content.
        links: List of discovered links on the page.
        metadata: Additional metadata (headers, status, etc).
    """

    url: HttpUrl
    title: Optional[str]
    text: Optional[str]
    html: Optional[str]
    links: List[HttpUrl]
    metadata: Dict[str, Any]


class WebScrapingClient:
    """
    Asynchronous web scraping client with circuit breaker, robots.txt compliance,
    and rate limiting.

    Args:
        config: ScrapingConfig instance with all scraping settings.

    Raises:
        WebScrapingError: For general scraping errors.
        CircuitBreakerError: When circuit breaker is open.
    """

    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Initialize circuit breaker, rate limiter, and aiohttp session
        self._limiter = AsyncLimiter(1, self.config.rate_limit_delay)
        self._session: Optional[aiohttp.ClientSession] = None
        self._robots_cache: Dict[str, Dict[str, Any]] = {}
        self._circuit_breaker_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_last_open = 0
        self._cb_config = self.config.circuit_breaker

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.config.user_agent},
                timeout=aiohttp.ClientTimeout(total=self._cb_config.timeout_seconds),
            )
        return self._session

    def _check_circuit_breaker(self):
        import time

        if self._circuit_breaker_open:
            elapsed = time.time() - self._circuit_breaker_last_open
            if elapsed > self._cb_config.recovery_timeout:
                self._circuit_breaker_open = False
                self._circuit_breaker_failures = 0
            else:
                raise CircuitBreakerError("Circuit breaker is open")
        # else: proceed

    def _record_failure(self):
        import time

        self._circuit_breaker_failures += 1
        if self._circuit_breaker_failures >= self._cb_config.failure_threshold:
            self._circuit_breaker_open = True
            self._circuit_breaker_last_open = time.time()
            self.logger.error("Circuit breaker opened due to repeated failures.")

    def _record_success(self):
        self._circuit_breaker_failures = 0

    async def is_url_allowed(self, url: str) -> bool:
        """
        Check robots.txt compliance for the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if scraping is allowed, False otherwise.

        Raises:
            WebScrapingError: On robots.txt fetch or parse failure.

        # Implements: robots.txt fetching and parsing
        """
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        user_agent = self.config.user_agent

        # Cache robots.txt per domain
        if base in self._robots_cache:
            rules = self._robots_cache[base]
        else:
            robots_url = urljoin(base, "/robots.txt")
            try:
                session = await self._get_session()
                async with session.get(robots_url) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        rules = self._parse_robots_txt(content)
                        self._robots_cache[base] = rules
                    elif resp.status == 404:
                        # No robots.txt means allowed
                        self._robots_cache[base] = {}
                        return True
                    else:
                        raise WebScrapingError(
                            f"Failed to fetch robots.txt: HTTP {resp.status}",
                            status_code=resp.status,
                        )
            except asyncio.TimeoutError:
                raise WebScrapingError("Timeout fetching robots.txt", status_code=504)
            except Exception as e:
                raise WebScrapingError(
                    f"Error fetching robots.txt: {e}", status_code=500
                )

        # Evaluate rules for user-agent
        path = parsed.path or "/"
        allowed = self._is_path_allowed(rules, user_agent, path)
        return allowed

    def _parse_robots_txt(self, content: str) -> Dict[str, List[str]]:
        # Very basic robots.txt parser for Disallow/Allow rules per user-agent
        rules = {}
        current_agent = None
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
                if current_agent not in rules:
                    rules[current_agent] = []
            elif line.lower().startswith("disallow:") and current_agent:
                path = line.split(":", 1)[1].strip()
                rules.setdefault(current_agent, []).append(("disallow", path))
            elif line.lower().startswith("allow:") and current_agent:
                path = line.split(":", 1)[1].strip()
                rules.setdefault(current_agent, []).append(("allow", path))
        return rules

    def _is_path_allowed(
        self, rules: Dict[str, List[str]], user_agent: str, path: str
    ) -> bool:
        # Follows robots.txt precedence: specific UA > * > allow/disallow order
        agent_rules = rules.get(user_agent, []) + rules.get("*", [])
        allowed = True
        for rule_type, rule_path in agent_rules:
            if path.startswith(rule_path):
                if rule_type == "disallow" and rule_path != "":
                    allowed = False
                elif rule_type == "allow":
                    allowed = True
        return allowed

    async def scrape_page(self, url: str) -> ScrapedContent:
        """
        Scrape a single web page and extract content.

        Args:
            url: The URL to scrape.

        Returns:
            ScrapedContent: Structured content and metadata.

        Raises:
            WebScrapingError: On HTTP or parsing errors.
            CircuitBreakerError: If circuit breaker is open.

        # Implements: HTTP GET, circuit breaker, parsing, and error handling
        """
        self._check_circuit_breaker()
        allowed = await self.is_url_allowed(url)
        if not allowed:
            raise WebScrapingError("Scraping disallowed by robots.txt", status_code=403)

        await self._limiter.acquire()
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                status = resp.status
                headers = dict(resp.headers)
                html = await resp.text(errors="replace")
                if status == 403:
                    self._record_failure()
                    raise WebScrapingError(
                        "Forbidden (403)", status_code=403, error_context={"url": url}
                    )
                if status == 404:
                    self._record_failure()
                    raise WebScrapingError(
                        "Not Found (404)", status_code=404, error_context={"url": url}
                    )
                if status == 429:
                    self._record_failure()
                    raise WebScrapingError(
                        "Rate Limited (429)",
                        status_code=429,
                        error_context={"url": url},
                    )
                if status >= 500:
                    self._record_failure()
                    raise WebScrapingError(
                        f"Server Error ({status})",
                        status_code=status,
                        error_context={"url": url},
                    )
                # Success
                self._record_success()
        except asyncio.TimeoutError:
            self._record_failure()
            raise WebScrapingError(
                "Timeout during HTTP GET", status_code=504, error_context={"url": url}
            )
        except CircuitBreakerError:
            raise
        except Exception as e:
            self._record_failure()
            raise WebScrapingError(
                f"Unexpected error: {e}", status_code=500, error_context={"url": url}
            )

        # Parse HTML and extract content
        soup = BeautifulSoup(html, "lxml")
        # Remove script/style/noscript
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        # Remove comments
        for comment in soup.find_all(
            string=lambda text: isinstance(text, (type(soup.Comment)))
        ):
            comment.extract()
        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        # Extract main text as markdown
        text = md(str(soup.body or soup)) if soup.body else md(str(soup))
        # Extract links
        links = await self.extract_links(str(soup), url)
        # Metadata
        metadata = {
            "headers": headers,
            "status": status,
        }
        return ScrapedContent(
            url=url, title=title, text=text, html=html, links=links, metadata=metadata
        )

    async def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract all valid links from HTML content.

        Args:
            html: Raw HTML content.
            base_url: The base URL for resolving relative links.

        Returns:
            List of absolute URLs as strings.

        # Implements: link extraction using BeautifulSoup4
        """
        soup = BeautifulSoup(html, "lxml")
        found = set()
        base_parsed = urlparse(base_url)
        allowed_domains = [base_parsed.netloc]
        # Optionally support allowed domains from config in future
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue
            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)
            # Only allow http(s) and same-origin
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc not in allowed_domains:
                continue
            found.add(abs_url)
        return list(found)
