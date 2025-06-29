#!/usr/bin/env python3
"""
Initialize default AnythingLLM workspace for DocAIche
This ensures a workspace exists for document uploads and searches
"""

import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_service(url, timeout=60):
    """Wait for a service to be available"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False

def init_workspace():
    """Initialize default AnythingLLM workspace"""
    base_url = os.getenv("ANYTHINGLLM_URL", "http://anythingllm:3001")
    api_key = os.getenv("ANYTHINGLLM_API_KEY", "docaiche-lab-default-key-2025")
    
    # Wait for AnythingLLM to be ready
    logger.info("Waiting for AnythingLLM to be ready...")
    if not wait_for_service(f"{base_url}/api/v1/health"):
        logger.error("AnythingLLM not available after timeout")
        return False
    
    logger.info("AnythingLLM is ready!")
    
    # Check existing workspaces
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(f"{base_url}/api/v1/workspaces", headers=headers)
        if response.status_code == 200:
            workspaces = response.json()
            
            # Check if default workspace exists
            if isinstance(workspaces, list):
                for ws in workspaces:
                    if ws.get("slug") == "docaiche-default":
                        logger.info("Default workspace already exists")
                        return True
            elif isinstance(workspaces, dict) and workspaces.get("workspaces"):
                for ws in workspaces["workspaces"]:
                    if ws.get("slug") == "docaiche-default":
                        logger.info("Default workspace already exists")
                        return True
        
        # Create default workspace
        logger.info("Creating default workspace...")
        create_data = {
            "name": "DocAIche Default",
            "slug": "docaiche-default",
            "onboardingComplete": True
        }
        
        response = requests.post(
            f"{base_url}/api/v1/workspace/new",
            headers=headers,
            json=create_data
        )
        
        if response.status_code in [200, 201]:
            logger.info("Default workspace created successfully!")
            return True
        else:
            logger.error(f"Failed to create workspace: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing workspace: {e}")
        return False

if __name__ == "__main__":
    init_workspace()