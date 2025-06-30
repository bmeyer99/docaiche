"""
Collections Resource
===================

Provides access to available documentation collections.
"""

import logging
from typing import Dict, Any

from .base_resource import BaseResource
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class CollectionsResource(BaseResource):
    """Documentation collections resource"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__(
            uri_prefix="docaiche://collections",
            description="List available documentation collections"
        )
        self.db_manager = db_manager
    
    async def read(self, uri: str) -> Dict[str, Any]:
        """
        Read collections data.
        
        Args:
            uri: Resource URI (e.g., docaiche://collections)
            
        Returns:
            Collections data
        """
        try:
            if self.db_manager:
                # Get collections from database
                # Note: Using workspace instead of collection based on schema
                query = """
                SELECT DISTINCT 
                    workspace,
                    technology,
                    COUNT(*) as document_count
                FROM content_metadata
                WHERE status = 'active'
                GROUP BY workspace, technology
                ORDER BY workspace
                """
                
                rows = await self.db_manager.fetch_all(query)
                
                collections = {}
                for row in rows:
                    collection_name = row['workspace']
                    if collection_name not in collections:
                        collections[collection_name] = {
                            "name": collection_name,
                            "technologies": [],
                            "document_count": 0
                        }
                    
                    if row['technology']:
                        collections[collection_name]["technologies"].append(row['technology'])
                    collections[collection_name]["document_count"] += row['document_count']
                
                return {
                    "uri": uri,
                    "name": "Documentation Collections",
                    "mimeType": "application/json",
                    "text": {
                        "collections": list(collections.values()),
                        "total_collections": len(collections)
                    }
                }
            else:
                # Return mock data if no database
                logger.warning("Database not available, returning mock collections")
                return {
                    "uri": uri,
                    "name": "Documentation Collections",
                    "mimeType": "application/json", 
                    "text": {
                        "collections": [
                            {
                                "name": "default",
                                "technologies": ["python", "javascript"],
                                "document_count": 0
                            }
                        ],
                        "total_collections": 1
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to read collections: {e}", exc_info=True)
            raise ValueError(f"Failed to read collections: {str(e)}")