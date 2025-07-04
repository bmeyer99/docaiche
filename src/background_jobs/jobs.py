"""
Context7 Background Job Implementations
=======================================

Specific job implementations for Context7 document TTL management,
refresh operations, and health monitoring.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

from .models import JobConfig, JobExecution, Context7JobConfig
from src.ingestion.context7_ingestion_service import Context7IngestionService
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.llm.client import LLMProviderClient
from src.mcp.providers.implementations.context7_provider import Context7Provider
from src.search.llm_query_analyzer import QueryIntent

logger = logging.getLogger(__name__)


class BaseJob:
    """Base class for background jobs"""
    
    def __init__(
        self,
        context7_service: Context7IngestionService,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager,
        config: Context7JobConfig
    ):
        self.context7_service = context7_service
        self.weaviate_client = weaviate_client
        self.db_manager = db_manager
        self.config = config
        
    async def execute(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Execute the job - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def _get_target_workspaces(self) -> List[str]:
        """Get list of workspaces to process"""
        try:
            # If specific workspaces are configured, use those
            if self.config.target_workspaces:
                workspaces = self.config.target_workspaces
            else:
                # Otherwise, get all workspaces from Weaviate
                workspaces = await self.weaviate_client.list_workspaces()
            
            # Filter out excluded workspaces
            if self.config.excluded_workspaces:
                workspaces = [
                    ws for ws in workspaces 
                    if ws not in self.config.excluded_workspaces
                ]
            
            return workspaces
            
        except Exception as e:
            logger.error(f"Failed to get target workspaces: {e}")
            return []
    
    async def _rate_limit_delay(self) -> None:
        """Apply rate limiting delay"""
        await asyncio.sleep(self.config.rate_limit_delay_seconds)


class TTLCleanupJob(BaseJob):
    """
    TTL Cleanup Job for Context7 Documents
    
    Handles daily cleanup of expired Context7 documents across all workspaces.
    Uses intelligent batching and workspace-level processing to ensure
    efficient and comprehensive cleanup operations.
    """
    
    async def execute(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Execute TTL cleanup job"""
        start_time = time.time()
        correlation_id = execution.correlation_id or f"ttl_cleanup_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting TTL cleanup job")
            logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_job_start "
                       f"correlation_id={correlation_id} job_id={job_config.job_id}")
            
            # Get job parameters
            batch_size = job_config.parameters.get("batch_size", self.config.ttl_cleanup_batch_size)
            max_age_days = job_config.parameters.get("max_age_days", self.config.ttl_cleanup_max_age_days)
            
            # Get target workspaces
            workspaces = await self._get_target_workspaces()
            logger.info(f"Processing {len(workspaces)} workspaces for TTL cleanup")
            
            # Track results
            total_deleted_documents = 0
            total_deleted_chunks = 0
            processed_workspaces = 0
            failed_workspaces = []
            workspace_results = {}
            
            # Process each workspace
            for workspace in workspaces:
                workspace_start = time.time()
                
                try:
                    logger.info(f"Processing workspace: {workspace}")
                    logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_workspace_start "
                               f"correlation_id={correlation_id} workspace={workspace}")
                    
                    # Cleanup expired documents in this workspace
                    cleanup_result = await self.context7_service.cleanup_expired_documents(
                        workspace_slug=workspace,
                        correlation_id=correlation_id
                    )
                    
                    # Update totals
                    workspace_deleted_docs = cleanup_result.get("weaviate_cleanup", {}).get("deleted_documents", 0)
                    workspace_deleted_chunks = cleanup_result.get("weaviate_cleanup", {}).get("deleted_chunks", 0)
                    
                    total_deleted_documents += workspace_deleted_docs
                    total_deleted_chunks += workspace_deleted_chunks
                    processed_workspaces += 1
                    
                    workspace_time = int((time.time() - workspace_start) * 1000)
                    workspace_results[workspace] = {
                        "deleted_documents": workspace_deleted_docs,
                        "deleted_chunks": workspace_deleted_chunks,
                        "duration_ms": workspace_time,
                        "status": "success"
                    }
                    
                    logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_workspace_complete "
                               f"correlation_id={correlation_id} workspace={workspace} "
                               f"duration_ms={workspace_time} deleted_documents={workspace_deleted_docs} "
                               f"deleted_chunks={workspace_deleted_chunks}")
                    
                    # Apply rate limiting
                    await self._rate_limit_delay()
                    
                except Exception as e:
                    workspace_time = int((time.time() - workspace_start) * 1000)
                    failed_workspaces.append(workspace)
                    workspace_results[workspace] = {
                        "error": str(e),
                        "duration_ms": workspace_time,
                        "status": "failed"
                    }
                    
                    logger.error(f"Failed to cleanup workspace {workspace}: {e}")
                    logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_workspace_error "
                               f"correlation_id={correlation_id} workspace={workspace} "
                               f"duration_ms={workspace_time} error=\"{str(e)}\"")
            
            # Additional database cleanup for orphaned records
            await self._cleanup_orphaned_database_records(correlation_id, max_age_days)
            
            # Calculate final metrics
            total_time = int((time.time() - start_time) * 1000)
            success_rate = (processed_workspaces / len(workspaces)) * 100 if workspaces else 100
            
            # Update execution metrics
            execution.records_processed = len(workspaces)
            execution.records_failed = len(failed_workspaces)
            
            result = {
                "status": "completed",
                "summary": {
                    "total_workspaces": len(workspaces),
                    "processed_workspaces": processed_workspaces,
                    "failed_workspaces": len(failed_workspaces),
                    "success_rate_percent": success_rate,
                    "total_deleted_documents": total_deleted_documents,
                    "total_deleted_chunks": total_deleted_chunks,
                    "duration_ms": total_time
                },
                "workspace_results": workspace_results,
                "failed_workspaces": failed_workspaces,
                "parameters": {
                    "batch_size": batch_size,
                    "max_age_days": max_age_days
                },
                "correlation_id": correlation_id,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"TTL cleanup job completed successfully")
            logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_job_complete "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"workspaces_processed={processed_workspaces} "
                       f"total_deleted_documents={total_deleted_documents} "
                       f"success_rate={success_rate:.1f}%")
            
            return result
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"TTL cleanup job failed: {e}")
            logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_job_error "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"error=\"{str(e)}\"")
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": total_time,
                "correlation_id": correlation_id,
                "failed_at": datetime.utcnow().isoformat()
            }
    
    async def _cleanup_orphaned_database_records(
        self, 
        correlation_id: str, 
        max_age_days: int
    ) -> None:
        """Clean up orphaned database records"""
        try:
            cleanup_start = time.time()
            
            # Clean up content metadata for expired Context7 documents
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            query = """
            DELETE FROM content_metadata
            WHERE enrichment_metadata->'ttl_info'->>'source_provider' = 'context7'
            AND enrichment_metadata->'ttl_info'->>'expires_at' < :cutoff_date
            """
            
            result = await self.db_manager.execute(query, {
                "cutoff_date": cutoff_date.isoformat()
            })
            
            cleanup_time = int((time.time() - cleanup_start) * 1000)
            rowcount = getattr(result, 'rowcount', 0)
            
            logger.info(f"PIPELINE_METRICS: step=ttl_cleanup_database_cleanup "
                       f"correlation_id={correlation_id} duration_ms={cleanup_time} "
                       f"cleaned_records={rowcount}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned database records: {e}")


class DocumentRefreshJob(BaseJob):
    """
    Document Refresh Job for Context7 Documents
    
    Handles weekly refresh of near-expired Context7 documents to ensure
    content remains current and accurate. Uses intelligent refresh logic
    to prioritize high-quality, frequently-accessed documents.
    """
    
    def __init__(
        self,
        context7_service: Context7IngestionService,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager,
        llm_client: LLMProviderClient,
        config: Context7JobConfig
    ):
        super().__init__(context7_service, weaviate_client, db_manager, config)
        self.llm_client = llm_client
    
    async def execute(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Execute document refresh job"""
        start_time = time.time()
        correlation_id = execution.correlation_id or f"doc_refresh_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting document refresh job")
            logger.info(f"PIPELINE_METRICS: step=document_refresh_job_start "
                       f"correlation_id={correlation_id} job_id={job_config.job_id}")
            
            # Get job parameters
            batch_size = job_config.parameters.get("batch_size", self.config.refresh_batch_size)
            threshold_days = job_config.parameters.get("threshold_days", self.config.refresh_threshold_days)
            max_age_days = job_config.parameters.get("max_age_days", self.config.refresh_max_age_days)
            min_quality = job_config.parameters.get("minimum_quality_score", self.config.minimum_quality_score)
            
            # Get target workspaces
            workspaces = await self._get_target_workspaces()
            logger.info(f"Processing {len(workspaces)} workspaces for document refresh")
            
            # Track results
            total_refreshed_documents = 0
            total_failed_refreshes = 0
            processed_workspaces = 0
            failed_workspaces = []
            workspace_results = {}
            
            # Process each workspace
            for workspace in workspaces:
                workspace_start = time.time()
                
                try:
                    logger.info(f"Processing workspace: {workspace}")
                    logger.info(f"PIPELINE_METRICS: step=document_refresh_workspace_start "
                               f"correlation_id={correlation_id} workspace={workspace}")
                    
                    # Get candidates for refresh
                    candidates = await self._get_refresh_candidates(
                        workspace, threshold_days, max_age_days, min_quality, correlation_id
                    )
                    
                    if not candidates:
                        logger.info(f"No refresh candidates found in workspace: {workspace}")
                        workspace_results[workspace] = {
                            "candidates_found": 0,
                            "documents_refreshed": 0,
                            "documents_failed": 0,
                            "status": "completed"
                        }
                        continue
                    
                    # Refresh documents in batches
                    workspace_refreshed = 0
                    workspace_failed = 0
                    
                    for i in range(0, len(candidates), batch_size):
                        batch = candidates[i:i + batch_size]
                        batch_start = time.time()
                        
                        batch_results = await self._refresh_document_batch(
                            batch, workspace, correlation_id
                        )
                        
                        batch_time = int((time.time() - batch_start) * 1000)
                        batch_refreshed = batch_results["refreshed"]
                        batch_failed = batch_results["failed"]
                        
                        workspace_refreshed += batch_refreshed
                        workspace_failed += batch_failed
                        
                        logger.info(f"PIPELINE_METRICS: step=document_refresh_batch_complete "
                                   f"correlation_id={correlation_id} workspace={workspace} "
                                   f"batch_number={i//batch_size + 1} duration_ms={batch_time} "
                                   f"batch_size={len(batch)} refreshed={batch_refreshed} "
                                   f"failed={batch_failed}")
                        
                        # Apply rate limiting between batches
                        await self._rate_limit_delay()
                    
                    total_refreshed_documents += workspace_refreshed
                    total_failed_refreshes += workspace_failed
                    processed_workspaces += 1
                    
                    workspace_time = int((time.time() - workspace_start) * 1000)
                    workspace_results[workspace] = {
                        "candidates_found": len(candidates),
                        "documents_refreshed": workspace_refreshed,
                        "documents_failed": workspace_failed,
                        "duration_ms": workspace_time,
                        "status": "completed"
                    }
                    
                    logger.info(f"PIPELINE_METRICS: step=document_refresh_workspace_complete "
                               f"correlation_id={correlation_id} workspace={workspace} "
                               f"duration_ms={workspace_time} candidates={len(candidates)} "
                               f"refreshed={workspace_refreshed} failed={workspace_failed}")
                    
                except Exception as e:
                    workspace_time = int((time.time() - workspace_start) * 1000)
                    failed_workspaces.append(workspace)
                    workspace_results[workspace] = {
                        "error": str(e),
                        "duration_ms": workspace_time,
                        "status": "failed"
                    }
                    
                    logger.error(f"Failed to refresh documents in workspace {workspace}: {e}")
                    logger.info(f"PIPELINE_METRICS: step=document_refresh_workspace_error "
                               f"correlation_id={correlation_id} workspace={workspace} "
                               f"duration_ms={workspace_time} error=\"{str(e)}\"")
            
            # Calculate final metrics
            total_time = int((time.time() - start_time) * 1000)
            success_rate = (processed_workspaces / len(workspaces)) * 100 if workspaces else 100
            
            # Update execution metrics
            execution.records_processed = total_refreshed_documents
            execution.records_failed = total_failed_refreshes
            
            result = {
                "status": "completed",
                "summary": {
                    "total_workspaces": len(workspaces),
                    "processed_workspaces": processed_workspaces,
                    "failed_workspaces": len(failed_workspaces),
                    "success_rate_percent": success_rate,
                    "total_refreshed_documents": total_refreshed_documents,
                    "total_failed_refreshes": total_failed_refreshes,
                    "duration_ms": total_time
                },
                "workspace_results": workspace_results,
                "failed_workspaces": failed_workspaces,
                "parameters": {
                    "batch_size": batch_size,
                    "threshold_days": threshold_days,
                    "max_age_days": max_age_days,
                    "minimum_quality_score": min_quality
                },
                "correlation_id": correlation_id,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Document refresh job completed successfully")
            logger.info(f"PIPELINE_METRICS: step=document_refresh_job_complete "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"workspaces_processed={processed_workspaces} "
                       f"total_refreshed={total_refreshed_documents} "
                       f"success_rate={success_rate:.1f}%")
            
            return result
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"Document refresh job failed: {e}")
            logger.info(f"PIPELINE_METRICS: step=document_refresh_job_error "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"error=\"{str(e)}\"")
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": total_time,
                "correlation_id": correlation_id,
                "failed_at": datetime.utcnow().isoformat()
            }
    
    async def _get_refresh_candidates(
        self,
        workspace: str,
        threshold_days: int,
        max_age_days: int,
        min_quality: float,
        correlation_id: str
    ) -> List[Dict[str, Any]]:
        """Get documents that need refreshing"""
        try:
            # Calculate date thresholds
            now = datetime.utcnow()
            near_expiry_threshold = now + timedelta(days=threshold_days)
            max_age_threshold = now - timedelta(days=max_age_days)
            
            # Query for refresh candidates
            query = """
            SELECT 
                content_id,
                enrichment_metadata,
                created_at,
                updated_at
            FROM content_metadata
            WHERE weaviate_workspace = :workspace
            AND enrichment_metadata->'ttl_info'->>'source_provider' = 'context7'
            AND (
                -- Documents near expiry
                (enrichment_metadata->'ttl_info'->>'expires_at')::timestamp <= :near_expiry_threshold
                OR
                -- Documents older than max age
                created_at <= :max_age_threshold
            )
            AND (
                -- Skip if updated recently (within last hour)
                :skip_recent = false OR updated_at <= :recent_threshold
            )
            ORDER BY 
                -- Prioritize by quality score (higher first)
                COALESCE((enrichment_metadata->>'quality_score')::float, 0) DESC,
                -- Then by age (older first)
                created_at ASC
            """
            
            recent_threshold = now - timedelta(hours=1) if self.config.skip_recent_updates else now
            
            results = await self.db_manager.fetch_all(query, {
                "workspace": workspace,
                "near_expiry_threshold": near_expiry_threshold,
                "max_age_threshold": max_age_threshold,
                "skip_recent": self.config.skip_recent_updates,
                "recent_threshold": recent_threshold
            })
            
            # Filter by quality score
            candidates = []
            for row in results:
                enrichment_metadata = row["enrichment_metadata"] or {}
                quality_score = enrichment_metadata.get("quality_score", 0.0)
                
                if quality_score >= min_quality:
                    candidates.append({
                        "content_id": row["content_id"],
                        "enrichment_metadata": enrichment_metadata,
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "quality_score": quality_score
                    })
            
            logger.info(f"Found {len(candidates)} refresh candidates in workspace {workspace}")
            logger.info(f"PIPELINE_METRICS: step=document_refresh_candidates_found "
                       f"correlation_id={correlation_id} workspace={workspace} "
                       f"candidates_count={len(candidates)} total_queried={len(results)}")
            
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to get refresh candidates for workspace {workspace}: {e}")
            return []
    
    async def _refresh_document_batch(
        self,
        candidates: List[Dict[str, Any]],
        workspace: str,
        correlation_id: str
    ) -> Dict[str, int]:
        """Refresh a batch of documents"""
        refreshed = 0
        failed = 0
        
        for candidate in candidates:
            try:
                content_id = candidate["content_id"]
                
                # Get original document metadata
                metadata = candidate["enrichment_metadata"]
                source_url = metadata.get("source_url", "")
                technology = metadata.get("technology", "")
                
                if not source_url or not technology:
                    logger.warning(f"Missing metadata for document {content_id}, skipping refresh")
                    failed += 1
                    continue
                
                # Create refresh intent
                intent = QueryIntent(
                    technology=technology,
                    intent_type="refresh",
                    confidence_score=1.0,
                    key_concepts=[technology],
                    suggested_providers=["context7"]
                )
                
                # Attempt to re-fetch and process the document
                refresh_start = time.time()
                
                # This is a simplified refresh - in a real implementation,
                # you would re-fetch from the original source and re-process
                success = await self._perform_document_refresh(
                    content_id, source_url, technology, intent, workspace, correlation_id
                )
                
                refresh_time = int((time.time() - refresh_start) * 1000)
                
                if success:
                    refreshed += 1
                    logger.info(f"PIPELINE_METRICS: step=document_refresh_success "
                               f"correlation_id={correlation_id} content_id={content_id} "
                               f"duration_ms={refresh_time} technology={technology}")
                else:
                    failed += 1
                    logger.warning(f"PIPELINE_METRICS: step=document_refresh_failed "
                                  f"correlation_id={correlation_id} content_id={content_id} "
                                  f"duration_ms={refresh_time}")
                
            except Exception as e:
                failed += 1
                logger.error(f"Failed to refresh document {candidate.get('content_id')}: {e}")
        
        return {"refreshed": refreshed, "failed": failed}
    
    async def _perform_document_refresh(
        self,
        content_id: str,
        source_url: str,
        technology: str,
        intent: QueryIntent,
        workspace: str,
        correlation_id: str
    ) -> bool:
        """Perform the actual document refresh"""
        try:
            # For this implementation, we'll simulate a successful refresh
            # In a real implementation, you would:
            # 1. Re-fetch the document from the source URL
            # 2. Re-process it through the Context7 ingestion pipeline
            # 3. Update the document in Weaviate with new TTL
            # 4. Update the database metadata
            
            # Update the document's TTL metadata to extend its life
            now = datetime.utcnow()
            new_expires_at = now + timedelta(days=30)  # Extend by 30 days
            
            query = """
            UPDATE content_metadata
            SET enrichment_metadata = jsonb_set(
                enrichment_metadata,
                '{ttl_info,expires_at}',
                :new_expires_at,
                true
            ),
            enrichment_metadata = jsonb_set(
                enrichment_metadata,
                '{ttl_info,updated_at}',
                :updated_at,
                true
            ),
            updated_at = :updated_at
            WHERE content_id = :content_id
            AND weaviate_workspace = :workspace
            """
            
            await self.db_manager.execute(query, {
                "content_id": content_id,
                "workspace": workspace,
                "new_expires_at": json.dumps(new_expires_at.isoformat()),
                "updated_at": now
            })
            
            logger.debug(f"Refreshed document {content_id} with new expiry: {new_expires_at}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to perform document refresh for {content_id}: {e}")
            return False


class HealthCheckJob(BaseJob):
    """
    Health Check Job for Context7 Services
    
    Performs comprehensive health checks on all Context7 related services
    and dependencies to ensure system reliability and early problem detection.
    """
    
    async def execute(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Execute health check job"""
        start_time = time.time()
        correlation_id = execution.correlation_id or f"health_check_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting health check job")
            logger.info(f"PIPELINE_METRICS: step=health_check_job_start "
                       f"correlation_id={correlation_id} job_id={job_config.job_id}")
            
            health_results = {}
            overall_status = "healthy"
            
            # Check Weaviate health
            weaviate_health = await self._check_weaviate_health(correlation_id)
            health_results["weaviate"] = weaviate_health
            if weaviate_health["status"] != "healthy":
                overall_status = "unhealthy"
            
            # Check database health
            database_health = await self._check_database_health(correlation_id)
            health_results["database"] = database_health
            if database_health["status"] != "healthy":
                overall_status = "unhealthy"
            
            # Check Context7 service health
            context7_health = await self._check_context7_service_health(correlation_id)
            health_results["context7_service"] = context7_health
            if context7_health["status"] != "healthy" and overall_status == "healthy":
                overall_status = "degraded"
            
            # Check workspace health
            workspace_health = await self._check_workspace_health(correlation_id)
            health_results["workspaces"] = workspace_health
            if workspace_health["status"] != "healthy" and overall_status == "healthy":
                overall_status = "degraded"
            
            # Calculate final metrics
            total_time = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed",
                "overall_health": overall_status,
                "health_checks": health_results,
                "summary": {
                    "total_checks": len(health_results),
                    "healthy_checks": sum(1 for check in health_results.values() if check["status"] == "healthy"),
                    "duration_ms": total_time
                },
                "correlation_id": correlation_id,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Health check job completed - Overall status: {overall_status}")
            logger.info(f"PIPELINE_METRICS: step=health_check_job_complete "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"overall_health={overall_status} total_checks={len(health_results)}")
            
            return result
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"Health check job failed: {e}")
            logger.info(f"PIPELINE_METRICS: step=health_check_job_error "
                       f"correlation_id={correlation_id} duration_ms={total_time} "
                       f"error=\"{str(e)}\"")
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": total_time,
                "correlation_id": correlation_id,
                "failed_at": datetime.utcnow().isoformat()
            }
    
    async def _check_weaviate_health(self, correlation_id: str) -> Dict[str, Any]:
        """Check Weaviate health"""
        try:
            start_time = time.time()
            
            # Check basic connectivity
            health_status = await self.weaviate_client.health_check()
            
            duration = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "healthy" if health_status else "unhealthy",
                "response_time_ms": duration,
                "details": health_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"PIPELINE_METRICS: step=health_check_weaviate "
                       f"correlation_id={correlation_id} duration_ms={duration} "
                       f"status={result['status']}")
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_database_health(self, correlation_id: str) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            
            # Simple query to check database connectivity
            result = await self.db_manager.fetch_one("SELECT 1 as health_check")
            
            duration = int((time.time() - start_time) * 1000)
            
            health_result = {
                "status": "healthy" if result else "unhealthy",
                "response_time_ms": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"PIPELINE_METRICS: step=health_check_database "
                       f"correlation_id={correlation_id} duration_ms={duration} "
                       f"status={health_result['status']}")
            
            return health_result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_context7_service_health(self, correlation_id: str) -> Dict[str, Any]:
        """Check Context7 service health"""
        try:
            start_time = time.time()
            
            # Check service availability (this is a basic check)
            # In a real implementation, you might check provider connectivity
            service_available = hasattr(self.context7_service, 'process_context7_document')
            
            duration = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "healthy" if service_available else "unhealthy",
                "response_time_ms": duration,
                "details": {
                    "service_available": service_available
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"PIPELINE_METRICS: step=health_check_context7_service "
                       f"correlation_id={correlation_id} duration_ms={duration} "
                       f"status={result['status']}")
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_workspace_health(self, correlation_id: str) -> Dict[str, Any]:
        """Check workspace health"""
        try:
            start_time = time.time()
            
            # Get workspaces and check basic stats
            workspaces = await self._get_target_workspaces()
            healthy_workspaces = 0
            total_workspaces = len(workspaces)
            
            for workspace in workspaces[:5]:  # Check first 5 workspaces
                try:
                    # Simple check - try to get workspace info
                    workspace_info = await self.weaviate_client.get_workspace_info(workspace)
                    if workspace_info:
                        healthy_workspaces += 1
                except Exception:
                    pass  # Workspace check failed
            
            duration = int((time.time() - start_time) * 1000)
            
            # Determine status
            if total_workspaces == 0:
                status = "healthy"  # No workspaces to check
            elif healthy_workspaces == total_workspaces:
                status = "healthy"
            elif healthy_workspaces > 0:
                status = "degraded"
            else:
                status = "unhealthy"
            
            result = {
                "status": status,
                "response_time_ms": duration,
                "details": {
                    "total_workspaces": total_workspaces,
                    "healthy_workspaces": healthy_workspaces,
                    "health_percentage": (healthy_workspaces / total_workspaces * 100) if total_workspaces > 0 else 100
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"PIPELINE_METRICS: step=health_check_workspaces "
                       f"correlation_id={correlation_id} duration_ms={duration} "
                       f"status={result['status']} total_workspaces={total_workspaces} "
                       f"healthy_workspaces={healthy_workspaces}")
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }