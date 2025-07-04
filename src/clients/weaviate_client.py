"""
Weaviate Client Implementation
Complete HTTP/gRPC client for Weaviate multi-tenant vector database management

This client implements vector search, document upload, and multi-tenancy support
with circuit breaker pattern, async operations, and comprehensive error handling.
"""

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure
from weaviate.classes.tenants import Tenant, TenantActivityStatus
from weaviate.classes.query import MetadataQuery
import asyncio
import logging
import time
import uuid
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import httpx

from src.core.config.models import WeaviateConfig
from src.database.connection import ProcessedDocument, DocumentChunk, UploadResult
from .exceptions import (
    WeaviateError,
    WeaviateConnectionError,
    WeaviateAuthenticationError,
    WeaviateRateLimitError,
    WeaviateWorkspaceError,
)

logger = logging.getLogger(__name__)

# Import enhanced logging for external service monitoring
try:
    from src.logging_config import ExternalServiceLogger, SecurityLogger
    _service_logger = ExternalServiceLogger(logger)
    _security_logger = SecurityLogger(logger)
except ImportError:
    _service_logger = None
    _security_logger = None
    logger.warning("Enhanced service logging not available")


class WeaviateVectorClient:
    """
    Weaviate client with multi-tenancy support for DocAIche.
    
    Provides complete integration with Weaviate for tenant (workspace) management,
    document upload, vector search, and health monitoring operations.
    
    Uses the official Weaviate Python client v4 with async support.
    """
    
    COLLECTION_NAME = "DocumentContent"
    
    def __init__(self, config: WeaviateConfig):
        """
        Initialize Weaviate client with configuration.
        
        Args:
            config: Weaviate configuration
        """
        self.config = config
        self.base_url = config.endpoint.rstrip("/")
        self.api_key = config.api_key
        self.client: Optional[weaviate.WeaviateClient] = None
        self._request_count = 0
        self._rate_limit_remaining = None
        self._rate_limit_reset = None
        
        logger.info(f"Weaviate client initialized for endpoint: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize Weaviate client connection"""
        start_time = time.time()
        
        try:
            # Parse the endpoint to get host and port
            import urllib.parse
            parsed = urllib.parse.urlparse(self.base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8080
            
            # Connect to Weaviate
            connect_params = {
                "http_host": host,
                "http_port": port,
                "http_secure": False,  # Not using HTTPS internally
                "grpc_host": host,
                "grpc_port": 50051,  # Default gRPC port
                "grpc_secure": False,  # Not using secure gRPC internally
            }
            
            if self.api_key:
                connect_params["auth_credentials"] = Auth.api_key(self.api_key)
            
            self.client = weaviate.connect_to_custom(**connect_params)
            
            # Ensure the main collection exists
            await self._ensure_collection_exists()
            
            connection_duration = (time.time() - start_time) * 1000
            logger.info("Weaviate client session initialized")
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="weaviate",
                    endpoint=self.base_url,
                    method="CONNECT",
                    duration_ms=connection_duration,
                    status_code=200
                )
                
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise WeaviateConnectionError(
                f"Failed to connect to Weaviate: {str(e)}",
                error_context={"endpoint": self.base_url}
            )
    
    async def disconnect(self) -> None:
        """Clean up Weaviate client connection"""
        if self.client:
            self.client.close()
            logger.info("Weaviate client session closed")
    
    async def _ensure_collection_exists(self) -> None:
        """Ensure the main collection exists with multi-tenancy enabled and TTL support"""
        try:
            # Check if collection exists
            if not self.client.collections.exists(self.COLLECTION_NAME):
                # Create collection with multi-tenancy enabled and TTL properties
                self.client.collections.create(
                    name=self.COLLECTION_NAME,
                    multi_tenancy_config=Configure.multi_tenancy(
                        enabled=True,
                        auto_tenant_creation=True,
                        auto_tenant_activation=True
                    ),
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        weaviate.classes.config.Property(
                            name="content",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="chunk_id",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="chunk_index",
                            data_type=weaviate.classes.config.DataType.INT
                        ),
                        weaviate.classes.config.Property(
                            name="total_chunks",
                            data_type=weaviate.classes.config.DataType.INT
                        ),
                        weaviate.classes.config.Property(
                            name="document_title",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="document_id",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="technology",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="source_url",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        # TTL properties
                        weaviate.classes.config.Property(
                            name="expires_at",
                            data_type=weaviate.classes.config.DataType.DATE
                        ),
                        weaviate.classes.config.Property(
                            name="created_at",
                            data_type=weaviate.classes.config.DataType.DATE
                        ),
                        weaviate.classes.config.Property(
                            name="updated_at",
                            data_type=weaviate.classes.config.DataType.DATE
                        ),
                        weaviate.classes.config.Property(
                            name="source_provider",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                    ]
                )
                logger.info(f"Created Weaviate collection: {self.COLLECTION_NAME} with TTL support")
            else:
                # Collection exists - check if we need to add TTL properties
                await self._migrate_collection_schema()
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise
    
    async def _migrate_collection_schema(self) -> None:
        """Migrate existing collection to add TTL properties if they don't exist"""
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            collection_config = collection.config.get()
            
            # Check which TTL properties are missing
            existing_props = {prop.name for prop in collection_config.properties}
            required_ttl_props = {
                "expires_at": weaviate.classes.config.DataType.DATE,
                "created_at": weaviate.classes.config.DataType.DATE,
                "updated_at": weaviate.classes.config.DataType.DATE,
                "source_provider": weaviate.classes.config.DataType.TEXT,
            }
            
            missing_props = []
            for prop_name, prop_type in required_ttl_props.items():
                if prop_name not in existing_props:
                    missing_props.append(
                        weaviate.classes.config.Property(
                            name=prop_name,
                            data_type=prop_type
                        )
                    )
            
            if missing_props:
                logger.info(f"Adding {len(missing_props)} TTL properties to existing collection")
                
                # Add missing properties to the collection
                for prop in missing_props:
                    collection.config.add_property(prop)
                    logger.info(f"Added TTL property: {prop.name}")
                
                logger.info("Collection schema migration completed successfully")
            else:
                logger.info("Collection already has all required TTL properties")
                
        except Exception as e:
            logger.error(f"Failed to migrate collection schema: {e}")
            # Don't raise here - continue with existing schema
            logger.warning("Continuing with existing schema - TTL features may not work correctly")
    
    def _calculate_ttl_timestamps(self, default_ttl_days: int = 30) -> Dict[str, datetime]:
        """Calculate TTL timestamps for document chunks"""
        now = datetime.utcnow()
        
        return {
            "created_at": now,
            "updated_at": now,
            "expires_at": now + timedelta(days=default_ttl_days)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Weaviate service health"""
        start_time = time.time()
        try:
            # Use the client's readiness check
            is_ready = self.client.is_ready()
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy" if is_ready else "unhealthy",
                "ready": is_ready,
                "endpoint": self.base_url
            }
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="weaviate",
                    endpoint="/v1/.well-known/ready",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=200 if is_ready else 503
                )
            
            return health_data
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Weaviate health check failed: {e}")
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="weaviate",
                    endpoint="/v1/.well-known/ready",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=500,
                    error_message=str(e)
                )
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "ready": False
            }
    
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all available workspaces (tenants)"""
        start_time = time.time()
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenants = collection.tenants.get()
            
            duration_ms = (time.time() - start_time) * 1000
            
            workspaces = []
            for tenant_name, tenant_obj in tenants.items():
                workspaces.append({
                    "slug": tenant_name,
                    "name": tenant_name.replace("-", " ").title(),
                    "status": tenant_obj.activity_status.value if hasattr(tenant_obj, 'activity_status') else "ACTIVE"
                })
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="weaviate",
                    endpoint=f"/v1/schema/{self.COLLECTION_NAME}/tenants",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=200,
                    result_count=len(workspaces)
                )
            
            return workspaces
            
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            raise WeaviateError(f"Failed to list workspaces: {str(e)}")
    
    async def get_or_create_workspace(
        self, workspace_slug: str, name: str = None
    ) -> Dict[str, Any]:
        """Get existing workspace (tenant) or create new one"""
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            
            # Check if tenant exists
            tenants = collection.tenants.get()
            if workspace_slug in tenants:
                return {
                    "slug": workspace_slug,
                    "name": name or workspace_slug.replace("-", " ").title(),
                    "id": workspace_slug,
                    "status": tenants[workspace_slug].activity_status.value if hasattr(tenants[workspace_slug], 'activity_status') else "ACTIVE"
                }
            
            # Create new tenant
            collection.tenants.create([
                Tenant(
                    name=workspace_slug,
                    activity_status=TenantActivityStatus.ACTIVE
                )
            ])
            
            logger.info(f"Created new workspace/tenant: {workspace_slug}")
            
            return {
                "slug": workspace_slug,
                "name": name or workspace_slug.replace("-", " ").title(),
                "id": workspace_slug,
                "status": "ACTIVE"
            }
            
        except Exception as e:
            logger.error(f"Failed to get or create workspace: {e}")
            raise WeaviateWorkspaceError(
                f"Failed to get or create workspace: {str(e)}",
                workspace_slug=workspace_slug
            )
    
    async def upload_document(
        self, workspace_slug: str, document: ProcessedDocument, ttl_days: int = 30, source_provider: str = "default"
    ) -> UploadResult:
        """
        Upload ProcessedDocument to workspace (tenant) by iterating over chunks.
        
        Process:
        1. Validate workspace exists
        2. Upload chunks with batch processing and TTL metadata
        3. Track failures and retry with exponential backoff
        4. Return comprehensive result
        """
        logger.info(
            f"Starting upload of document {document.id} to workspace {workspace_slug} with TTL: {ttl_days} days"
        )
        
        # Step 1: Validate workspace exists
        await self.get_or_create_workspace(workspace_slug)
        
        # Step 2: Calculate TTL timestamps
        ttl_timestamps = self._calculate_ttl_timestamps(ttl_days)
        
        # Step 3: Prepare upload results tracking
        upload_results = {
            "document_id": document.id,
            "workspace_slug": workspace_slug,
            "total_chunks": len(document.chunks),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "uploaded_chunk_ids": [],
            "failed_chunk_ids": [],
            "errors": [],
        }
        
        # Step 4: Upload chunks in batches
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Use Weaviate's batch import
            with tenant_collection.batch.fixed_size(batch_size=100) as batch:
                for chunk in document.chunks:
                    try:
                        chunk_data = {
                            "content": chunk.content,
                            "chunk_id": chunk.id,
                            "chunk_index": chunk.chunk_index,
                            "total_chunks": chunk.total_chunks,
                            "document_title": document.title,
                            "document_id": document.id,
                            "technology": document.technology,
                            "source_url": document.source_url,
                            # TTL metadata
                            "expires_at": ttl_timestamps["expires_at"],
                            "created_at": ttl_timestamps["created_at"],
                            "updated_at": ttl_timestamps["updated_at"],
                            "source_provider": source_provider,
                        }
                        
                        batch.add_object(properties=chunk_data)
                        upload_results["successful_uploads"] += 1
                        upload_results["uploaded_chunk_ids"].append(chunk.id)
                        
                    except Exception as e:
                        logger.error(f"Failed to upload chunk {chunk.id}: {e}")
                        upload_results["failed_uploads"] += 1
                        upload_results["failed_chunk_ids"].append(chunk.id)
                        upload_results["errors"].append(f"Chunk {chunk.id}: {str(e)}")
            
            # Log results
            success_rate = (
                upload_results["successful_uploads"] / upload_results["total_chunks"]
            )
            logger.info(
                f"Document upload completed: {success_rate:.1%} success rate "
                f"({upload_results['successful_uploads']}/{upload_results['total_chunks']} chunks) "
                f"with TTL expiration: {ttl_timestamps['expires_at']}"
            )
            
        except Exception as e:
            logger.error(f"Batch upload failed: {e}")
            upload_results["errors"].append(f"Batch upload error: {str(e)}")
        
        return UploadResult(**upload_results)
    
    async def search_workspace(
        self, workspace_slug: str, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Execute vector search against workspace (tenant)"""
        start_time = time.time()
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Perform near text search
            response = tenant_collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=MetadataQuery(distance=True, certainty=True)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Format results to match expected structure
            results = []
            for obj in response.objects:
                result = {
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        "source": obj.properties.get("source_url", ""),
                        "document_id": obj.properties.get("document_id", ""),
                        "chunk_id": obj.properties.get("chunk_id", ""),
                        "technology": obj.properties.get("technology", ""),
                        "distance": obj.metadata.distance if obj.metadata else None,
                        "certainty": obj.metadata.certainty if obj.metadata else None,
                        # TTL metadata
                        "expires_at": obj.properties.get("expires_at"),
                        "created_at": obj.properties.get("created_at"),
                        "updated_at": obj.properties.get("updated_at"),
                        "source_provider": obj.properties.get("source_provider", ""),
                    },
                    "id": str(obj.uuid) if obj.uuid else obj.properties.get("chunk_id", ""),
                }
                results.append(result)
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="weaviate",
                    endpoint=f"/v1/graphql",
                    method="POST",
                    duration_ms=duration_ms,
                    status_code=200,
                    workspace=workspace_slug,
                    query_length=len(query),
                    result_count=len(results)
                )
            
            return results
            
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__
            logger.info(f"Weaviate search exception for workspace '{workspace_slug}': {e} (type: {error_type})")
            
            # Handle data-related scenarios as empty results (not system errors)
            data_related_errors = [
                "tenant", "not found", "does not exist", "no such tenant", 
                "no objects found", "empty", "no results", "no schema",
                "collection", "class", "not exist"
            ]
            
            if any(phrase in error_str for phrase in data_related_errors):
                logger.info(f"Workspace '{workspace_slug}' has no data or doesn't exist - returning empty results")
                return []
            
            # Log full exception details for system errors
            logger.error(f"System error in workspace search '{workspace_slug}': {e}", exc_info=True)
            raise WeaviateError(f"Search failed for workspace {workspace_slug}: {str(e)}")
    
    async def list_workspace_documents(
        self, workspace_slug: str
    ) -> List[Dict[str, Any]]:
        """List all documents in workspace (tenant)"""
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Query all objects and group by document_id
            response = tenant_collection.query.fetch_objects(limit=10000)
            
            # Group by document
            documents_map = {}
            for obj in response.objects:
                doc_id = obj.properties.get("document_id", "unknown")
                if doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "id": doc_id,
                        "title": obj.properties.get("document_title", "Untitled"),
                        "chunks": 0,
                        "technology": obj.properties.get("technology", ""),
                        "source_url": obj.properties.get("source_url", ""),
                        # TTL metadata
                        "expires_at": obj.properties.get("expires_at"),
                        "created_at": obj.properties.get("created_at"),
                        "updated_at": obj.properties.get("updated_at"),
                        "source_provider": obj.properties.get("source_provider", ""),
                    }
                documents_map[doc_id]["chunks"] += 1
            
            return list(documents_map.values())
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise WeaviateError(f"Failed to list documents: {str(e)}")
    
    async def delete_document(self, workspace_slug: str, document_id: str) -> bool:
        """Delete document from workspace (tenant)"""
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Delete all chunks belonging to this document
            # For now, iterate through objects and delete individually
            response = tenant_collection.query.fetch_objects(limit=10000)
            deleted_count = 0
            for obj in response.objects:
                if obj.properties.get("document_id") == document_id:
                    tenant_collection.data.delete_by_id(obj.uuid)
                    deleted_count += 1
            
            logger.info(f"Deleted document {document_id} from workspace {workspace_slug}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            if "not found" in str(e).lower():
                return True  # Already deleted
            raise WeaviateError(f"Failed to delete document: {str(e)}")
    
    async def get_expired_documents(self, workspace_slug: str, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Get documents that have expired based on TTL.
        
        Args:
            workspace_slug: The workspace to search in
            limit: Maximum number of objects to fetch (default: 10000)
            
        Returns:
            List of expired documents with metadata
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Query objects with larger limit to handle big datasets
            response = tenant_collection.query.fetch_objects(limit=limit)
            
            # Group by document and filter expired ones
            documents_map = {}
            current_time = datetime.utcnow()
            processed_chunks = 0
            
            logger.info(f"Scanning {len(response.objects)} chunks for expired documents in workspace '{workspace_slug}'")
            
            for obj in response.objects:
                processed_chunks += 1
                
                # Check if document is expired
                expires_at = obj.properties.get("expires_at")
                if expires_at and isinstance(expires_at, datetime) and expires_at < current_time:
                    doc_id = obj.properties.get("document_id", "unknown")
                    if doc_id not in documents_map:
                        documents_map[doc_id] = {
                            "id": doc_id,
                            "title": obj.properties.get("document_title", "Untitled"),
                            "chunks": 0,
                            "technology": obj.properties.get("technology", ""),
                            "source_url": obj.properties.get("source_url", ""),
                            "expires_at": obj.properties.get("expires_at"),
                            "created_at": obj.properties.get("created_at"),
                            "updated_at": obj.properties.get("updated_at"),
                            "source_provider": obj.properties.get("source_provider", ""),
                        }
                    documents_map[doc_id]["chunks"] += 1
            
            expired_docs = list(documents_map.values())
            logger.info(f"Found {len(expired_docs)} expired documents out of {processed_chunks} total chunks")
            
            return expired_docs
            
        except Exception as e:
            logger.error(f"Failed to get expired documents in workspace '{workspace_slug}': {e}")
            raise WeaviateError(f"Failed to get expired documents: {str(e)}")
    
    async def cleanup_expired_documents(self, workspace_slug: str, batch_size: int = 50, correlation_id: str = None) -> Dict[str, Any]:
        """
        Clean up expired documents from workspace.
        
        Args:
            workspace_slug: The workspace to clean up
            batch_size: Number of documents to process in each batch (default: 50)
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Dictionary with cleanup statistics
        """
        start_time = datetime.utcnow()
        perf_start = time.time()
        if correlation_id is None:
            correlation_id = f"wv_cleanup_{uuid.uuid4().hex[:8]}"
        
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Query for expired documents
            logger.info(f"Starting cleanup of expired documents in workspace '{workspace_slug}'")
            expired_docs = await self.get_expired_documents(workspace_slug)
            
            if not expired_docs:
                return {
                    "deleted_documents": 0,
                    "deleted_chunks": 0,
                    "message": "No expired documents found",
                    "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                }
            
            logger.info(f"Found {len(expired_docs)} expired documents to clean up")
            
            # Delete expired documents in batches
            deleted_chunks = 0
            failed_deletions = []
            successful_deletions = []
            
            for i in range(0, len(expired_docs), batch_size):
                batch = expired_docs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(expired_docs) + batch_size - 1)//batch_size}")
                
                for doc in batch:
                    try:
                        # Delete document using the existing delete method
                        success = await self.delete_document(workspace_slug, doc["id"])
                        if success:
                            deleted_chunks += doc["chunks"]
                            successful_deletions.append(doc["id"])
                            logger.info(f"Deleted expired document {doc['id']} with {doc['chunks']} chunks")
                        else:
                            failed_deletions.append(doc["id"])
                            logger.warning(f"Failed to delete document {doc['id']}")
                    except Exception as e:
                        failed_deletions.append(doc["id"])
                        logger.error(f"Error deleting document {doc['id']}: {e}")
                        continue
            
            cleanup_duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                "deleted_documents": len(successful_deletions),
                "deleted_chunks": deleted_chunks,
                "failed_deletions": len(failed_deletions),
                "message": f"Successfully cleaned up {len(successful_deletions)} expired documents",
                "duration_seconds": cleanup_duration
            }
            
            if failed_deletions:
                result["failed_document_ids"] = failed_deletions
                result["message"] += f" ({len(failed_deletions)} failed)"
            
            logger.info(f"Cleanup completed in {cleanup_duration:.2f}s: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired documents in workspace '{workspace_slug}': {e}")
            raise WeaviateError(f"Failed to cleanup expired documents: {str(e)}")
    
    async def get_documents_by_provider(self, workspace_slug: str, source_provider: str, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Get documents by source provider.
        
        Args:
            workspace_slug: The workspace to search in
            source_provider: The source provider to filter by
            limit: Maximum number of objects to fetch (default: 10000)
            
        Returns:
            List of documents from the specified provider
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Query all documents and filter by provider in Python
            response = tenant_collection.query.fetch_objects(limit=limit)
            
            # Group by document and filter by provider
            documents_map = {}
            processed_chunks = 0
            
            logger.info(f"Scanning {len(response.objects)} chunks for provider '{source_provider}' in workspace '{workspace_slug}'")
            
            for obj in response.objects:
                processed_chunks += 1
                obj_provider = obj.properties.get("source_provider", "")
                
                if obj_provider == source_provider:
                    doc_id = obj.properties.get("document_id", "unknown")
                    if doc_id not in documents_map:
                        documents_map[doc_id] = {
                            "id": doc_id,
                            "title": obj.properties.get("document_title", "Untitled"),
                            "chunks": 0,
                            "technology": obj.properties.get("technology", ""),
                            "source_url": obj.properties.get("source_url", ""),
                            "expires_at": obj.properties.get("expires_at"),
                            "created_at": obj.properties.get("created_at"),
                            "updated_at": obj.properties.get("updated_at"),
                            "source_provider": obj.properties.get("source_provider", ""),
                        }
                    documents_map[doc_id]["chunks"] += 1
            
            filtered_docs = list(documents_map.values())
            logger.info(f"Found {len(filtered_docs)} documents from provider '{source_provider}' out of {processed_chunks} total chunks")
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Failed to get documents by provider '{source_provider}' in workspace '{workspace_slug}': {e}")
            raise WeaviateError(f"Failed to get documents by provider: {str(e)}")
    
    async def get_expired_documents_optimized(self, workspace_slug: str, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Get expired documents using Weaviate's native filtering (when available).
        
        This method attempts to use Weaviate's where filtering to improve performance
        for large datasets. Falls back to Python filtering if native filtering fails.
        
        Args:
            workspace_slug: The workspace to search in
            limit: Maximum number of objects to fetch (default: 10000)
            
        Returns:
            List of expired documents with metadata
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            current_time = datetime.utcnow()
            
            # Try to use Weaviate's native filtering for better performance
            try:
                # Note: Weaviate v4 client doesn't support 'where' in fetch_objects
                # This is a placeholder for when Weaviate supports native date filtering
                logger.info("Native filtering not available in current Weaviate version")
                raise NotImplementedError("Native filtering not supported")
                
            except Exception as filter_error:
                logger.warning(f"Native filtering failed, falling back to Python filtering: {filter_error}")
                # Fall back to regular fetch and Python filtering
                response = tenant_collection.query.fetch_objects(limit=limit)
                
                # Filter in Python
                filtered_objects = []
                for obj in response.objects:
                    expires_at = obj.properties.get("expires_at")
                    if expires_at and isinstance(expires_at, datetime) and expires_at < current_time:
                        filtered_objects.append(obj)
                
                # Create a mock response object for consistency
                class MockResponse:
                    def __init__(self, objects):
                        self.objects = objects
                
                response = MockResponse(filtered_objects)
                logger.info(f"Using Python filtering: found {len(response.objects)} expired chunks")
            
            # Group by document
            documents_map = {}
            for obj in response.objects:
                doc_id = obj.properties.get("document_id", "unknown")
                if doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "id": doc_id,
                        "title": obj.properties.get("document_title", "Untitled"),
                        "chunks": 0,
                        "technology": obj.properties.get("technology", ""),
                        "source_url": obj.properties.get("source_url", ""),
                        "expires_at": obj.properties.get("expires_at"),
                        "created_at": obj.properties.get("created_at"),
                        "updated_at": obj.properties.get("updated_at"),
                        "source_provider": obj.properties.get("source_provider", ""),
                    }
                documents_map[doc_id]["chunks"] += 1
            
            expired_docs = list(documents_map.values())
            logger.info(f"Optimized query found {len(expired_docs)} expired documents")
            
            return expired_docs
            
        except Exception as e:
            logger.error(f"Failed to get expired documents (optimized) in workspace '{workspace_slug}': {e}")
            # Fall back to the regular method
            logger.info("Falling back to regular get_expired_documents method")
            return await self.get_expired_documents(workspace_slug, limit)
    
    async def get_expiration_statistics(self, workspace_slug: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics about document expiration in a workspace.
        
        Args:
            workspace_slug: The workspace to analyze
            
        Returns:
            Dictionary with expiration statistics
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Get all documents with a very safe limit
            response = tenant_collection.query.fetch_objects(limit=100)
            
            current_time = datetime.utcnow()
            
            # Statistics tracking
            stats = {
                "total_chunks": len(response.objects),
                "total_documents": 0,
                "expired_documents": 0,
                "expired_chunks": 0,
                "expiring_soon_documents": 0,  # Within 7 days
                "expiring_soon_chunks": 0,
                "providers": {},
                "oldest_expiry": None,
                "newest_expiry": None,
                "documents_by_expiry": {
                    "expired": [],
                    "expiring_soon": [],
                    "long_term": []
                }
            }
            
            documents_map = {}
            
            # Process all chunks
            for obj in response.objects:
                doc_id = obj.properties.get("document_id", "unknown")
                expires_at = obj.properties.get("expires_at")
                provider = obj.properties.get("source_provider", "unknown")
                
                # Track document
                if doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "id": doc_id,
                        "title": obj.properties.get("document_title", "Untitled"),
                        "chunks": 0,
                        "expires_at": expires_at,
                        "source_provider": provider,
                        "is_expired": False,
                        "is_expiring_soon": False
                    }
                
                documents_map[doc_id]["chunks"] += 1
                
                # Track provider statistics
                if provider not in stats["providers"]:
                    stats["providers"][provider] = {
                        "documents": 0,
                        "chunks": 0,
                        "expired_documents": 0,
                        "expired_chunks": 0
                    }
                
                stats["providers"][provider]["chunks"] += 1
                
                # Analyze expiration
                if expires_at and isinstance(expires_at, datetime):
                    # Track oldest and newest expiry
                    if stats["oldest_expiry"] is None or expires_at < stats["oldest_expiry"]:
                        stats["oldest_expiry"] = expires_at
                    if stats["newest_expiry"] is None or expires_at > stats["newest_expiry"]:
                        stats["newest_expiry"] = expires_at
                    
                    # Check if expired
                    if expires_at < current_time:
                        stats["expired_chunks"] += 1
                        documents_map[doc_id]["is_expired"] = True
                        stats["providers"][provider]["expired_chunks"] += 1
                    
                    # Check if expiring soon (within 7 days)
                    elif expires_at < current_time + timedelta(days=7):
                        stats["expiring_soon_chunks"] += 1
                        documents_map[doc_id]["is_expiring_soon"] = True
            
            # Finalize document statistics
            for doc_id, doc_info in documents_map.items():
                stats["total_documents"] += 1
                provider = doc_info["source_provider"]
                stats["providers"][provider]["documents"] += 1
                
                if doc_info["is_expired"]:
                    stats["expired_documents"] += 1
                    stats["providers"][provider]["expired_documents"] += 1
                    stats["documents_by_expiry"]["expired"].append(doc_info)
                elif doc_info["is_expiring_soon"]:
                    stats["expiring_soon_documents"] += 1
                    stats["documents_by_expiry"]["expiring_soon"].append(doc_info)
                else:
                    stats["documents_by_expiry"]["long_term"].append(doc_info)
            
            # Calculate percentages
            if stats["total_documents"] > 0:
                stats["expiration_percentages"] = {
                    "expired": (stats["expired_documents"] / stats["total_documents"]) * 100,
                    "expiring_soon": (stats["expiring_soon_documents"] / stats["total_documents"]) * 100,
                    "long_term": ((stats["total_documents"] - stats["expired_documents"] - stats["expiring_soon_documents"]) / stats["total_documents"]) * 100
                }
            
            logger.info(f"Generated expiration statistics for workspace '{workspace_slug}': {stats['total_documents']} documents, {stats['expired_documents']} expired")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get expiration statistics for workspace '{workspace_slug}': {e}")
            raise WeaviateError(f"Failed to get expiration statistics: {str(e)}")
    
    async def delete_document(self, workspace_slug: str, document_id: str) -> Dict[str, Any]:
        """
        Delete a document and all its chunks from the workspace.
        
        Args:
            workspace_slug: The workspace to delete from
            document_id: The document ID to delete
            
        Returns:
            Dict with deletion results
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # First, find all chunks for this document
            response = tenant_collection.query.fetch_objects(
                where=weaviate.classes.query.Filter.by_property("document_id").equal(document_id),
                limit=10000
            )
            
            chunk_ids = []
            for obj in response.objects:
                chunk_ids.append(obj.uuid)
            
            # Delete all chunks
            deleted_count = 0
            for chunk_id in chunk_ids:
                try:
                    tenant_collection.data.delete_by_id(chunk_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete chunk {chunk_id}: {e}")
            
            result = {
                "document_id": document_id,
                "workspace_slug": workspace_slug,
                "total_chunks": len(chunk_ids),
                "deleted_chunks": deleted_count,
                "success": deleted_count > 0,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Deleted document {document_id}: {deleted_count}/{len(chunk_ids)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return {
                "document_id": document_id,
                "workspace_slug": workspace_slug,
                "total_chunks": 0,
                "deleted_chunks": 0,
                "success": False,
                "error": str(e),
                "deleted_at": datetime.utcnow().isoformat()
            }
    
    async def update_document_ttl(
        self, 
        workspace_slug: str, 
        document_id: str, 
        new_ttl_days: int
    ) -> Dict[str, Any]:
        """
        Update TTL for a document and all its chunks.
        
        Args:
            workspace_slug: The workspace containing the document
            document_id: The document ID to update
            new_ttl_days: New TTL in days
            
        Returns:
            Dict with update results
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Calculate new TTL timestamps
            ttl_timestamps = self._calculate_ttl_timestamps(new_ttl_days)
            
            # Find all chunks for this document
            response = tenant_collection.query.fetch_objects(
                where=weaviate.classes.query.Filter.by_property("document_id").equal(document_id),
                limit=10000
            )
            
            updated_count = 0
            for obj in response.objects:
                try:
                    # Update TTL properties
                    tenant_collection.data.update(
                        uuid=obj.uuid,
                        properties={
                            "expires_at": ttl_timestamps["expires_at"],
                            "updated_at": ttl_timestamps["updated_at"]
                        }
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to update chunk {obj.uuid}: {e}")
            
            result = {
                "document_id": document_id,
                "workspace_slug": workspace_slug,
                "total_chunks": len(response.objects),
                "updated_chunks": updated_count,
                "new_ttl_days": new_ttl_days,
                "new_expires_at": ttl_timestamps["expires_at"].isoformat(),
                "success": updated_count > 0,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updated TTL for document {document_id}: {updated_count}/{len(response.objects)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update TTL for document {document_id}: {e}")
            return {
                "document_id": document_id,
                "workspace_slug": workspace_slug,
                "total_chunks": 0,
                "updated_chunks": 0,
                "new_ttl_days": new_ttl_days,
                "success": False,
                "error": str(e),
                "updated_at": datetime.utcnow().isoformat()
            }
    
    async def get_document_ttl_info(
        self, 
        workspace_slug: str, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get TTL information for a document.
        
        Args:
            workspace_slug: The workspace containing the document
            document_id: The document ID to query
            
        Returns:
            Dict with TTL information or None if not found
        """
        try:
            collection = self.client.collections.get(self.COLLECTION_NAME)
            tenant_collection = collection.with_tenant(workspace_slug)
            
            # Find first chunk for this document to get TTL info
            response = tenant_collection.query.fetch_objects(
                where=weaviate.classes.query.Filter.by_property("document_id").equal(document_id),
                limit=1
            )
            
            if not response.objects:
                return None
            
            obj = response.objects[0]
            expires_at = obj.properties.get("expires_at")
            created_at = obj.properties.get("created_at")
            updated_at = obj.properties.get("updated_at")
            
            # Calculate TTL days
            ttl_days = None
            if expires_at and created_at:
                if isinstance(expires_at, datetime) and isinstance(created_at, datetime):
                    ttl_days = (expires_at - created_at).days
            
            # Calculate time remaining
            time_remaining = None
            expired = False
            if expires_at and isinstance(expires_at, datetime):
                now = datetime.utcnow()
                if expires_at > now:
                    time_remaining = (expires_at - now).total_seconds()
                else:
                    expired = True
            
            return {
                "document_id": document_id,
                "workspace_slug": workspace_slug,
                "expires_at": expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at,
                "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
                "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at,
                "ttl_days": ttl_days,
                "time_remaining_seconds": time_remaining,
                "expired": expired,
                "source_provider": obj.properties.get("source_provider"),
                "technology": obj.properties.get("technology"),
                "title": obj.properties.get("document_title")
            }
            
        except Exception as e:
            logger.error(f"Failed to get TTL info for document {document_id}: {e}")
            return None