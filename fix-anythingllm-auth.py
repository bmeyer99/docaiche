#!/usr/bin/env python3
"""
Fix AnythingLLM authentication by creating a proper API key
"""

import os
import sys
import time
import json
import requests

def main():
    base_url = "http://anythingllm:3001"
    auth_token = "docaiche-lab-default-key-2025"
    
    print("🔧 Fixing AnythingLLM authentication...")
    
    # Step 1: Check if we can authenticate with the AUTH_TOKEN
    print("\n1. Testing AUTH_TOKEN authentication...")
    try:
        # The AUTH_TOKEN should work for admin endpoints
        response = requests.get(
            f"{base_url}/api/system/workspace-chats",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        print(f"   Response status: {response.status_code}")
        if response.status_code == 401:
            print("   ❌ AUTH_TOKEN not valid for API access")
        else:
            print("   ✅ AUTH_TOKEN accepted")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Step 2: Try to create an API key using the admin interface
    print("\n2. Attempting to create API key...")
    
    # First, we need to authenticate as admin
    # In AnythingLLM, the AUTH_TOKEN is used differently than API keys
    # We might need to use a different approach
    
    # Try the API key endpoint with AUTH_TOKEN
    try:
        response = requests.post(
            f"{base_url}/api/v1/admin/api-key/new",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"name": "DocAIche Default API Key"},
            timeout=10
        )
        print(f"   Response status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("apiKey", "")
            print(f"\n✅ API Key created: {api_key}")
            
            # Update the docker-compose.yml
            print("\n3. Updating docker-compose.yml...")
            with open("/app/docker-compose.yml", "r") as f:
                content = f.read()
            
            updated_content = content.replace(
                "ANYTHINGLLM_API_KEY=docaiche-lab-default-key-2025",
                f"ANYTHINGLLM_API_KEY={api_key}"
            )
            
            with open("/app/docker-compose.yml", "w") as f:
                f.write(updated_content)
            
            print("   ✅ Configuration updated")
            print("\n🎉 Authentication fixed! Restart the API container to apply changes.")
            return 0
            
    except Exception as e:
        print(f"   ❌ Error creating API key: {e}")
    
    # Step 3: Check available endpoints
    print("\n3. Checking available auth endpoints...")
    endpoints = [
        "/api/v1/admin/api-keys",
        "/api/admin/api-keys",
        "/api/system/api-keys",
        "/api/v1/system/api-key/new"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f"{base_url}{endpoint}",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=5
            )
            print(f"   {endpoint}: {response.status_code}")
        except:
            print(f"   {endpoint}: Failed")
    
    print("\n❌ Could not create API key automatically.")
    print("\n💡 Manual steps required:")
    print("1. Access AnythingLLM at http://localhost:3001")
    print("2. Use the AUTH_TOKEN to access: docaiche-lab-default-key-2025")
    print("3. Go to Settings -> API Keys")
    print("4. Create a new API key")
    print("5. Update ANYTHINGLLM_API_KEY in docker-compose.yml")
    print("6. Restart the containers")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())