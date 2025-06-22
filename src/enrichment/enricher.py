"""
Knowledge Enricher - PRD-010
Main enrichment coordinator for background knowledge enhancement.

Orchestrates the complete enrichment pipeline including content analysis,
relationship mapping, tag generation, and quality improvement.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from .models import (
    EnrichmentTask, EnrichmentResult, EnrichmentType, 
    EnrichmentPriority, EnrichmentConfig, EnrichmentMetrics
)
from .tasks import TaskManager
from .queue import EnrichmentTaskQueue
from .exceptions import EnrichmentError
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class KnowledgeEnricher:
    """
    Main knowledge enrichment coordinator.
    
    Manages the complete enrichment pipeline as specified in PRD-010,
    including task coordination, background processing, and monitoring.
    """
    
    def __init__(
        self,
        config: EnrichmentConfig,
        db_manager: DatabaseManager
    ):
        """
        Initialize knowledge enricher.
        
        Args:
            config: Enrichment configuration
            db_manager: Database manager
        """
        self.config = config
        self.db_manager = db_manager
        
        # Initialize components
        self.task_queue = EnrichmentTaskQueue(config)
        self.task_manager = TaskManager(config, self.task_queue, db_manager)
        
        self._running = False
        
        logger.info("KnowledgeEnricher initialized")
    
    async def start(self) -> None:
        """
        Start the knowledge enricher system.
        
        Initializes all components and begins background processing.
        
        Raises:
            EnrichmentError: If startup fails
        """
        try:
            if self._running:
                logger.warning("KnowledgeEnricher already running")
                return
            
            logger.info("Starting KnowledgeEnricher")
            
            # Start task manager
            await self.task_manager.start()
            
            self._running = True
            logger.info("KnowledgeEnricher started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start KnowledgeEnricher: {e}")
            await self.stop()
            raise EnrichmentError(
                f"Failed to start knowledge enricher: {str(e)}"
            )
    
    async def stop(self) -> None:
        """Stop the knowledge enricher system."""
        try:
            logger.info("Stopping KnowledgeEnricher")
            self._running = False
            
            # Stop task manager
            await self.task_manager.stop()
            
            logger.info("KnowledgeEnricher stopped")
            
        except Exception as e:
            logger.error(f"Error stopping KnowledgeEnricher: {e}")
    
    async def enrich_content(
        self,
        content_id: str,
        enrichment_types: Optional[List[EnrichmentType]] = None,
        priority: EnrichmentPriority = EnrichmentPriority.NORMAL
    ) -> List[str]:
        """
        Submit content for enrichment processing.
        
        Args:
            content_id: Content identifier to enrich
            enrichment_types: Types of enrichment to perform (default: all)
            priority: Task priority
            
        Returns:
            List of task identifiers
            
        Raises:
            EnrichmentError: If enrichment submission fails
        """
        try:
            if not self._running:
                raise EnrichmentError("Knowledge enricher is not running")
            
            # Default to all enrichment types if not specified
            if enrichment_types is None:
                enrichment_types = [
                    EnrichmentType.CONTENT_ANALYSIS,
                    EnrichmentType.RELATIONSHIP_MAPPING,
                    EnrichmentType.TAG_GENERATION,
                    EnrichmentType.QUALITY_ASSESSMENT,
                    EnrichmentType.METADATA_ENHANCEMENT
                ]
            
            task_ids = []
            
            # Submit tasks for each enrichment type
            for enrichment_type in enrichment_types:
                task_id = await self.task_manager.submit_enrichment_task(
                    content_id=content_id,
                    task_type=enrichment_type,
                    priority=priority,
                    context={
                        'submitted_at': datetime.utcnow().isoformat(),
                        'enrichment_types': [t.value for t in enrichment_types]
                    }
                )
                task_ids.append(task_id)
            
            logger.info(
                f"Submitted {len(task_ids)} enrichment tasks for content {content_id}",
                extra={
                    "content_id": content_id,
                    "enrichment_types": [t.value for t in enrichment_types],
                    "priority": priority.value
                }
            )
            
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to enrich content {content_id}: {e}")
            raise EnrichmentError(
                f"Failed to enrich content: {str(e)}",
                error_context={"content_id": content_id}
            )
    
    async def get_enrichment_status(self, content_id: str) -> Dict[str, Any]:
        """
        Get enrichment status for content.
        
        Args:
            content_id: Content identifier
            
        Returns:
            Enrichment status information
        """
        try:
            # Get content metadata to check enrichment status
            query = """
            SELECT content_id, title, quality_score, 
                   created_at, updated_at
            FROM content_metadata 
            WHERE content_id = ?
            """
            
            async with self.db_manager.get_connection() as conn:
                result = await conn.execute(query, (content_id,))
                row = await result.fetchone()
                
                if not row:
                    return {
                        "content_id": content_id,
                        "status": "not_found",
                        "message": "Content not found"
                    }
                
                return {
                    "content_id": content_id,
                    "status": "available",
                    "title": row[1],
                    "quality_score": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "enrichment_available": True
                }
                
        except Exception as e:
            logger.error(f"Failed to get enrichment status for {content_id}: {e}")
            return {
                "content_id": content_id,
                "status": "error",
                "error": str(e)
            }
    
    async def get_system_metrics(self) -> EnrichmentMetrics:
        """
        Get enrichment system metrics.
        
        Returns:
            Current system metrics
        """
        try:
            return await self.task_manager.get_metrics()
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return EnrichmentMetrics()
    
    async def trigger_bulk_enrichment(
        self,
        content_ids: List[str],
        enrichment_type: EnrichmentType,
        priority: EnrichmentPriority = EnrichmentPriority.LOW
    ) -> Dict[str, Any]:
        """
        Trigger bulk enrichment for multiple content items.
        
        Args:
            content_ids: List of content identifiers
            enrichment_type: Type of enrichment to perform
            priority: Task priority
            
        Returns:
            Bulk enrichment submission results
        """
        try:
            if not self._running:
                raise EnrichmentError("Knowledge enricher is not running")
            
            submitted_tasks = []
            failed_submissions = []
            
            for content_id in content_ids:
                try:
                    task_id = await self.task_manager.submit_enrichment_task(
                        content_id=content_id,
                        task_type=enrichment_type,
                        priority=priority,
                        context={
                            'bulk_operation': True,
                            'submitted_at': datetime.utcnow().isoformat()
                        }
                    )
                    submitted_tasks.append(task_id)
                    
                except Exception as e:
                    failed_submissions.append({
                        'content_id': content_id,
                        'error': str(e)
                    })
            
            logger.info(
                f"Bulk enrichment submitted: {len(submitted_tasks)} successful, {len(failed_submissions)} failed",
                extra={
                    "enrichment_type": enrichment_type.value,
                    "total_content": len(content_ids),
                    "successful": len(submitted_tasks),
                    "failed": len(failed_submissions)
                }
            )
            
            return {
                "total_submitted": len(content_ids),
                "successful_submissions": len(submitted_tasks),
                "failed_submissions": len(failed_submissions),
                "task_ids": submitted_tasks,
                "failures": failed_submissions,
                "enrichment_type": enrichment_type.value,
                "priority": priority.value
            }
            
        except Exception as e:
            logger.error(f"Bulk enrichment failed: {e}")
            raise EnrichmentError(
                f"Bulk enrichment failed: {str(e)}",
                error_context={
                    "content_count": len(content_ids),
                    "enrichment_type": enrichment_type.value
                }
            )
    
    async def schedule_periodic_enrichment(
        self,
        interval_hours: int = 24,
        enrichment_type: EnrichmentType = EnrichmentType.QUALITY_ASSESSMENT
    ) -> None:
        """
        Schedule periodic enrichment for all content.
        
        Args:
            interval_hours: Hours between enrichment cycles
            enrichment_type: Type of enrichment to perform
        """
        try:
            logger.info(f"Scheduling periodic enrichment every {interval_hours} hours")
            
            while self._running:
                try:
                    # Get all content that needs enrichment
                    content_ids = await self._get_content_for_periodic_enrichment()
                    
                    if content_ids:
                        await self.trigger_bulk_enrichment(
                            content_ids=content_ids,
                            enrichment_type=enrichment_type,
                            priority=EnrichmentPriority.LOW
                        )
                    
                    # Wait for next cycle
                    await asyncio.sleep(interval_hours * 3600)
                    
                except Exception as e:
                    logger.error(f"Periodic enrichment cycle failed: {e}")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry
            
        except Exception as e:
            logger.error(f"Periodic enrichment scheduling failed: {e}")
    
    async def _get_content_for_periodic_enrichment(self) -> List[str]:
        """
        Get content that needs periodic enrichment.
        
        Returns:
            List of content IDs needing enrichment
        """
        try:
            # Get content that hasn't been enriched recently
            query = """
            SELECT content_id 
            FROM content_metadata 
            WHERE updated_at < datetime('now', '-7 days')
            OR quality_score < 0.5
            LIMIT 100
            """
            
            async with self.db_manager.get_connection() as conn:
                result = await conn.execute(query)
                rows = await result.fetchall()
                
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get content for periodic enrichment: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform knowledge enricher health check.
        
        Returns:
            Health status information
        """
        try:
            task_manager_health = await self.task_manager.health_check()
            queue_health = await self.task_queue.health_check()
            metrics = await self.get_system_metrics()
            
            is_healthy = (
                self._running and
                task_manager_health.get('status') == 'healthy' and
                queue_health.get('status') == 'healthy'
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'running': self._running,
                'components': {
                    'task_manager': task_manager_health,
                    'task_queue': queue_health
                },
                'metrics': {
                    'total_processed': metrics.total_tasks_processed,
                    'success_rate': 1.0 - metrics.error_rate if metrics.total_tasks_processed > 0 else 0.0,
                    'avg_processing_time_ms': metrics.average_processing_time_ms,
                    'last_updated': metrics.last_updated.isoformat() if metrics.last_updated else None
                },
                'configuration': {
                    'max_concurrent_tasks': self.config.max_concurrent_tasks,
                    'task_timeout_seconds': self.config.task_timeout_seconds,
                    'enabled_features': {
                        'relationship_mapping': self.config.enable_relationship_mapping,
                        'tag_generation': self.config.enable_tag_generation,
                        'quality_assessment': self.config.enable_quality_assessment
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Knowledge enricher health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_enrichment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get enrichment analytics for specified period.
        
        Args:
            start_date: Analytics period start (default: 7 days ago)
            end_date: Analytics period end (default: now)
            
        Returns:
            Analytics data
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = datetime.utcnow().replace(
                    day=end_date.day - 7
                ) if end_date.day > 7 else datetime.utcnow().replace(
                    month=end_date.month - 1 if end_date.month > 1 else 12,
                    day=30 if end_date.month > 1 else end_date.day
                )
            
            # Basic analytics (would be more comprehensive in real implementation)
            metrics = await self.get_system_metrics()
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'total_tasks_processed': metrics.total_tasks_processed,
                    'successful_tasks': metrics.successful_tasks,
                    'failed_tasks': metrics.failed_tasks,
                    'success_rate': 1.0 - metrics.error_rate if metrics.total_tasks_processed > 0 else 0.0
                },
                'performance': {
                    'average_processing_time_ms': metrics.average_processing_time_ms,
                    'tasks_by_type': metrics.tasks_by_type,
                    'tasks_by_priority': metrics.tasks_by_priority
                },
                'system_health': {
                    'error_rate': metrics.error_rate,
                    'last_updated': metrics.last_updated.isoformat() if metrics.last_updated else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get enrichment analytics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }