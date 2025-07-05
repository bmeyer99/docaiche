#!/usr/bin/env python3
"""
Test script to query Weaviate for Context7 documents with TTL metadata.
This checks if Context7 results are actually being ingested and stored.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
import json
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.database.connection import DatabaseManager
from src.clients.weaviate_client import WeaviateVectorClient
from src.core.config import get_system_configuration

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def query_context7_documents():
    """Query Weaviate for Context7 documents and check TTL metadata."""
    
    config = get_system_configuration()
    db_manager = await DatabaseManager.create(config.database)
    weaviate_client = WeaviateVectorClient(config)
    
    try:
        logger.info("=== Context7 Document Query in Weaviate ===")
        
        # 1. Check if workspace exists
        workspaces = await weaviate_client.list_workspaces()
        logger.info(f"Available workspaces: {workspaces}")
        
        # 2. Query for documents with source_provider='context7'
        logger.info("\nSearching for Context7 documents...")
        
        # Try to search across all workspaces for Context7 content
        context7_docs = []
        for workspace in workspaces:
            try:
                # Search for Context7 content in each workspace
                query = """
                {
                    Get {
                        %(class_name)s(
                            where: {
                                path: ["metadata", "source_provider"],
                                operator: Equal,
                                valueString: "context7"
                            }
                            limit: 10
                        ) {
                            _additional {
                                id
                                creationTimeUnix
                                lastUpdateTimeUnix
                            }
                            content
                            title
                            source_url
                            metadata
                        }
                    }
                }
                """ % {"class_name": workspace.replace("-", "_").title()}
                
                # Execute raw GraphQL query
                result = await weaviate_client.client.query.raw(query)
                
                if result and 'data' in result:
                    class_data = result['data']['Get'].get(workspace.replace("-", "_").title(), [])
                    if class_data:
                        logger.info(f"Found {len(class_data)} Context7 documents in workspace: {workspace}")
                        for doc in class_data:
                            doc['workspace'] = workspace
                            context7_docs.append(doc)
                            
            except Exception as e:
                logger.debug(f"Error querying workspace {workspace}: {e}")
                continue
        
        # 3. Display results
        if context7_docs:
            logger.info(f"\n=== Found {len(context7_docs)} Context7 Documents ===")
            for i, doc in enumerate(context7_docs[:5]):  # Show first 5
                logger.info(f"\nDocument {i+1}:")
                logger.info(f"  Workspace: {doc.get('workspace')}")
                logger.info(f"  Title: {doc.get('title', 'N/A')}")
                logger.info(f"  URL: {doc.get('source_url', 'N/A')}")
                
                metadata = doc.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        pass
                
                logger.info(f"  Metadata:")
                logger.info(f"    - Source Provider: {metadata.get('source_provider', 'N/A')}")
                logger.info(f"    - TTL Days: {metadata.get('ttl_days', 'N/A')}")
                logger.info(f"    - Expires At: {metadata.get('expires_at', 'N/A')}")
                logger.info(f"    - Technology: {metadata.get('technology', 'N/A')}")
                logger.info(f"    - Ingestion Type: {metadata.get('ingestion_type', 'N/A')}")
                
                # Check if document has expired
                expires_at = metadata.get('expires_at')
                if expires_at:
                    try:
                        expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        is_expired = datetime.utcnow() > expiry_time
                        time_until_expiry = expiry_time - datetime.utcnow()
                        logger.info(f"    - Expired: {'YES' if is_expired else 'NO'}")
                        if not is_expired:
                            logger.info(f"    - Time until expiry: {time_until_expiry}")
                    except:
                        pass
                
                # Show creation time
                if '_additional' in doc:
                    creation_time = doc['_additional'].get('creationTimeUnix')
                    if creation_time:
                        created_at = datetime.fromtimestamp(int(creation_time) / 1000)
                        logger.info(f"    - Created: {created_at.isoformat()}")
        else:
            logger.info("\nNo Context7 documents found in Weaviate")
        
        # 4. Check database for Context7 metadata
        logger.info("\n=== Checking Database for Context7 Metadata ===")
        
        db_query = """
        SELECT 
            content_id,
            source_url,
            title,
            technology,
            processing_status,
            enrichment_metadata,
            created_at,
            updated_at
        FROM content_metadata
        WHERE enrichment_metadata LIKE '%context7%'
           OR processing_status LIKE '%context7%'
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        db_results = await db_manager.fetch_all(db_query)
        
        if db_results:
            logger.info(f"Found {len(db_results)} Context7 entries in database:")
            for row in db_results[:5]:
                logger.info(f"\nDatabase Entry:")
                logger.info(f"  Content ID: {row['content_id']}")
                logger.info(f"  Title: {row['title']}")
                logger.info(f"  Technology: {row['technology']}")
                logger.info(f"  Status: {row['processing_status']}")
                logger.info(f"  Created: {row['created_at']}")
                
                if row['enrichment_metadata']:
                    try:
                        metadata = json.loads(row['enrichment_metadata'])
                        ttl_info = metadata.get('ttl_info', {})
                        if ttl_info:
                            logger.info(f"  TTL Info:")
                            logger.info(f"    - TTL Days: {ttl_info.get('ttl_days')}")
                            logger.info(f"    - Expires At: {ttl_info.get('expires_at')}")
                            logger.info(f"    - Source Provider: {ttl_info.get('source_provider')}")
                    except:
                        pass
        else:
            logger.info("No Context7 entries found in database")
        
        # 5. Check cache for Context7 content
        logger.info("\n=== Checking Cache for Context7 Content ===")
        
        # Check for any context7 cache keys
        cache_manager = db_manager.cache_manager
        if cache_manager:
            # Try to get some common Context7 cache patterns
            patterns = [
                "context7_content:*",
                "context7_content_ttl:*",
                "search:*context7*"
            ]
            
            for pattern in patterns:
                try:
                    # Note: This is a simplified check - actual implementation would need proper cache scanning
                    test_key = pattern.replace('*', 'test')
                    value = await cache_manager.get(test_key)
                    if value:
                        logger.info(f"Found cache entry for pattern {pattern}: {test_key}")
                except:
                    pass
        
        logger.info("\n=== Summary ===")
        logger.info(f"Context7 documents in Weaviate: {len(context7_docs)}")
        logger.info(f"Context7 entries in database: {len(db_results) if db_results else 0}")
        
        if not context7_docs and not db_results:
            logger.info("\n⚠️  No Context7 documents found in either Weaviate or database!")
            logger.info("This suggests that Context7 ingestion may not be working properly.")
            logger.info("\nPossible reasons:")
            logger.info("1. Sync ingestion is not enabled in configuration")
            logger.info("2. Context7 provider is not returning results")
            logger.info("3. Ingestion pipeline is failing")
            logger.info("4. Documents are being filtered out during processing")
        
    except Exception as e:
        logger.error(f"Error querying for Context7 documents: {e}", exc_info=True)
    finally:
        await db_manager.close()
        if hasattr(weaviate_client, 'close'):
            await weaviate_client.close()


if __name__ == "__main__":
    asyncio.run(query_context7_documents())