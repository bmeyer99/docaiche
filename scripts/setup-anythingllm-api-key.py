#!/usr/bin/env python3
"""
Setup AnythingLLM API Key

This script logs into AnythingLLM using the AUTH_TOKEN and creates an API key
for programmatic access. This is required because AUTH_TOKEN is only for
web interface access, not API access.
"""

import os
import sys
import time
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_service(url, timeout=60):
    """Wait for a service to be available"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code in [200, 401]:  # 401 is ok, means auth is required
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    return False

def setup_api_key():
    """Setup AnythingLLM API key by logging in with AUTH_TOKEN"""
    base_url = os.getenv("ANYTHINGLLM_URL", "http://localhost:3001")
    auth_token = os.getenv("ANYTHINGLLM_AUTH_TOKEN", "docaiche-lab-default-key-2025")
    
    logger.info(f"Setting up AnythingLLM API key at {base_url}")
    
    # Wait for service
    if not wait_for_service(f"{base_url}/api/v1/health"):
        logger.error("AnythingLLM not available")
        return None
    
    # First, we need to authenticate with the AUTH_TOKEN
    # This requires a login flow, not just API headers
    
    # Check if we can access the API docs endpoint
    try:
        # Try to get system settings to see if we need to setup
        response = requests.get(f"{base_url}/api/system/settings")
        
        if response.status_code == 401:
            logger.info("Authentication required - this is expected for initial setup")
            
            # The AUTH_TOKEN is used for initial setup/login
            # We need to create a session and get an API key through the interface
            
            # For Docker deployments, AnythingLLM might auto-create an API key
            # Let's check if there's a default API key file
            storage_dir = os.getenv("STORAGE_DIR", "/app/server/storage")
            api_key_file = os.path.join(storage_dir, ".api-key")
            
            if os.path.exists(api_key_file):
                with open(api_key_file, 'r') as f:
                    api_key = f.read().strip()
                logger.info("Found existing API key file")
                return api_key
            
            # If no API key file exists, we need manual setup
            logger.warning("""
No API key found. Please complete the following steps:

1. Open AnythingLLM at {base_url}
2. Login with AUTH_TOKEN: {auth_token}
3. Go to Settings > API Keys
4. Create a new API key
5. Save the API key and update ANYTHINGLLM_API_KEY in docker-compose.yml
6. Restart the containers

Alternatively, if you have an existing API key, set it as:
ANYTHINGLLM_API_KEY=your-api-key
""".format(base_url=base_url, auth_token=auth_token))
            
            return None
            
    except Exception as e:
        logger.error(f"Error checking AnythingLLM: {e}")
        return None

def save_api_key_to_env(api_key):
    """Save API key to environment file"""
    env_file = "/data/.anythingllm-api-key"
    
    try:
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
        with open(env_file, 'w') as f:
            f.write(api_key)
        logger.info(f"API key saved to {env_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        return False

def main():
    """Main setup function"""
    # Check if API key already exists in environment
    existing_key = os.getenv("ANYTHINGLLM_API_KEY")
    if existing_key and existing_key != "docaiche-lab-default-key-2025":
        logger.info("API key already configured in environment")
        return 0
    
    # Try to setup API key
    api_key = setup_api_key()
    
    if api_key:
        # Save to persistent storage
        if save_api_key_to_env(api_key):
            logger.info("API key setup completed successfully")
            return 0
        else:
            logger.error("Failed to save API key")
            return 1
    else:
        logger.warning("API key setup requires manual intervention")
        return 2

if __name__ == "__main__":
    sys.exit(main())