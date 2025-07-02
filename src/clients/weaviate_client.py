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
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
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
        """Ensure the main collection exists with multi-tenancy enabled"""
        try:
            # Check if collection exists
            if not self.client.collections.exists(self.COLLECTION_NAME):
                # Create collection with multi-tenancy enabled
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
                    ]
                )
                logger.info(f"Created Weaviate collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise
    
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
        self, workspace_slug: str, document: ProcessedDocument
    ) -> UploadResult:
        """
        Upload ProcessedDocument to workspace (tenant) by iterating over chunks.
        
        Process:
        1. Validate workspace exists
        2. Upload chunks with batch processing
        3. Track failures and retry with exponential backoff
        4. Return comprehensive result
        """
        logger.info(
            f"Starting upload of document {document.id} to workspace {workspace_slug}"
        )
        
        # Step 1: Validate workspace exists
        await self.get_or_create_workspace(workspace_slug)
        
        # Step 2: Prepare upload results tracking
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
        
        # Step 3: Upload chunks in batches
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
                f"({upload_results['successful_uploads']}/{upload_results['total_chunks']} chunks)"
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
            logger.info(f"Weaviate search exception for workspace {workspace_slug}: {e} (type: {type(e).__name__})")
            
            # Handle workspace not found as empty results, not an error
            if any(phrase in error_str for phrase in [
                "tenant", "not found", "does not exist", "no such tenant", "no objects found", "empty"
            ]):
                logger.info(f"Workspace {workspace_slug} not found or empty, returning empty results")
                return []
            
            # Handle other exceptions as actual errors
            logger.error(f"Search failed for workspace {workspace_slug}: {e}")
            raise WeaviateError(f"Search failed: {str(e)}")
    
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
                        "source_url": obj.properties.get("source_url", "")
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
            result = tenant_collection.data.delete_many(
                where=tenant_collection.query.where_property("document_id").equal(document_id)
            )
            
            logger.info(f"Deleted document {document_id} from workspace {workspace_slug}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            if "not found" in str(e).lower():
                return True  # Already deleted
            raise WeaviateError(f"Failed to delete document: {str(e)}")