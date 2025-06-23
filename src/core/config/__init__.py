"""
Configuration stubs for all required system attributes and external dependency stubs.
PRD alignment: PRD-003, PRD-004, PRD-005, PRD-002.
"""

from typing import Dict, Any

class DummyAppConfig:
    environment = "development"
    data_dir = "/tmp"
    api_host = "0.0.0.0"
    api_port = 8080
    debug = True
    log_level = "INFO"

class DummyAIConfig:
    primary_provider = None
    ollama = None
    openai = None
    cache_ttl_seconds = 0

class DummyContentConfig:
    chunk_size_default = 512

class DummyAnythingLLMConfig:
    host = "localhost"
    port = 3001

class DummyGithubConfig:
    api_url = "https://api.github.com"

class DummyScrapingConfig:
    user_agent = "Mozilla/5.0"

class DummyRedisConfig:
    host = "localhost"
    port = 6379

# External dependency stubs for test/dev mode
class DummyRedisStub:
    def __init__(self, *args, **kwargs):
        self._store = {}
    async def get(self, key):
        return self._store.get(key)
    async def set(self, key, value, ex=None):
        self._store[key] = value
    async def ping(self):
        return True

class DummyAnythingLLMStub:
    async def health_check(self):
        return {"status": "healthy", "details": "Stubbed AnythingLLM"}

class DummySystemConfig:
    ai = DummyAIConfig()
    app = DummyAppConfig()
    content = DummyContentConfig()
    anythingllm = DummyAnythingLLMConfig()
    github = DummyGithubConfig()
    scraping = DummyScrapingConfig()
    redis = DummyRedisConfig()

def get_settings():
    # Return a dummy config object with all required attributes
    class DummySettings:
        app = DummyAppConfig()
        anythingllm = DummyAnythingLLMConfig()
        github = DummyGithubConfig()
        scraping = DummyScrapingConfig()
        redis = DummyRedisConfig()
        ai = DummyAIConfig()
        content = DummyContentConfig()
        # Stubs for test/dev
        redis_stub = DummyRedisStub()
        anythingllm_stub = DummyAnythingLLMStub()
    return DummySettings()

def get_configuration_manager():
    class DummyConfigManager:
        def get_config(self):
            return {}
    return DummyConfigManager()

def get_system_configuration():
    return DummySystemConfig()

def reload_configuration():
    return None

# End of file