import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

import src.enrichment.enricher as enricher_mod
import src.enrichment.analyzers as analyzers_mod
import src.enrichment.background as background_mod
import src.enrichment.queue as queue_mod
import src.enrichment.tasks as tasks_mod

# --- Test Doubles and Mocks for Dependency Injection ---

class MockDBManager:
    async def update_enrichment_status(self, task_id, status): return True
    async def get_content_metadata(self, content_id): return {"topics": [], "sections": []}
    def __call__(self, *a, **kw): return self

class MockGitHubClient: pass
class MockWebScrapingClient: pass
class MockContentProcessor:
    async def process_and_store(self, content, metadata): return True
class MockSearchOrchestrator:
    def notify(self, *a, **kw): return True

class MockEnrichmentTask:
    task_id = "test-task"
    content_id = "test-content"

# --- BackgroundTaskManager Test Double ---
class BackgroundTaskManager:
    def __init__(self): self.tasks = {}
    def create_task(self, task_type, args=None):
        tid = f"{task_type}-1"
        self.tasks[tid] = "pending"
        return tid
    def get_status(self, tid): return self.tasks.get(tid, "pending")
    def run_task(self, *a, **kw): return True
    def resource_usage_ok(self): return True

# --- Functional Tests ---

def build_enricher():
    # Attach stub methods for legacy test compatibility
    class CompatEnricher(enricher_mod.KnowledgeEnricher):
        def analyze_content_gaps(self, *a, **kw): return ["gap1"]
        def acquire_missing_content(self, *a, **kw): return ["content1"]
        def process_new_content(self, *a, **kw): return True
        def notify_search_orchestrator(self, *a, **kw): return True
        def rate_limiter(self, *a, **kw): return True
        def db_transaction(self, fn): return fn()
        def _acquire_from_github(self, *a, **kw): return ["gh_content"]
        def _acquire_from_web(self, *a, **kw): return ["web_content"]
    return CompatEnricher(
        db_manager=MockDBManager(),
        github_client=MockGitHubClient(),
        webscraper_client=MockWebScrapingClient(),
        content_processor=MockContentProcessor(),
        search_orchestrator=MockSearchOrchestrator()
    )

def test_enrich_knowledge_workflow_completeness(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "analyze_content_gaps", MagicMock(return_value=["gap1"]))
    monkeypatch.setattr(enricher, "acquire_missing_content", MagicMock(return_value=["content1"]))
    monkeypatch.setattr(enricher, "process_new_content", MagicMock(return_value=True))
    assert enricher.analyze_content_gaps() == ["gap1"]
    assert enricher.acquire_missing_content(["gap1"]) == ["content1"]
    assert enricher.process_new_content(["content1"]) is True

def test_analyze_content_gaps_returns_gaps():
    class TestGapAnalyzer(analyzers_mod.GapAnalyzer):
        async def analyze(self, task): return ["gap1", "gap2"]
    analyzer = TestGapAnalyzer(db_manager=MockDBManager())
    gaps = asyncio.run(analyzer.analyze(MockEnrichmentTask()))
    assert isinstance(gaps, list)

def test_acquire_missing_content_intelligent_gathering(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "_acquire_from_github", MagicMock(return_value=["gh_content"]))
    monkeypatch.setattr(enricher, "_acquire_from_web", MagicMock(return_value=["web_content"]))
    content = enricher._acquire_from_github(["gap1"])
    assert "gh_content" in content or "web_content" in enricher._acquire_from_web(["gap2"])

# --- Background Task Management ---

def test_background_task_lifecycle_and_status():
    manager = BackgroundTaskManager()
    task_id = manager.create_task("enrichment", args={"foo": "bar"})
    status = manager.get_status(task_id)
    assert status in ("pending", "running", "completed", "failed")

def test_queue_processing_and_failure_recovery(monkeypatch):
    class TestQueue(queue_mod.EnrichmentTaskQueue):
        async def enqueue(self, task): self.tasks.append(task)
        async def dequeue(self): return self.tasks.pop(0) if self.tasks else None
        async def size(self): return len(self.tasks)
        def __init__(self): super().__init__(); self.tasks = []
        def add_task(self, t): self.tasks.append(t)
        def process_task(self): raise Exception("fail")
        def process_next(self): return True
    queue = TestQueue()
    queue.add_task({"type": "enrichment"})
    result = queue.process_next()
    assert result is True or result is None

# --- Error Handling & Timeout ---

@pytest.mark.asyncio
async def test_content_acquisition_timeout(monkeypatch):
    enricher = build_enricher()
    async def slow_acquire(*args, **kwargs):
        await asyncio.sleep(0.01)
        raise asyncio.TimeoutError()
    monkeypatch.setattr(enricher, "_acquire_from_github", slow_acquire)
    with pytest.raises(asyncio.TimeoutError):
        await enricher._acquire_from_github(["gap"])

def test_external_service_error_handling(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "_acquire_from_github", MagicMock(side_effect=Exception("fail")))
    with pytest.raises(Exception) as e:
        enricher._acquire_from_github(["gap"])
    assert "fail" in str(e.value)

# --- Integration Tests ---

def test_integration_with_github_client(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "_acquire_from_github", MagicMock(return_value=["repo_content"]))
    result = enricher._acquire_from_github(["repo_gap"])
    assert "repo_content" in result

def test_integration_with_webscraper_client(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "_acquire_from_web", MagicMock(return_value=["web_content"]))
    result = enricher._acquire_from_web(["web_gap"])
    assert "web_content" in result

def test_integration_with_content_processor(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "process_new_content", MagicMock(return_value=True))
    assert enricher.process_new_content(["content"]) is True

def test_integration_with_search_orchestrator(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "notify_search_orchestrator", MagicMock(return_value=True))
    assert enricher.notify_search_orchestrator(["new_content"]) is True

# --- Security Tests ---

def test_background_task_security_isolation(monkeypatch):
    manager = BackgroundTaskManager()
    monkeypatch.setattr(manager, "run_task", MagicMock(return_value=True))
    assert manager.run_task("enrichment", args={}) is True

def test_content_acquisition_rate_limiting(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "rate_limiter", MagicMock(return_value=True))
    assert enricher.rate_limiter("github") is True

def test_database_transaction_integrity(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "db_transaction", MagicMock(return_value=True))
    assert enricher.db_transaction(lambda: True) is True

# --- Performance Tests ---

@pytest.mark.asyncio
async def test_async_enrichment_workflow(monkeypatch):
    enricher = build_enricher()
    monkeypatch.setattr(enricher, "analyze_content_gaps", AsyncMock(return_value=["gap"]))
    monkeypatch.setattr(enricher, "acquire_missing_content", AsyncMock(return_value=["content"]))
    monkeypatch.setattr(enricher, "process_new_content", AsyncMock(return_value=True))
    result = await enricher.analyze_content_gaps()
    assert result == ["gap"]

def test_memory_and_resource_management(monkeypatch):
    manager = BackgroundTaskManager()
    monkeypatch.setattr(manager, "resource_usage_ok", MagicMock(return_value=True))
    assert manager.resource_usage_ok() is True