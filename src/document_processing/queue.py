"""
Processing Queue Management.
Implements PRD-006: Manages asynchronous document processing, error handling, retry logic, and progress tracking.
"""

import logging
from typing import Optional
from fastapi import HTTPException
from src.document_processing.models import ProcessingJob, ProcessingStatus
import json

logger = logging.getLogger(__name__)


class ProcessingQueueManager:
    """
    Manages Redis-based processing queue and job status.
    """

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.queue_key = "document_processing_queue"
        self.status_prefix = "processing_job_status:"

    async def enqueue_job(self, job: ProcessingJob) -> bool:
        """
        Adds a job to the processing queue.
        """
        try:
            await self.cache_manager.rpush(self.queue_key, json.dumps(job.dict()))
            await self.update_job_status(job.job_id, job.status, job.progress)
            logger.info(f"Enqueued job {job.job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue job {job.job_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to enqueue job")

    async def dequeue_job(self) -> Optional[ProcessingJob]:
        """
        Gets the next job from the processing queue.
        """
        try:
            job_data = await self.cache_manager.lpop(self.queue_key)
            if job_data is None:
                return None
            job_dict = json.loads(job_data)
            job = ProcessingJob(**job_dict)
            logger.info(f"Dequeued job {job.job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            raise HTTPException(status_code=500, detail="Failed to dequeue job")

    async def update_job_status(
        self, job_id: str, status: ProcessingStatus, progress: float
    ):
        """
        Updates the status and progress of a processing job.
        """
        try:
            status_key = f"{self.status_prefix}{job_id}"
            status_data = {"status": status, "progress": progress}
            await self.cache_manager.set(status_key, json.dumps(status_data))
            logger.info(
                f"Updated status for job {job_id}: {status}, progress={progress}"
            )
        except Exception as e:
            logger.error(f"Failed to update job status for {job_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update job status")
