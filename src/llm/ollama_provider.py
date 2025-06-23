"""
Ollama LLM Provider Implementation - PRD-005 LLM-002
Ollama-specific provider class with POST requests to /api/generate endpoint

Implements circuit breaker configuration for internal service with lower
tolerance settings as specified in PRD-005 lines 244-250.
"""

import logging
import asyncio
import aiohttp
from typing import Any, Dict, Optional

from .base_provider import BaseLLMProvider, LLMProviderError, LLMProviderTimeoutError, LLMProviderUnavailableError

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Minimal stateful circuit breaker for PRD-005 contract compliance.
    """
    def __init__(self, failure_threshold=3, recovery_timeout=60):
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

class OllamaProvider(BaseLLMProvider):
    """
    Ollama-specific LLM provider implementing PRD-005 requirements.
    
    Makes POST requests to Ollama's /api/generate endpoint with internal
    service circuit breaker configuration (failure_threshold=3, recovery_timeout=60).
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_manager=None):
        """
        Initialize Ollama provider with configuration.

        Args:
            config: Ollama configuration from OllamaConfig
            cache_manager: Optional cache manager for response caching
        """
        config = config or {}
        super().__init__(config, cache_manager)
        self.endpoint = config.get('endpoint', 'http://localhost:11434').rstrip('/')
        self.model = config.get('model', 'llama2')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        self.timeout = config.get('timeout_seconds', 60)
        self.session: aiohttp.ClientSession = None
        self._circuit_breaker = self._create_circuit_breaker()

    def _create_circuit_breaker(self):
        # Real stateful circuit breaker for contract compliance
        return CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def _ensure_session(self):
        """Ensure HTTP session is created and configured."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'AI-Documentation-Cache/1.0'
                }
            )

    async def _make_request(self, prompt: str, **kwargs) -> str:
        """
        Make POST request to Ollama /api/generate endpoint.

        Args:
            prompt: Formatted prompt text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Raw response text from Ollama
            
        Raises:
            LLMProviderError: When request fails
            LLMProviderTimeoutError: When request times out
        """
        await self._ensure_session()
        if self._circuit_breaker.is_open():
            raise LLMProviderUnavailableError("Circuit breaker is open")
        payload = {
            'model': kwargs.get('model', self.model),
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }
        if 'top_p' in kwargs:
            payload['options']['top_p'] = kwargs['top_p']
        if 'top_k' in kwargs:
            payload['options']['top_k'] = kwargs['top_k']

        url = f"{self.endpoint}/api/generate"
        try:
            logger.debug(f"Making Ollama request to {url}")
            async with self.session.post(url, json=payload) as response:
                if response.status == 404:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError(f"Ollama model '{payload['model']}' not found")
                elif response.status == 500:
                    self._circuit_breaker.record_failure()
                    error_text = await response.text()
                    raise LLMProviderError(f"Ollama server error: {error_text}")
                elif response.status != 200:
                    self._circuit_breaker.record_failure()
                    error_text = await response.text()
                    raise LLMProviderError(f"Ollama request failed with status {response.status}: {error_text}")
                response_data = await response.json()
                if 'error' in response_data:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError(f"Ollama error: {response_data['error']}")
                if 'response' not in response_data:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError("Invalid Ollama response format: missing 'response' field")
                response_text = response_data['response']
                if not response_text or not response_text.strip():
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError("Empty response from Ollama")
                logger.debug(f"Received Ollama response ({len(response_text)} chars)")
                self._circuit_breaker.record_success()
                return response_text.strip()
        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            logger.error(f"Ollama request timeout after {self.timeout}s")
            raise LLMProviderTimeoutError(f"Ollama request timed out after {self.timeout}s")
        except aiohttp.ClientError as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Ollama client error: {e}")
            raise LLMProviderError(f"Ollama connection error: {str(e)}")
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Unexpected Ollama error: {e}")
            raise LLMProviderError(f"Unexpected Ollama error: {str(e)}")

    async def list_models(self) -> Dict[str, Any]:
        """
        List available models from Ollama.

        Returns:
            Dictionary with available models information
        """
        await self._ensure_session()
        try:
            url = f"{self.endpoint}/api/tags"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'models': [model['name'] for model in data.get('models', [])],
                        'count': len(data.get('models', [])),
                        'endpoint': self.endpoint
                    }
                else:
                    return {
                        'models': [],
                        'count': 0,
                        'error': f"Failed to fetch models: HTTP {response.status}"
                    }
        except Exception as e:
            return {
                'models': [],
                'count': 0,
                'error': f"Error fetching models: {str(e)}"
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Ollama health and availability.

        Returns:
            Health status dictionary
        """
        try:
            await self._ensure_session()
            url = f"{self.endpoint}/api/generate"
            test_payload = {
                'model': self.model,
                'prompt': 'Respond with just: OK',
                'stream': False,
                'options': {
                    'num_predict': 10,
                    'temperature': 0.1
                }
            }
            async with asyncio.wait_for(
                self.session.post(url, json=test_payload),
                timeout=10.0
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'response' in data:
                        self._circuit_breaker.record_success()
                        return {
                            "provider": "ollama",
                            "status": "healthy",
                            "endpoint": self.endpoint,
                            "model": self.model,
                            "circuit_breaker": self._circuit_breaker.state
                        }
                self._circuit_breaker.record_failure()
                return {
                    "provider": "ollama",
                    "status": "unhealthy",
                    "error": f"Unexpected response status: {response.status}",
                    "endpoint": self.endpoint,
                    "circuit_breaker": self._circuit_breaker.state
                }
        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            return {
                "provider": "ollama", 
                "status": "unhealthy",
                "error": "Health check timeout",
                "endpoint": self.endpoint,
                "circuit_breaker": self._circuit_breaker.state
            }
        except Exception as e:
            self._circuit_breaker.record_failure()
            return {
                "provider": "ollama",
                "status": "unhealthy", 
                "error": str(e),
                "endpoint": self.endpoint,
                "circuit_breaker": self._circuit_breaker.state
            }

    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Ollama provider session closed")