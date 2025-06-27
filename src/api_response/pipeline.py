"""
APIResponsePipeline: Orchestrates formatting and caching of API responses.
"""
from typing import Any, Dict, Optional
from .formatters import BaseAPIFormatter, SimpleJSONFormatter
from .caching import ResponseCacheHandler
from .exceptions import APIResponseError

class APIResponsePipeline:
    """
    Handles the processing of API responses, including formatting and caching.
    """
    def __init__(
        self,
        formatter: BaseAPIFormatter,
        cache_handler: ResponseCacheHandler,
        enable_cache: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.formatter = formatter or SimpleJSONFormatter()
        self.cache_handler = cache_handler
        self.enable_cache = enable_cache
        self.config = config or {}

    async def process_response(
        self,
        response_data: Any,
        context: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        use_cache: Optional[bool] = None,
        formatter_name: Optional[str] = None,
    ) -> Any:
        """
        Process the response data through the pipeline.
        """
        use_cache = use_cache if use_cache is not None else self.enable_cache

        if use_cache and cache_key:
            cached = await self.cache_handler.get(cache_key)
            if cached and cached.value is not None:
                return cached.value

        try:
            formatted_response = self.formatter.format(response_data, context=context)
        except Exception as e:
            raise APIResponseError(f"Error formatting response: {e}")

        if use_cache and cache_key:
            await self.cache_handler.set(cache_key, formatted_response)

        return formatted_response