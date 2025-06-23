"""
OpenAI-Compatible LLM Provider Implementation - PRD-005 LLM-003

Implements the OpenAI REST API contract, but allows the base URL to be set to any
OpenAI-compatible endpoint (local, remote, proxy, etc). Uses the OpenAI SDK with
configurable api_base for maximum compatibility and developer ergonomics.

This provider does NOT require or use the real OpenAI cloud API unless configured to do so.
"""
import logging
import asyncio
import os
from typing import Any, Dict, Optional

from .base_provider import BaseLLMProvider, LLMProviderError, LLMProviderTimeoutError

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Minimal stateful circuit breaker for PRD-005 contract compliance.
    """
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"
        self.last_failure_time = None

    def record_failure(self, now=None):
        import time
        now = now or time.time()
        self.failures += 1
        self.last_failure_time = now
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def record_success(self):
        self.failures = 0
        self.state = "closed"
        self.last_failure_time = None

    def is_open(self, now=None):
        import time
        now = now or time.time()
        if self.state == "open":
            if self.last_failure_time and (now - self.last_failure_time) > self.recovery_timeout:
                self.state = "half_open"
            else:
                return True
        return False

def _resolve_api_key(config: Dict[str, Any]) -> str:
    """
    Securely resolve the OpenAI API key from config or environment.
    """
    key = config.get('api_key', '')
    if key and not key.startswith('${'):
        return key
    env_var = None
    if key.startswith('${') and key.endswith('}'):
        env_var = key[2:-1]
    if not env_var:
        env_var = 'OPENAI_API_KEY'
    env_value = os.environ.get(env_var, '')
    if not env_value:
        logger.warning("OpenAI API key not found in environment variable %s", env_var)
    return env_value

def _resolve_api_base(config: Dict[str, Any]) -> str:
    """
    Resolve the OpenAI-compatible API base URL from config or environment.
    """
    base = config.get('api_base', '')
    if base and not base.startswith('${'):
        return base
    env_var = None
    if base.startswith('${') and base.endswith('}'):
        env_var = base[2:-1]
    if not env_var:
        env_var = 'OPENAI_API_BASE'
    env_value = os.environ.get(env_var, '')
    if not env_value:
        # Default to OpenAI cloud if nothing set, but user should override for local/proxy
        env_value = 'https://api.openai.com/v1'
    return env_value

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI-compatible LLM provider implementing PRD-005 requirements.

    Uses OpenAI SDK with configurable api_base for compatibility with local/proxy endpoints.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_manager=None):
        """
        Initialize OpenAI-compatible provider with configuration.

        Args:
            config: OpenAI configuration from OpenAIConfig
            cache_manager: Optional cache manager for response caching
        """
        config = config or {}
        super().__init__(config, cache_manager)
        self.api_key = _resolve_api_key(config)
        self.api_base = _resolve_api_base(config)
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        self.timeout = config.get('timeout_seconds', 30)

        # Validate API key (security requirement from PRD-005)
        if not self.api_key or len(self.api_key.strip()) < 8:
            logger.warning("OpenAI API key is missing or too short")

        # Initialize the OpenAI 1.x async client
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
        except ImportError as e:
            logger.error("OpenAI SDK >=1.0.0 is required: %s", e)
            raise

        self._circuit_breaker = self._create_circuit_breaker()

    def _create_circuit_breaker(self):
        # Real stateful circuit breaker for contract compliance
        return CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async def _make_request(self, prompt: str, **kwargs) -> str:
        """
        Make request to OpenAI-compatible Chat Completions API using official SDK.

        Args:
            prompt: Formatted prompt text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Raw response text from OpenAI-compatible endpoint

        Raises:
            LLMProviderError: When request fails
            LLMProviderTimeoutError: When request times out
        """
        try:
            if self._circuit_breaker.is_open():
                raise LLMProviderUnavailableError("Circuit breaker is open")

            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            response = await self._client.chat.completions.create(
                model=kwargs.get('model', self.model),
                messages=messages,
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                top_p=kwargs.get('top_p', 1.0),
                frequency_penalty=kwargs.get('frequency_penalty', 0.0),
                presence_penalty=kwargs.get('presence_penalty', 0.0),
                timeout=self.timeout,
            )
            if not hasattr(response, "choices") or not response.choices:
                self._circuit_breaker.record_failure()
                raise LLMProviderError("Invalid OpenAI response format: missing 'choices'")
            choice = response.choices[0]
            if not hasattr(choice, "message") or not hasattr(choice.message, "content"):
                self._circuit_breaker.record_failure()
                raise LLMProviderError("Invalid OpenAI response format: missing message content")
            response_text = choice.message.content
            if not response_text or not response_text.strip():
                self._circuit_breaker.record_failure()
                raise LLMProviderError("Empty response from OpenAI-compatible endpoint")
            usage = getattr(response, "usage", {})
            logger.debug("OpenAI-compatible response received", extra={
                "tokens_used": getattr(usage, "total_tokens", 0) if usage else 0,
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0
            })
            self._circuit_breaker.record_success()
            return response_text.strip()
        except Exception as e:
            msg = str(e)
            if "authentication" in msg.lower():
                self._circuit_breaker.record_failure()
                logger.error("OpenAI-compatible API authentication failed - check API key")
                raise LLMProviderError("OpenAI-compatible API authentication failed - check API key")
            if "rate limit" in msg.lower():
                self._circuit_breaker.record_failure()
                logger.warning(f"OpenAI-compatible rate limit exceeded: {e}")
                raise LLMProviderError(f"OpenAI-compatible rate limit exceeded: {e}")
            if isinstance(e, asyncio.TimeoutError):
                self._circuit_breaker.record_failure()
                logger.error(f"OpenAI-compatible request timeout after {self.timeout}s")
                raise LLMProviderTimeoutError(f"OpenAI-compatible request timed out after {self.timeout}s")
            logger.error(f"Unexpected OpenAI-compatible error: {e}")
            self._circuit_breaker.record_failure()
            raise LLMProviderError(f"Unexpected OpenAI-compatible error: {str(e)}")

    async def list_models(self) -> Dict[str, Any]:
        """
        List available models from OpenAI-compatible endpoint.

        Returns:
            Dictionary with available models information
        """
        try:
            models = await self._client.models.list()
            model_ids = [
                m.id for m in models.data
                if m.id.startswith(("gpt-", "text-", "davinci", "curie", "babbage", "ada"))
            ]
            return {
                "models": sorted(model_ids),
                "count": len(model_ids),
                "endpoint": self.api_base
            }
        except Exception as e:
            return {
                "models": [],
                "count": 0,
                "error": f"Error fetching models: {str(e)}"
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check OpenAI-compatible health and availability.

        Returns:
            Health status dictionary
        """
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Respond with just: OK"}],
                max_tokens=10,
                temperature=0.1,
                timeout=10
            )
            if hasattr(response, "choices") and response.choices:
                self._circuit_breaker.record_success()
                return {
                    "provider": "openai-compatible",
                    "status": "healthy",
                    "model": self.model,
                    "circuit_breaker": self._circuit_breaker.state,
                    "api_endpoint": self.api_base
                }
            self._circuit_breaker.record_failure()
            return {
                "provider": "openai-compatible",
                "status": "unhealthy",
                "error": "Unexpected response format",
                "api_endpoint": self.api_base,
                "circuit_breaker": self._circuit_breaker.state
            }
        except Exception as e:
            self._circuit_breaker.record_failure()
            msg = str(e)
            if "authentication" in msg.lower():
                return {
                    "provider": "openai-compatible",
                    "status": "unhealthy",
                    "error": "Authentication failed - check API key",
                    "api_endpoint": self.api_base,
                    "circuit_breaker": self._circuit_breaker.state
                }
            if "rate limit" in msg.lower():
                return {
                    "provider": "openai-compatible",
                    "status": "rate_limited",
                    "error": "API rate limit exceeded",
                    "api_endpoint": self.api_base,
                    "circuit_breaker": self._circuit_breaker.state
                }
            if isinstance(e, asyncio.TimeoutError):
                return {
                    "provider": "openai-compatible",
                    "status": "unhealthy",
                    "error": "Health check timeout",
                    "api_endpoint": self.api_base,
                    "circuit_breaker": self._circuit_breaker.state
                }
            return {
                "provider": "openai-compatible",
                "status": "unhealthy",
                "error": str(e),
                "api_endpoint": self.api_base,
                "circuit_breaker": self._circuit_breaker.state
            }

    async def close(self):
        """No persistent session to close with OpenAI SDK."""
        logger.debug("OpenAI-compatible provider cleanup complete")