#!/usr/bin/env python3
"""
Initialize Weaviate workspaces (tenants) for DocAIche system
Replaces AnythingLLM workspace initialization with Weaviate multi-tenancy setup
"""

import asyncio
import os
import sys
import logging
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, '/app')

from src.clients.weaviate_client import WeaviateVectorClient
from src.core.config.models import WeaviateConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default workspaces to create
DEFAULT_WORKSPACES = [
    {
        "slug": "react-docs",
        "name": "React Documentation"
    },
    {
        "slug": "vue-docs", 
        "name": "Vue.js Documentation"
    },
    {
        "slug": "angular-docs",
        "name": "Angular Documentation"
    },
    {
        "slug": "python-docs",
        "name": "Python Documentation"
    },
    {
        "slug": "typescript-docs",
        "name": "TypeScript Documentation"
    },
    {
        "slug": "nodejs-docs",
        "name": "Node.js Documentation"
    },
    {
        "slug": "general-tech",
        "name": "General Technology"
    }
]


async def wait_for_weaviate(client: WeaviateVectorClient, max_retries: int = 30) -> bool:
    """Wait for Weaviate to be ready"""
    logger.info("Waiting for Weaviate to be ready...")
    
    for attempt in range(max_retries):
        try:
            health = await client.health_check()
            if health.get("ready", False):
                logger.info("Weaviate is ready!")
                return True
        except Exception as e:
            logger.debug(f"Weaviate not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
        
        await asyncio.sleep(2)
    
    logger.error("Weaviate failed to become ready within timeout")
    return False


async def initialize_workspaces(client: WeaviateVectorClient, workspaces: List[Dict[str, str]]) -> None:
    """Initialize default workspaces in Weaviate"""
    logger.info(f"Checking {len(workspaces)} default workspaces...")
    
    # First, check which workspaces already exist
    try:
        existing_workspaces = await client.list_workspaces()
        existing_slugs = {ws.get("slug") for ws in existing_workspaces}
        logger.info(f"Found {len(existing_slugs)} existing workspaces: {sorted(existing_slugs)}")
    except Exception as e:
        logger.warning(f"Could not check existing workspaces: {e}")
        existing_slugs = set()
    
    # Only create workspaces that don't exist
    created_count = 0
    skipped_count = 0
    
    for workspace in workspaces:
        workspace_slug = workspace["slug"]
        try:
            if workspace_slug in existing_slugs:
                logger.info(f"⚪ Workspace already exists, skipping: {workspace_slug}")
                skipped_count += 1
                continue
                
            result = await client.get_or_create_workspace(
                workspace_slug=workspace_slug,
                name=workspace["name"]
            )
            logger.info(f"✓ Workspace created: {workspace_slug} - {workspace['name']}")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ Failed to initialize workspace {workspace_slug}: {e}")
    
    logger.info(f"Workspace initialization complete: {created_count} created, {skipped_count} already existed")


async def main():
    """Main initialization function"""
    logger.info("Starting Weaviate workspace initialization...")
    
    # Configure Weaviate client
    weaviate_url = os.environ.get("WEAVIATE_URL", "http://weaviate:8080")
    weaviate_api_key = os.environ.get("WEAVIATE_API_KEY", "docaiche-weaviate-key-2025")
    
    config = WeaviateConfig(
        endpoint=weaviate_url,
        api_key=weaviate_api_key
    )
    
    # Initialize client
    async with WeaviateVectorClient(config) as client:
        # Wait for Weaviate to be ready
        if not await wait_for_weaviate(client):
            logger.error("Failed to connect to Weaviate")
            sys.exit(1)
        
        # Initialize workspaces
        await initialize_workspaces(client, DEFAULT_WORKSPACES)
        
        # List all workspaces to confirm
        try:
            all_workspaces = await client.list_workspaces()
            logger.info(f"\nTotal workspaces available: {len(all_workspaces)}")
            for ws in all_workspaces:
                logger.info(f"  - {ws['slug']}: {ws['name']} (Status: {ws.get('status', 'ACTIVE')})")
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
    
    logger.info("\nWeaviate workspace initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())