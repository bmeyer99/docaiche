"""
Ollama LLM Provider Implementation - PRD-005 LLM-002
Ollama-specific provider class with POST requests to /api/generate endpoint

Implements circuit breaker configuration for internal service with lower
tolerance settings as specified in PRD-005 lines 244-250.
"""

import logging
import asyncio
import aiohttp
from typing import Any, Dict, Optional, List
from datetime import datetime

from .base_provider import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)
from .models import (
    ProviderCapabilities, ProviderCategory, ModelInfo, ModelType,
    ModelDiscoveryResult, TextGenerationRequest, TextGenerationResponse
)

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
            if (
                self.last_failure_time
                and (now - self.last_failure_time) > self.recovery_timeout
            ):
                self.state = "half_open"
            else:
                return True
        return False


class OllamaProvider(BaseLLMProvider):
    """
    Ollama-specific LLM provider implementing PRD-005 requirements and multi-provider interface.

    Makes POST requests to Ollama's /api/generate endpoint with internal
    service circuit breaker configuration (failure_threshold=3, recovery_timeout=60).
    """
    
    # Provider metadata
    _provider_id = "ollama"
    _display_name = "Ollama"
    _description = "Local Ollama server for running LLM models"
    _category = ProviderCategory.LOCAL

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        """
        Initialize Ollama provider with configuration.

        Args:
            config: Ollama configuration (required)
            cache_manager: Optional cache manager for response caching
        """
        super().__init__(config, cache_manager)
        self.endpoint = config.get("endpoint", "http://localhost:11434").rstrip("/")
        self.model = config.get("model", "llama2")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)
        self.timeout = config.get("timeout_seconds", 60)
        self.session: aiohttp.ClientSession = None
        self._circuit_breaker = self._create_circuit_breaker()

    @classmethod
    def get_static_capabilities(cls) -> ProviderCapabilities:
        """Get static capabilities for Ollama provider."""
        return ProviderCapabilities(
            text_generation=True,
            embeddings=False,  # Ollama embeddings require separate endpoint
            streaming=True,
            function_calling=False,
            local=True,
            model_discovery=True,
            prompt_caching=False,
            system_prompts=True,
            json_mode=True,
            vision=False
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for Ollama configuration."""
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "default": "http://localhost:11434",
                    "description": "Ollama server endpoint URL"
                },
                "model": {
                    "type": "string", 
                    "default": "llama2",
                    "description": "Default model name"
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "default": 0.7,
                    "description": "Sampling temperature"
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 32768,
                    "default": 4096,
                    "description": "Maximum tokens to generate"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 60,
                    "description": "Request timeout in seconds"
                }
            },
            "required": ["endpoint"],
            "additionalProperties": True
        }
    
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
                    "Content-Type": "application/json",
                    "User-Agent": "AI-Documentation-Cache/1.0",
                },
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
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }
        if "top_p" in kwargs:
            payload["options"]["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["options"]["top_k"] = kwargs["top_k"]

        url = f"{self.endpoint}/api/generate"
        try:
            logger.debug(f"Making Ollama request to {url}")
            async with self.session.post(url, json=payload) as response:
                if response.status == 404:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError(
                        f"Ollama model '{payload['model']}' not found"
                    )
                elif response.status == 500:
                    self._circuit_breaker.record_failure()
                    error_text = await response.text()
                    raise LLMProviderError(f"Ollama server error: {error_text}")
                elif response.status != 200:
                    self._circuit_breaker.record_failure()
                    error_text = await response.text()
                    raise LLMProviderError(
                        f"Ollama request failed with status {response.status}: {error_text}"
                    )
                response_data = await response.json()
                if "error" in response_data:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError(f"Ollama error: {response_data['error']}")
                if "response" not in response_data:
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError(
                        "Invalid Ollama response format: missing 'response' field"
                    )
                response_text = response_data["response"]
                if not response_text or not response_text.strip():
                    self._circuit_breaker.record_failure()
                    raise LLMProviderError("Empty response from Ollama")
                logger.debug(f"Received Ollama response ({len(response_text)} chars)")
                self._circuit_breaker.record_success()
                return response_text.strip()
        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            logger.error(f"Ollama request timeout after {self.timeout}s")
            raise LLMProviderTimeoutError(
                f"Ollama request timed out after {self.timeout}s"
            )
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
                        "models": [model["name"] for model in data.get("models", [])],
                        "count": len(data.get("models", [])),
                        "endpoint": self.endpoint,
                    }
                else:
                    return {
                        "models": [],
                        "count": 0,
                        "error": f"Failed to fetch models: HTTP {response.status}",
                    }
        except Exception as e:
            return {
                "models": [],
                "count": 0,
                "error": f"Error fetching models: {str(e)}",
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
                "model": self.model,
                "prompt": "Respond with just: OK",
                "stream": False,
                "options": {"num_predict": 10, "temperature": 0.1},
            }
            logger.info(f"Ollama health check: endpoint={self.endpoint}, model={self.model}, payload={test_payload}")
            response = await asyncio.wait_for(
                self.session.post(url, json=test_payload), timeout=10.0
            )
            async with response:
                if response.status == 200:
                    data = await response.json()
                    if "response" in data:
                        self._circuit_breaker.record_success()
                        return {
                            "provider": "ollama",
                            "status": "healthy",
                            "endpoint": self.endpoint,
                            "model": self.model,
                            "circuit_breaker": self._circuit_breaker.state,
                        }
                self._circuit_breaker.record_failure()
                return {
                    "provider": "ollama",
                    "status": "unhealthy",
                    "error": f"Unexpected response status: {response.status}",
                    "endpoint": self.endpoint,
                    "circuit_breaker": self._circuit_breaker.state,
                }
        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            return {
                "provider": "ollama",
                "status": "unhealthy",
                "error": "Health check timeout",
                "endpoint": self.endpoint,
                "circuit_breaker": self._circuit_breaker.state,
            }
        except Exception as e:
            self._circuit_breaker.record_failure()
            return {
                "provider": "ollama",
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.endpoint,
                "circuit_breaker": self._circuit_breaker.state,
            }

    async def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """
        Generate text using Ollama.
        
        Args:
            request: Text generation request
            
        Returns:
            Text generation response
        """
        start_time = datetime.utcnow()
        
        # Build generation parameters
        kwargs = {
            "model": request.model_id or self.model,
            "temperature": request.temperature or self.temperature,
            "max_tokens": request.max_tokens or self.max_tokens
        }
        
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        
        # Use system prompt if provided
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"System: {request.system_prompt}\n\nUser: {prompt}"
        
        try:
            response_text = await self._make_request(prompt, **kwargs)
            
            # Calculate metrics
            end_time = datetime.utcnow()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Estimate token usage (rough approximation)
            tokens_used = len(prompt.split()) + len(response_text.split())
            
            return TextGenerationResponse(
                text=response_text,
                finish_reason="stop",  # Ollama doesn't provide detailed finish reasons
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                model_id=kwargs["model"],
                provider_id=self._provider_id,
                cost_usd=None,  # Local model has no cost
                metadata=request.metadata
            )
            
        except Exception as e:
            raise LLMProviderError(f"Text generation failed: {str(e)}")
    
    async def discover_models(self, config: Dict[str, Any]) -> ModelDiscoveryResult:
        """
        Discover available models from Ollama server.
        
        Args:
            config: Provider configuration
            
        Returns:
            Model discovery result
        """
        try:
            models_info = await self.list_models()
            
            text_models = []
            for model_name in models_info.get("models", []):
                text_models.append(ModelInfo(
                    model_id=model_name,
                    display_name=model_name,
                    model_type=ModelType.TEXT,
                    context_window=None,  # Would need to query each model
                    max_tokens=None,
                    cost_per_token=None,  # Local models are free
                    capabilities={"local": True, "streaming": True},
                    deprecated=False
                ))
            
            return ModelDiscoveryResult(
                text_models=text_models,
                embedding_models=[],  # Ollama embeddings use different endpoint
                source="api"
            )
            
        except Exception as e:
            logger.warning(f"Model discovery failed: {e}")
            # Return static fallback
            return ModelDiscoveryResult(
                text_models=self._get_static_text_models(),
                embedding_models=[],
                source="static"
            )
    
    def _get_static_text_models(self) -> List[ModelInfo]:
        """Get static list of common Ollama models."""
        return [
            ModelInfo(
                model_id="llama2",
                display_name="Llama 2",
                model_type=ModelType.TEXT,
                context_window=4096,
                capabilities={"local": True, "streaming": True}
            ),
            ModelInfo(
                model_id="llama3.1:8b",
                display_name="Llama 3.1 8B",
                model_type=ModelType.TEXT,
                context_window=8192,
                capabilities={"local": True, "streaming": True}
            ),
            ModelInfo(
                model_id="mistral",
                display_name="Mistral",
                model_type=ModelType.TEXT,
                context_window=4096,
                capabilities={"local": True, "streaming": True}
            )
        ]
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Ollama provider session closed")
