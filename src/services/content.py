"""
Content service implementation.

Handles content management operations including document ingestion,
metadata management, and collection operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from src.database.manager import DatabaseManager
from src.api.schemas import (
    ContentIngestionRequest, ContentIngestionResponse,
    ContentMetadata, ContentCollection,
    ContentStatsResponse
)


class ContentService:
    """Service for handling content management operations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the content service.
        
        Args:
            db_manager: Optional DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
    
    async def ingest_content(self, request: ContentIngestionRequest) -> ContentIngestionResponse:
        """
        Process and store new content in the system.
        
        Args:
            request: Content ingestion request with URL and metadata
            
        Returns:
            ContentIngestionResponse with ingestion status
        """
        if not self.db_manager:
            return ContentIngestionResponse(
                content_id="",
                status="failed",
                message="Database manager not available"
            )
        
        try:
            # Generate unique content ID
            content_id = str(uuid.uuid4())
            
            # Insert content metadata into database
            query = """
            INSERT INTO content_metadata (
                content_id, title, content, source_url, technology,
                content_type, workspace, created_at, updated_at, metadata
            ) VALUES (
                :content_id, :title, :content, :source_url, :technology,
                :content_type, :workspace, :created_at, :updated_at, :metadata
            )
            """
            
            params = {
                "content_id": content_id,
                "title": request.title or f"Content from {request.source_url}",
                "content": request.content or "",
                "source_url": request.source_url,
                "technology": request.technology,
                "content_type": request.content_type or "document",
                "workspace": request.workspace or "default",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": request.metadata or {}
            }
            
            await self.db_manager.execute(query, params)
            
            return ContentIngestionResponse(
                content_id=content_id,
                status="completed",
                message="Content ingested successfully"
            )
            
        except Exception as e:
            return ContentIngestionResponse(
                content_id="",
                status="failed",
                message=f"Ingestion failed: {str(e)}"
            )
    
    async def get_content_metadata(self, content_id: str) -> Optional[ContentMetadata]:
        """
        Retrieve metadata for a specific content item.
        
        Args:
            content_id: Unique content identifier
            
        Returns:
            ContentMetadata if found, None otherwise
        """
        if not self.db_manager:
            return None
        
        try:
            query = """
            SELECT content_id, title, source_url, technology, content_type,
                   workspace, created_at, updated_at, metadata
            FROM content_metadata
            WHERE content_id = :content_id
            """
            
            result = await self.db_manager.fetch_one(query, {"content_id": content_id})
            
            if result:
                return ContentMetadata(
                    content_id=result["content_id"],
                    title=result["title"],
                    source_url=result["source_url"],
                    technology=result["technology"],
                    content_type=result["content_type"],
                    workspace=result["workspace"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                    metadata=result["metadata"] or {}
                )
            
            return None
            
        except Exception:
            return None
    
    async def list_collections(self) -> List[ContentCollection]:
        """
        List all content collections (workspaces).
        
        Returns:
            List of ContentCollection objects
        """
        if not self.db_manager:
            return []
        
        try:
            query = """
            SELECT workspace, COUNT(*) as item_count,
                   MIN(created_at) as created_at,
                   MAX(updated_at) as updated_at
            FROM content_metadata
            GROUP BY workspace
            ORDER BY workspace
            """
            
            results = await self.db_manager.fetch_all(query, {})
            
            collections = []
            for row in results:
                collections.append(ContentCollection(
                    collection_id=row["workspace"],
                    name=row["workspace"],
                    description=f"Collection: {row['workspace']}",
                    item_count=row["item_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                ))
            
            return collections
            
        except Exception:
            return []
    
    async def get_content_stats(self) -> ContentStatsResponse:
        """
        Get statistics about content in the system.
        
        Returns:
            ContentStatsResponse with content statistics
        """
        if not self.db_manager:
            return ContentStatsResponse(
                total_documents=0,
                by_technology={},
                by_content_type={},
                by_workspace={},
                last_updated=datetime.utcnow()
            )
        
        try:
            # Get total document count
            total_query = "SELECT COUNT(*) as count FROM content_metadata"
            total_result = await self.db_manager.fetch_one(total_query, {})
            total_documents = total_result["count"] if total_result else 0
            
            # Get counts by technology
            tech_query = """
            SELECT technology, COUNT(*) as count
            FROM content_metadata
            WHERE technology IS NOT NULL
            GROUP BY technology
            """
            tech_results = await self.db_manager.fetch_all(tech_query, {})
            by_technology = {row["technology"]: row["count"] for row in tech_results}
            
            # Get counts by content type
            type_query = """
            SELECT content_type, COUNT(*) as count
            FROM content_metadata
            WHERE content_type IS NOT NULL
            GROUP BY content_type
            """
            type_results = await self.db_manager.fetch_all(type_query, {})
            by_content_type = {row["content_type"]: row["count"] for row in type_results}
            
            # Get counts by workspace
            workspace_query = """
            SELECT workspace, COUNT(*) as count
            FROM content_metadata
            GROUP BY workspace
            """
            workspace_results = await self.db_manager.fetch_all(workspace_query, {})
            by_workspace = {row["workspace"]: row["count"] for row in workspace_results}
            
            return ContentStatsResponse(
                total_documents=total_documents,
                by_technology=by_technology,
                by_content_type=by_content_type,
                by_workspace=by_workspace,
                last_updated=datetime.utcnow()
            )
            
        except Exception:
            return ContentStatsResponse(
                total_documents=0,
                by_technology={},
                by_content_type={},
                by_workspace={},
                last_updated=datetime.utcnow()
            )
    
    async def delete_content(self, content_id: str) -> bool:
        """
        Delete a content item from the system.
        
        Args:
            content_id: Unique content identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.db_manager:
            return False
        
        try:
            query = "DELETE FROM content_metadata WHERE content_id = :content_id"
            await self.db_manager.execute(query, {"content_id": content_id})
            return True
        except Exception:
            return False