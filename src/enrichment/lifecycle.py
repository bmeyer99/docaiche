# src/enrichment/lifecycle.py

from typing import Any, Dict, Optional
import logging
from abc import ABC, abstractmethod
from src.enrichment.models import EnrichmentTask
from src.enrichment.exceptions import EnrichmentException

logger = logging.getLogger(__name__)

class EnrichmentLifecycleManager(ABC):
    """
    Abstract base class for managing the lifecycle of enrichment tasks.
    Handles state transitions, status updates, and cleanup.
    """

    def __init__(self, db_manager: Any, config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def update_status(self, task: EnrichmentTask, status: str) -> None:
        """
        Update the status of an enrichment task.
        # TODO: IMPLEMENTATION ENGINEER - Implement status update logic:
        """
        pass

    @abstractmethod
    async def cleanup(self, task: EnrichmentTask) -> None:
        """
        Perform cleanup after enrichment task completion or failure.
        # TODO: IMPLEMENTATION ENGINEER - Implement cleanup logic:
        """
        pass

class SimpleEnrichmentLifecycleManager(EnrichmentLifecycleManager):
    """
    Concrete implementation of EnrichmentLifecycleManager for PRD-010.
    """

    async def update_status(self, task: EnrichmentTask, status: str) -> None:
        """
        Update task status in database, log status transitions, handle error cases and retries.
        """
        try:
            await self.db_manager.update_enrichment_status(task.task_id, status)
            self.logger.info(f"Updated status for task {task.task_id} to {status}")
        except Exception as e:
            self.logger.error(f"Failed to update status for task {task.task_id}: {e}")
            raise EnrichmentException(f"Failed to update status for task {task.task_id}") from e

    async def cleanup(self, task: EnrichmentTask) -> None:
        """
        Remove temporary data/resources, finalize task in database, log cleanup actions.
        """
        try:
            await self.db_manager.finalize_enrichment_task(task.task_id)
            self.logger.info(f"Cleanup complete for task {task.task_id}")
        except Exception as e:
            self.logger.error(f"Cleanup failed for task {task.task_id}: {e}")
            raise EnrichmentException(f"Cleanup failed for task {task.task_id}") from e