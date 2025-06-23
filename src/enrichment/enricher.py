# src/enrichment/enricher.py

from typing import Any, Dict, Optional, List
import logging
from src.enrichment.models import EnrichmentTask, GapAnalysisResult
from src.enrichment.analyzers import GapAnalyzer, SimpleGapAnalyzer
from src.enrichment.tasks import ContentAcquisitionManager, SimpleContentAcquisitionManager
from src.enrichment.lifecycle import EnrichmentLifecycleManager
from src.database.manager import DatabaseManager
from src.clients.github import GitHubClient
from src.clients.webscraper import WebScrapingClient
from src.processors.content_processor import ContentProcessingPipeline
from src.search.orchestrator import SearchOrchestrator
from src.enrichment.exceptions import EnrichmentException, GapAnalysisException, ContentAcquisitionException
import asyncio

logger = logging.getLogger(__name__)

class KnowledgeEnricher:
    """
    Main entry point for the Knowledge Enrichment Engine.
    Handles orchestration of gap analysis, content acquisition, and enrichment workflows.
    Integrates with database, content processing, and external acquisition services.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        github_client: GitHubClient,
        webscraper_client: WebScrapingClient,
        content_processor: ContentProcessingPipeline,
        search_orchestrator: SearchOrchestrator,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.db_manager = db_manager
        self.github_client = github_client
        self.webscraper_client = webscraper_client
        self.content_processor = content_processor
        self.search_orchestrator = search_orchestrator
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def enrich(self, task: EnrichmentTask) -> None:
        """
        Orchestrate the enrichment workflow for a given task.
        """
        try:
            self.logger.info(f"Starting enrichment for task {task.task_id}")
            # 1. Perform gap analysis using GapAnalyzer
            gap_analyzer = SimpleGapAnalyzer(self.db_manager, self.config)
            gap_result = await gap_analyzer.analyze(task)

            # 2. Acquire missing content using ContentAcquisitionManager
            acquisition_manager = SimpleContentAcquisitionManager(self.github_client, self.webscraper_client, self.config)
            acquired = await acquisition_manager.acquire(gap_result, task)

            # 3. Process and store new content via ContentProcessingPipeline
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
            await self.db_manager.update_enrichment_status(task.task_id, "completed")
            self.logger.info(f"Enrichment completed for task {task.task_id}")

            # 5. Trigger background enrichment tasks as needed (stub, can be expanded)
            # Example: If more gaps found, enqueue additional tasks (not implemented here)
        except (GapAnalysisException, ContentAcquisitionException) as e:
            self.logger.error(f"Enrichment failed for task {task.task_id}: {e}")
            await self.db_manager.update_enrichment_status(task.task_id, "failed")
            raise EnrichmentException(f"Enrichment failed for task {task.task_id}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during enrichment for task {task.task_id}: {e}")
            await self.db_manager.update_enrichment_status(task.task_id, "failed")
            raise EnrichmentException(f"Unexpected error during enrichment for task {task.task_id}") from e

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
        self.logger = logger or logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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

            # 4. Update enrichment progress/status
            await self.db_manager.update_enrichment_status(task.task_id, "completed")
            self.logger.info(f"Workflow completed for task {task.task_id}")

        except (GapAnalysisException, ContentAcquisitionException) as e:
            self.logger.error(f"Workflow failed for task {task.task_id}: {e}")
            await self.db_manager.update_enrichment_status(task.task_id, "failed")
            raise EnrichmentException(f"Workflow failed for task {task.task_id}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in workflow for task {task.task_id}: {e}")
            await self.db_manager.update_enrichment_status(task.task_id, "failed")
            raise EnrichmentException(f"Unexpected error in workflow for task {task.task_id}") from e