#!/usr/bin/env python3
"""
Initialize default AnythingLLM workspace for DocAIche
This ensures a workspace exists for document uploads and searches
"""

import os
import time
import requests
import logging
import json
from datetime import datetime

# Use structured logging
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
    start_time = time.time()
    correlation_id = f"init_workspace_{int(time.time() * 1000)}"
    
    base_url = os.getenv("ANYTHINGLLM_URL", "http://anythingllm:3001")
    # Check for actual API key first, then fall back to AUTH_TOKEN (which won't work for API)
    api_key = os.getenv("ANYTHINGLLM_API_KEY")
    auth_token = os.getenv("ANYTHINGLLM_AUTH_TOKEN", "docaiche-lab-default-key-2025")
    
    # If no real API key is set, we're using AUTH_TOKEN which won't work
    if not api_key or api_key == auth_token:
        logger.warning("⚠️ No valid API key found. AnythingLLM requires an API key for programmatic access.", extra={
            "event": "workspace_init_skipped",
            "correlation_id": correlation_id,
            "reason": "no_api_key",
            "message": "AUTH_TOKEN is for web interface only. Please create an API key through the AnythingLLM interface.",
            "timestamp": datetime.now().isoformat()
        })
        
        # Check if we can read a saved API key
        api_key_file = "/data/.anythingllm-api-key"
        if os.path.exists(api_key_file):
            try:
                with open(api_key_file, 'r') as f:
                    api_key = f.read().strip()
                logger.info("✅ Found saved API key", extra={
                    "event": "api_key_loaded",
                    "correlation_id": correlation_id,
                    "source": "file"
                })
            except Exception as e:
                logger.error(f"Failed to read API key file: {e}")
                return False
        else:
            # No API key available, skip initialization
            logger.info("""
📝 AnythingLLM API Key Setup Required:

1. Access AnythingLLM at http://localhost:3001
2. Login with AUTH_TOKEN: {auth_token}
3. Navigate to Settings > API Keys
4. Create a new API key
5. Save it as ANYTHINGLLM_API_KEY in docker-compose.yml
6. Rebuild and restart: docker-compose up -d --build

Until then, document search functionality will be unavailable.
""".format(auth_token=auth_token))
            return False
    
    logger.info("🚀 Starting AnythingLLM workspace initialization...", extra={
        "event": "workspace_init_start",
        "correlation_id": correlation_id,
        "base_url": base_url,
        "has_api_key": bool(api_key),
        "timestamp": datetime.now().isoformat()
    })
    
    # Wait for AnythingLLM to be ready
    logger.info("Waiting for AnythingLLM to be ready...")
    if not wait_for_service(f"{base_url}/api/v1/health"):
        logger.error("AnythingLLM not available after timeout", extra={
            "event": "workspace_init_failed",
            "correlation_id": correlation_id,
            "error": "service_timeout",
            "duration_ms": (time.time() - start_time) * 1000
        })
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
                        logger.info("✅ Default workspace already exists", extra={
                            "event": "workspace_init_complete",
                            "correlation_id": correlation_id,
                            "workspace_slug": "docaiche-default",
                            "status": "existing",
                            "duration_ms": (time.time() - start_time) * 1000
                        })
                        return True
            elif isinstance(workspaces, dict) and workspaces.get("workspaces"):
                for ws in workspaces["workspaces"]:
                    if ws.get("slug") == "docaiche-default":
                        logger.info("✅ Default workspace already exists", extra={
                            "event": "workspace_init_complete",
                            "correlation_id": correlation_id,
                            "workspace_slug": "docaiche-default",
                            "status": "existing",
                            "duration_ms": (time.time() - start_time) * 1000
                        })
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
            logger.info("✅ Default workspace created successfully!", extra={
                "event": "workspace_init_complete",
                "correlation_id": correlation_id,
                "workspace_slug": "docaiche-default",
                "status": "created",
                "duration_ms": (time.time() - start_time) * 1000
            })
            return True
        else:
            logger.error(f"Failed to create workspace: {response.status_code} - {response.text}", extra={
                "event": "workspace_init_failed",
                "correlation_id": correlation_id,
                "error": "create_failed",
                "status_code": response.status_code,
                "response": response.text,
                "duration_ms": (time.time() - start_time) * 1000
            })
            return False
            
    except Exception as e:
        logger.error(f"Error initializing workspace: {e}", extra={
            "event": "workspace_init_failed",
            "correlation_id": correlation_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": (time.time() - start_time) * 1000
        })
        return False

if __name__ == "__main__":
    init_workspace()