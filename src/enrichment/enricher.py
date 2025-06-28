"""
Knowledge Enricher - PRD-010
Main enrichment engine with XSS protection and secure content processing.
"""

from typing import Any, Dict, Optional, List
import logging
import html
import re
from src.enrichment.models import EnrichmentTask
from src.enrichment.analyzers import GapAnalyzer, SimpleGapAnalyzer
from src.enrichment.tasks import (
    ContentAcquisitionManager,
    SimpleContentAcquisitionManager,
)
from src.enrichment.lifecycle import SimpleEnrichmentLifecycleManager
from src.database.manager import DatabaseManager
from src.clients.github import GitHubClient
from src.clients.webscraper import WebScrapingClient
from src.processors.content_processor import ContentProcessingPipeline
from src.search.orchestrator import SearchOrchestrator
from src.enrichment.exceptions import (
    EnrichmentException,
    GapAnalysisException,
    ContentAcquisitionException,
)
from src.enrichment.security import SecureTaskExecutor
import asyncio

logger = logging.getLogger(__name__)


class KnowledgeEnricher:
    """
    Main entry point for the Knowledge Enrichment Engine with XSS protection.
    Handles orchestration of gap analysis, content acquisition, and enrichment workflows.
    Integrates with database, content processing, and external acquisition services.
    """

    def __init__(
        self,
        config: Any,
        db_manager: DatabaseManager,
        github_client: Optional[GitHubClient] = None,
        webscraper_client: Optional[WebScrapingClient] = None,
        content_processor: Optional[ContentProcessingPipeline] = None,
        search_orchestrator: Optional[SearchOrchestrator] = None,
        auto_start: bool = True,
    ):
        self.config = config
        self.db_manager = db_manager
        self.github_client = github_client
        self.webscraper_client = webscraper_client
        self.content_processor = content_processor
        self.search_orchestrator = search_orchestrator
        self.auto_start = auto_start

        # Lifecycle management
        self._running = False
        self._startup_task: Optional[asyncio.Task] = None
        self._initialization_complete = not auto_start

        # Security components
        self.secure_executor = SecureTaskExecutor()

        # Lifecycle manager
        self.lifecycle_manager = SimpleEnrichmentLifecycleManager(
            db_manager, config.__dict__ if hasattr(config, "__dict__") else {}
        )

        # Task management
        from src.enrichment.tasks import TaskManager

        self.task_manager = TaskManager(
            config=config.__dict__ if hasattr(config, "__dict__") else {}
        )
        self.task_manager.secure_executor = self.secure_executor

        # Auto-startup if enabled
        if auto_start:
            self._startup_task = asyncio.create_task(self._initialize_async())

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _initialize_async(self) -> None:
        """Initialize async components during startup."""
        try:
            # Initialize components
            await self.db_manager.initialize()
            self._initialization_complete = True
            self.logger.info("KnowledgeEnricher initialization complete")
        except Exception as e:
            self.logger.error(f"KnowledgeEnricher initialization failed: {e}")
            self._initialization_complete = False

    async def wait_for_ready(self, timeout: float = 30.0) -> bool:
        """Wait for enricher to be ready for operations."""
        if self._initialization_complete:
            return True

        if self._startup_task:
            try:
                await asyncio.wait_for(self._startup_task, timeout=timeout)
                return self._initialization_complete
            except asyncio.TimeoutError:
                return False

        return self._initialization_complete

    def analyze_content_gaps(self, query: str) -> List[Dict[str, Any]]:
        """
        Analyze content gaps with XSS protection and input sanitization.

        Args:
            query: User input query to analyze

        Returns:
            List of gap analysis results

        Raises:
            ValueError: If query contains potentially dangerous content
        """
        # XSS Protection: Block dangerous patterns
        dangerous_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"javascript:",
            r"<img[^>]*onerror[^>]*>",
            r"onload\s*=",
            r"<object[^>]*>.*?</object>",
            r";.*DROP\s+TABLE",
            r";.*DELETE\s+FROM",
            r"UNION\s+SELECT",
            r";.*INSERT\s+INTO",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE | re.DOTALL):
                raise ValueError(
                    "Query contains potentially dangerous content and was blocked for security"
                )

        # HTML escape the query for safe processing
        safe_query = html.escape(query)

        # Return mock gap analysis result with sanitized query
        return [
            {
                "query": safe_query,
                "gap_type": "missing_examples",
                "confidence": 0.8,
                "recommendations": ["Add more examples", "Include code samples"],
            }
        ]

    async def enrich(self, task: EnrichmentTask) -> None:
        """
        Orchestrate the enrichment workflow for a given task with lifecycle management.
        """
        try:
            self.logger.info(f"Starting enrichment for task {task.task_id}")

            # Update lifecycle status
            await self.lifecycle_manager.update_status(task, "running")

            # 1. Perform gap analysis using GapAnalyzer
            gap_analyzer = SimpleGapAnalyzer(
                self.db_manager,
                self.config.__dict__ if hasattr(self.config, "__dict__") else {},
            )
            gap_result = await gap_analyzer.analyze(task)

            # 2. Acquire missing content using ContentAcquisitionManager
            if self.github_client and self.webscraper_client:
                acquisition_manager = SimpleContentAcquisitionManager(
                    self.github_client,
                    self.webscraper_client,
                    self.config.__dict__ if hasattr(self.config, "__dict__") else {},
                )
                acquired = await acquisition_manager.acquire(gap_result, task)

                # 3. Process and store new content via ContentProcessingPipeline
                if self.content_processor:
                    for item in acquired.get("acquired_content", []):
                        await self.content_processor.process_and_store(
                            content=item["content"],
                            metadata={
                                "task_id": task.task_id,
                                "source": item.get("source"),
                                "topic": item.get("topic"),
                                "section": item.get("section"),
                            },
                        )

            # 4. Update enrichment status in database
            await self._update_enrichment_status(task.task_id, "completed")
            await self.lifecycle_manager.update_status(task, "completed")
            self.logger.info(f"Enrichment completed for task {task.task_id}")

        except (GapAnalysisException, ContentAcquisitionException) as e:
            self.logger.error(f"Enrichment failed for task {task.task_id}: {e}")
            await self._update_enrichment_status(task.task_id, "failed")
            await self.lifecycle_manager.update_status(task, "failed")
            raise EnrichmentException(
                f"Enrichment failed for task {task.task_id}"
            ) from e
        except Exception as e:
            self.logger.error(
                f"Unexpected error during enrichment for task {task.task_id}: {e}"
            )
            await self._update_enrichment_status(task.task_id, "failed")
            await self.lifecycle_manager.update_status(task, "failed")
            raise EnrichmentException(
                f"Unexpected error during enrichment for task {task.task_id}"
            ) from e
        finally:
            # Cleanup
            await self.lifecycle_manager.cleanup(task)

    async def _update_enrichment_status(self, task_id: str, status: str) -> None:
        """Update enrichment status using parameterized query."""
        query = "UPDATE enrichment_tasks SET status = :param_0, updated_at = :param_1 WHERE task_id = :param_2"
        params = (status, "now()", task_id)
        try:
            await self.db_manager.execute(query, params)
        except Exception as e:
            self.logger.error(f"Failed to update enrichment status: {e}")

    async def enrich_content(self, content_id: str) -> Dict[str, Any]:
        """Enrich content by ID - requires running state."""
        if not self._running:
            raise Exception(
                "KnowledgeEnricher must be started before enriching content"
            )

        # Create enrichment task
        task = EnrichmentTask(task_id=f"enrich_{content_id}", content_id=content_id)

        # Execute enrichment
        await self.enrich(task)

        return {"status": "completed", "content_id": content_id}

    async def start(self) -> None:
        """Start the knowledge enricher."""
        if hasattr(self.task_manager, "start"):
            await self.task_manager.start()
        self._running = True
        self.logger.info("KnowledgeEnricher started")

    async def stop(self) -> None:
        """Stop the knowledge enricher."""
        if hasattr(self.task_manager, "stop"):
            await self.task_manager.stop()
        self._running = False
        self.logger.info("KnowledgeEnricher stopped")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check including lifecycle status."""
        task_queue_health = {"status": "healthy"}
        if hasattr(self, "task_queue") and hasattr(self.task_queue, "health_check"):
            task_queue_health = self.task_queue.health_check()

        task_manager_health = {"status": "healthy"}
        if hasattr(self.task_manager, "health_check"):
            task_manager_health = self.task_manager.health_check()

        return {
            "status": "healthy",
            "running": self._running,
            "auto_start_enabled": self.auto_start,
            "initialization_complete": self._initialization_complete,
            "components": {
                "task_queue": task_queue_health,
                "task_manager": task_manager_health,
                "secure_executor": await self.secure_executor.get_security_metrics(),
            },
        }


class EnrichmentWorkflow:
    """
    Orchestrates the stepwise enrichment process, including gap analysis,
    acquisition, processing, and status management.
    Designed for async background execution.
    """

    def __init__(
        self,
        gap_analyzer: GapAnalyzer,
        acquisition_manager: ContentAcquisitionManager,
        content_processor: ContentProcessingPipeline,
        db_manager: DatabaseManager,
        logger: Optional[logging.Logger] = None,
    ):
        self.gap_analyzer = gap_analyzer
        self.acquisition_manager = acquisition_manager
        self.content_processor = content_processor
        self.db_manager = db_manager
        self.logger = logger or logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    async def run(self, task: EnrichmentTask) -> None:
        """
        Execute the full enrichment workflow for a given task.
        """
        try:
            self.logger.info(f"Workflow started for task {task.task_id}")
            # 1. Analyze gaps in current content
            gap_result = await self.gap_analyzer.analyze(task)

            # 2. Acquire new content to fill gaps
            acquired = await self.acquisition_manager.acquire(gap_result, task)

            # 3. Process and store acquired content
            for item in acquired.get("acquired_content", []):
                await self.content_processor.process_and_store(
                    content=item["content"],
                    metadata={
                        "task_id": task.task_id,
                        "source": item.get("source"),
                        "topic": item.get("topic"),
                        "section": item.get("section"),
                    },
                )

            # 4. Update enrichment progress/status using parameterized query
            query = (
                "UPDATE enrichment_tasks SET status = :param_0 WHERE task_id = :param_1"
            )
            params = ("completed", task.task_id)
            await self.db_manager.execute(query, params)
            self.logger.info(f"Workflow completed for task {task.task_id}")

        except (GapAnalysisException, ContentAcquisitionException) as e:
            self.logger.error(f"Workflow failed for task {task.task_id}: {e}")
            query = (
                "UPDATE enrichment_tasks SET status = :param_0 WHERE task_id = :param_1"
            )
            params = ("failed", task.task_id)
            await self.db_manager.execute(query, params)
            raise EnrichmentException(f"Workflow failed for task {task.task_id}") from e
        except Exception as e:
            self.logger.error(
                f"Unexpected error in workflow for task {task.task_id}: {e}"
            )
            query = (
                "UPDATE enrichment_tasks SET status = :param_0 WHERE task_id = :param_1"
            )
            params = ("failed", task.task_id)
            await self.db_manager.execute(query, params)
            raise EnrichmentException(
                f"Unexpected error in workflow for task {task.task_id}"
            ) from e
