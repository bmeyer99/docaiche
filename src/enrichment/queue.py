# src/enrichment/queue.py

from typing import Any, Dict, Optional, List
import logging
from abc import ABC, abstractmethod
from src.enrichment.models import EnrichmentTask

logger = logging.getLogger(__name__)


class EnrichmentTaskQueue(ABC):
    """
    Abstract base class for managing the queue of enrichment tasks.
    Handles enqueueing, dequeueing, and task prioritization.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def enqueue(self, task: EnrichmentTask) -> None:
        """
        Add an enrichment task to the queue.
        # TODO: IMPLEMENTATION ENGINEER - Implement enqueue logic:
        """
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[EnrichmentTask]:
        """
        Retrieve the next enrichment task from the queue.
        # TODO: IMPLEMENTATION ENGINEER - Implement dequeue logic:
        """
        pass

    @abstractmethod
    async def size(self) -> int:
        """
        Get the current size of the enrichment task queue.
        # TODO: IMPLEMENTATION ENGINEER - Implement size logic:
        """
        pass


class InMemoryEnrichmentTaskQueue(EnrichmentTaskQueue):
    """
    Simple in-memory implementation of EnrichmentTaskQueue for PRD-010.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._queue: List[EnrichmentTask] = []

    async def enqueue(self, task: EnrichmentTask) -> None:
        # Deduplication: do not add if task_id already exists
        if any(t.task_id == task.task_id for t in self._queue):
            self.logger.info(f"Task {task.task_id} already in queue, skipping enqueue.")
            return
        self._queue.append(task)
        self.logger.info(
            f"Enqueued task {task.task_id}. Queue size: {len(self._queue)}"
        )

    async def dequeue(self) -> Optional[EnrichmentTask]:
        if not self._queue:
            self.logger.info("Queue is empty on dequeue.")
            return None
        task = self._queue.pop(0)
        self.logger.info(
            f"Dequeued task {task.task_id}. Queue size: {len(self._queue)}"
        )
        return task

    async def size(self) -> int:
        return len(self._queue)
