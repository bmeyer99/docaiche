"""
Ollama LLM Provider Implementation - PRD-005 LLM-002
Ollama-specific provider class with POST requests to /api/generate endpoint

Implements circuit breaker configuration for internal service with lower
tolerance settings as specified in PRD-005 lines 244-250.
"""

import logging
import asyncio
import aiohttp
from typing import Any, Dict
from circuitbreaker import circuit

from .base_provider import BaseLLMProvider, LLMProviderError, LLMProviderTimeoutError

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama-specific LLM provider implementing PRD-005 requirements.
    
    Makes POST requests to Ollama's /api/generate endpoint with internal
    service circuit breaker configuration (failure_threshold=3, recovery_timeout=60).
    """
    
    def __init__(self, config: Dict[str, Any], cache_manager=None):
        """
        Initialize Ollama provider with configuration.
        
        Args:
            config: Ollama configuration from OllamaConfig
            cache_manager: Optional cache manager for response caching
        """
        super().__init__(config, cache_manager)
        self.endpoint = config.get('endpoint', 'http://localhost:11434').rstrip('/')
        self.model = config.get('model', 'llama2')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        self.timeout = config.get('timeout_seconds', 60)
        
        # Create HTTP session for connection reuse
        self.session: aiohttp.ClientSession = None
    
    def _create_circuit_breaker(self):
        """
        Create Ollama-specific circuit breaker for internal service.
        
        PRD-005 specifies: failure_threshold=3, recovery_timeout=60, timeout=30
        Lower tolerance for predictable local Docker service.
        """
        return circuit(
            failure_threshold=3,
            recovery_timeout=60,
            timeout=30,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
        )
    
    async def _ensure_session(self):
        """Ensure HTTP session is created and configured."""
        if self.session is None or self.session.closed:
            # Create session with appropriate timeouts and security settings
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=10,  # Connection pool limit
                ttl_dns_cache=300,  # DNS cache TTL
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
        
        # Prepare request payload according to Ollama API spec
        payload = {
            'model': kwargs.get('model', self.model),
            'prompt': prompt,
            'stream': False,  # Get complete response, not streaming
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }
        
        # Add any additional Ollama-specific options
        if 'top_p' in kwargs:
            payload['options']['top_p'] = kwargs['top_p']
        if 'top_k' in kwargs:
            payload['options']['top_k'] = kwargs['top_k']
        
        url = f"{self.endpoint}/api/generate"
        
        try:
            logger.debug(f"Making Ollama request to {url}")
            
            async with self.session.post(url, json=payload) as response:
                # Check for HTTP errors
                if response.status == 404:
                    raise LLMProviderError(f"Ollama model '{payload['model']}' not found")
                elif response.status == 500:
                    error_text = await response.text()
                    raise LLMProviderError(f"Ollama server error: {error_text}")
                elif response.status != 200:
                    error_text = await response.text()
                    raise LLMProviderError(f"Ollama request failed with status {response.status}: {error_text}")
                
                # Parse Ollama response format
                response_data = await response.json()
                
                if 'error' in response_data:
                    raise LLMProviderError(f"Ollama error: {response_data['error']}")
                
                if 'response' not in response_data:
                    raise LLMProviderError("Invalid Ollama response format: missing 'response' field")
                
                response_text = response_data['response']
                
                if not response_text or not response_text.strip():
                    raise LLMProviderError("Empty response from Ollama")
                
                logger.debug(f"Received Ollama response ({len(response_text)} chars)")
                return response_text.strip()
                
        except asyncio.TimeoutError:
            logger.error(f"Ollama request timeout after {self.timeout}s")
            raise LLMProviderTimeoutError(f"Ollama request timed out after {self.timeout}s")
        
        except aiohttp.ClientError as e:
            logger.error(f"Ollama client error: {e}")
            raise LLMProviderError(f"Ollama connection error: {str(e)}")
        
        except Exception as e:
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
            
            # Test with a simple generation request
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
                        return {
                            "provider": "ollama",
                            "status": "healthy",
                            "endpoint": self.endpoint,
                            "model": self.model,
                            "circuit_breaker": "closed"
                        }
                
                return {
                    "provider": "ollama",
                    "status": "unhealthy",
                    "error": f"Unexpected response status: {response.status}",
                    "endpoint": self.endpoint
                }
                
        except asyncio.TimeoutError:
            return {
                "provider": "ollama", 
                "status": "unhealthy",
                "error": "Health check timeout",
                "endpoint": self.endpoint
            }
        except Exception as e:
            return {
                "provider": "ollama",
                "status": "unhealthy", 
                "error": str(e),
                "endpoint": self.endpoint,
                "circuit_breaker": "open" if "Circuit breaker" in str(e) else "unknown"
            }
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Ollama provider session closed")