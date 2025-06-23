"""
OpenAI LLM Provider Implementation - PRD-005 LLM-003
OpenAI-specific provider class using openai.ChatCompletion.acreate async methods

Implements circuit breaker configuration for external API with higher
tolerance settings as specified in PRD-005 lines 236-242.
"""

import logging
import asyncio
import aiohttp
from typing import Any, Dict
from circuitbreaker import circuit

from .base_provider import BaseLLMProvider, LLMProviderError, LLMProviderTimeoutError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI-specific LLM provider implementing PRD-005 requirements.
    
    Uses OpenAI API with external API circuit breaker configuration
    (failure_threshold=5, recovery_timeout=300) for higher tolerance.
    """
    
    def __init__(self, config: Dict[str, Any], cache_manager=None):
        """
        Initialize OpenAI provider with configuration.
        
        Args:
            config: OpenAI configuration from OpenAIConfig
            cache_manager: Optional cache manager for response caching
        """
        super().__init__(config, cache_manager)
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        self.timeout = config.get('timeout_seconds', 30)
        
        # OpenAI API endpoint
        self.api_base = "https://api.openai.com/v1"
        
        # Create HTTP session for connection reuse
        self.session: aiohttp.ClientSession = None
        
        # Validate API key (security requirement from PRD-005)
        if not self.api_key or len(self.api_key.strip()) < 8:
            logger.warning("OpenAI API key is missing or too short")
    
    def _create_circuit_breaker(self):
        """
        Create OpenAI-specific circuit breaker for external API.
        
        PRD-005 specifies: failure_threshold=5, recovery_timeout=300, timeout=30
        Higher tolerance for external API due to rate limiting and variable response times.
        """
        return circuit(
            failure_threshold=5,
            recovery_timeout=300,
            timeout=30,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
        )
    
    async def _ensure_session(self):
        """Ensure HTTP session is created and configured."""
        if self.session is None or self.session.closed:
            # Create session with appropriate timeouts and security settings
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=20,  # Higher limit for external API
                ttl_dns_cache=300,
                use_dns_cache=True,
                ssl=True  # Ensure SSL for external API
            )
            
            # Secure headers with API key masking for logs
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'AI-Documentation-Cache/1.0'
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
    
    async def _make_request(self, prompt: str, **kwargs) -> str:
        """
        Make request to OpenAI Chat Completions API.
        
        Args:
            prompt: Formatted prompt text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Raw response text from OpenAI
            
        Raises:
            LLMProviderError: When request fails
            LLMProviderTimeoutError: When request times out
        """
        await self._ensure_session()
        
        # Prepare request payload according to OpenAI Chat Completions API
        payload = {
            'model': kwargs.get('model', self.model),
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
        }
        
        # Add optional parameters
        if 'top_p' in kwargs:
            payload['top_p'] = kwargs['top_p']
        if 'frequency_penalty' in kwargs:
            payload['frequency_penalty'] = kwargs['frequency_penalty']
        if 'presence_penalty' in kwargs:
            payload['presence_penalty'] = kwargs['presence_penalty']
        
        url = f"{self.api_base}/chat/completions"
        
        try:
            logger.debug(f"Making OpenAI request to {url}")
            
            async with self.session.post(url, json=payload) as response:
                # Handle OpenAI API rate limiting and errors
                if response.status == 401:
                    raise LLMProviderError("OpenAI API authentication failed - check API key")
                elif response.status == 429:
                    # Rate limiting - should trigger circuit breaker
                    error_text = await response.text()
                    raise LLMProviderError(f"OpenAI rate limit exceeded: {error_text}")
                elif response.status == 400:
                    error_text = await response.text()
                    raise LLMProviderError(f"OpenAI bad request: {error_text}")
                elif response.status == 500:
                    error_text = await response.text()
                    raise LLMProviderError(f"OpenAI server error: {error_text}")
                elif response.status != 200:
                    error_text = await response.text()
                    raise LLMProviderError(f"OpenAI request failed with status {response.status}: {error_text}")
                
                # Parse OpenAI response format
                response_data = await response.json()
                
                if 'error' in response_data:
                    error_info = response_data['error']
                    raise LLMProviderError(f"OpenAI API error: {error_info.get('message', 'Unknown error')}")
                
                if 'choices' not in response_data or not response_data['choices']:
                    raise LLMProviderError("Invalid OpenAI response format: missing 'choices'")
                
                choice = response_data['choices'][0]
                if 'message' not in choice or 'content' not in choice['message']:
                    raise LLMProviderError("Invalid OpenAI response format: missing message content")
                
                response_text = choice['message']['content']
                
                if not response_text or not response_text.strip():
                    raise LLMProviderError("Empty response from OpenAI")
                
                # Log usage information (without exposing API key)
                usage = response_data.get('usage', {})
                logger.debug(f"OpenAI response received", extra={
                    "tokens_used": usage.get('total_tokens', 0),
                    "prompt_tokens": usage.get('prompt_tokens', 0),
                    "completion_tokens": usage.get('completion_tokens', 0)
                })
                
                return response_text.strip()
                
        except asyncio.TimeoutError:
            logger.error(f"OpenAI request timeout after {self.timeout}s")
            raise LLMProviderTimeoutError(f"OpenAI request timed out after {self.timeout}s")
        
        except aiohttp.ClientError as e:
            logger.error(f"OpenAI client error: {e}")
            raise LLMProviderError(f"OpenAI connection error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            raise LLMProviderError(f"Unexpected OpenAI error: {str(e)}")
    
    async def list_models(self) -> Dict[str, Any]:
        """
        List available models from OpenAI.
        
        Returns:
            Dictionary with available models information
        """
        await self._ensure_session()
        
        try:
            url = f"{self.api_base}/models"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model['id'] for model in data.get('data', []) 
                             if model.get('id', '').startswith(('gpt-', 'text-', 'davinci', 'curie', 'babbage', 'ada'))]
                    
                    return {
                        'models': sorted(models),
                        'count': len(models),
                        'endpoint': 'OpenAI API'
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
        Check OpenAI health and availability.
        
        Returns:
            Health status dictionary
        """
        try:
            await self._ensure_session()
            
            # Test with a simple completion request
            url = f"{self.api_base}/chat/completions"
            test_payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': 'Respond with just: OK'}],
                'max_tokens': 10,
                'temperature': 0.1
            }
            
            async with asyncio.wait_for(
                self.session.post(url, json=test_payload),
                timeout=10.0
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'choices' in data and data['choices']:
                        return {
                            "provider": "openai",
                            "status": "healthy",
                            "model": self.model,
                            "circuit_breaker": "closed",
                            "api_endpoint": self.api_base
                        }
                elif response.status == 401:
                    return {
                        "provider": "openai",
                        "status": "unhealthy",
                        "error": "Authentication failed - check API key",
                        "api_endpoint": self.api_base
                    }
                elif response.status == 429:
                    return {
                        "provider": "openai",
                        "status": "rate_limited",
                        "error": "API rate limit exceeded",
                        "api_endpoint": self.api_base
                    }
                
                return {
                    "provider": "openai",
                    "status": "unhealthy",
                    "error": f"Unexpected response status: {response.status}",
                    "api_endpoint": self.api_base
                }
                
        except asyncio.TimeoutError:
            return {
                "provider": "openai",
                "status": "unhealthy",
                "error": "Health check timeout",
                "api_endpoint": self.api_base
            }
        except Exception as e:
            return {
                "provider": "openai",
                "status": "unhealthy",
                "error": str(e),
                "api_endpoint": self.api_base,
                "circuit_breaker": "open" if "Circuit breaker" in str(e) else "unknown"
            }
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("OpenAI provider session closed")