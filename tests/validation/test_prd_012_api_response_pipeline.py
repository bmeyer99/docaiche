import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.api_response.pipeline import APIResponsePipeline
from src.api_response.formatters import JSONAPIFormatter, SimpleJSONFormatter
from src.api_response.caching import ResponseCacheHandler
from src.api_response.models import CachedResponse
from src.response.generator import ResponseGenerator

@pytest.mark.asyncio
async def test_pipeline_process_response_with_jsonapi_formatter():
    mock_cache = AsyncMock(spec=ResponseCacheHandler)
    formatter = JSONAPIFormatter()
    pipeline = APIResponsePipeline(
        formatter=formatter,
        cache_handler=mock_cache,
        enable_cache=True
    )
    data = {"id": "1", "type": "test", "attributes": {"foo": "bar"}}
    context = {"resource_type": "test"}
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    result = await pipeline.process_response(data, context)
    assert "data" in result
    assert result["data"]["type"] == "test"
    assert result["data"]["attributes"]["foo"] == "bar"

@pytest.mark.asyncio
async def test_pipeline_process_response_with_simplejson_formatter():
    mock_cache = AsyncMock(spec=ResponseCacheHandler)
    formatter = SimpleJSONFormatter()
    pipeline = APIResponsePipeline(
        formatter=formatter,
        cache_handler=mock_cache,
        enable_cache=True
    )
    data = {"foo": "bar"}
    context = {}
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    result = await pipeline.process_response(data, context)
    assert result == {"foo": "bar"}

@pytest.mark.asyncio
async def test_cache_handler_set_get_invalidate(monkeypatch):
    # Simulate Redis client with async methods
    class FakeRedis:
        def __init__(self):
            self.store = {}
        async def set(self, key, value, ex=None):
            self.store[key] = value
        async def get(self, key):
            return self.store.get(key)
        async def delete(self, key):
            self.store.pop(key, None)
    redis = FakeRedis()
    handler = ResponseCacheHandler(redis_client=redis, ttl=10)
    resp = CachedResponse(key="abc", value={"foo": "bar"})
    await handler.set("abc", resp)
    cached = await handler.get("abc")
    assert isinstance(cached, CachedResponse)
    assert cached.value == {"foo": "bar"}
    await handler.invalidate("abc")
    assert await handler.get("abc") is None

def test_jsonapi_formatter_compliance():
    formatter = JSONAPIFormatter()
    data = {"id": "1", "type": "article", "attributes": {"title": "Test"}}
    result = formatter.format(data)
    assert "data" in result
    assert result["data"]["type"] == "article"
    assert "attributes" in result["data"]

def test_simplejson_formatter_output():
    formatter = SimpleJSONFormatter()
    data = {"foo": "bar"}
    result = formatter.format(data)
    assert result == {"foo": "bar"}

def test_cached_response_model_usage():
    resp = CachedResponse(key="k", value={"foo": "bar"})
    assert resp.key == "k"
    assert resp.value == {"foo": "bar"}
    assert hasattr(resp, "created_at")
    assert isinstance(resp.is_expired(), bool)

@pytest.mark.asyncio
async def test_pipeline_integration_with_response_generator(monkeypatch):
    class DummyGenerator:
        async def generate(self, *args, **kwargs):
            return {"foo": "bar"}
    mock_cache = AsyncMock(spec=ResponseCacheHandler)
    formatter = SimpleJSONFormatter()
    pipeline = APIResponsePipeline(
        formatter=formatter,
        cache_handler=mock_cache,
        enable_cache=False
    )
    generator = DummyGenerator()
    data = await generator.generate()
    result = await pipeline.process_response(data)
    assert result == {"foo": "bar"}

@pytest.mark.asyncio
async def test_cache_handler_async_operations():
    # Ensure all cache ops are async and non-blocking
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()
    handler = ResponseCacheHandler(redis_client=redis)
    resp = CachedResponse(key="k", value={"foo": "bar"})
    await handler.set("k", resp)
    await handler.get("k")
    await handler.invalidate("k")
    redis.set.assert_awaited()
    redis.get.assert_awaited()
    redis.delete.assert_awaited()