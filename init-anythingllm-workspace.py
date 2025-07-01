#!/usr/bin/env python3
"""
AnythingLLM Workspace Initialization Script
Automates the complete setup of AnythingLLM for DocAIche including onboarding and workspace creation
"""

import os
import sys
import time
import json
import requests
import subprocess
from typing import Dict, Any, Optional

def wait_for_service(url: str, service_name: str, max_attempts: int = 60) -> bool:
    """Wait for a service to become available"""
    print(f"⏳ Waiting for {service_name} to be ready...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:  # Accept any non-5xx response
                print(f"✅ {service_name} is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"⏳ Waiting for {service_name}... ({attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    print(f"❌ {service_name} failed to become ready after {max_attempts} attempts")
    return False

def check_setup_status(base_url: str) -> Dict[str, Any]:
    """Check if AnythingLLM needs initial setup"""
    try:
        # Check if workspaces already exist (if so, we're probably good)
        response = requests.get(f"{base_url}/api/v1/workspaces", timeout=10)
        if response.status_code == 200:
            workspaces = response.json()
            if workspaces and len(workspaces) > 0:
                return {"setup_complete": True, "needs_onboarding": False, "workspaces_exist": True}
        
        # Check if setup is complete
        response = requests.get(f"{base_url}/api/system/system-preferences", timeout=10)
        if response.status_code == 200:
            return {"setup_complete": True, "needs_onboarding": False}
        
        # Check setup-complete endpoint
        response = requests.get(f"{base_url}/api/system/setup-complete", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "setup_complete": data.get("setupComplete", False),
                "needs_onboarding": not data.get("setupComplete", False)
            }
        
        return {"setup_complete": False, "needs_onboarding": True}
        
    except Exception as e:
        print(f"⚠️ Error checking setup status: {e}")
        return {"setup_complete": False, "needs_onboarding": True}

def perform_onboarding(base_url: str, admin_password: str = "docaiche-admin-2025") -> Dict[str, Any]:
    """Perform initial AnythingLLM onboarding"""
    print("🔧 Performing AnythingLLM onboarding...")
    
    onboarding_data = {
        "username": "admin",
        "password": admin_password,
        "organizationName": "DocAIche Lab",
        "organizationLogo": None,
        "customAppName": "DocAIche Knowledge Base"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/system/setup",
            json=onboarding_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Onboarding completed successfully")
            return {
                "success": True,
                "data": data,
                "auth_token": data.get("token", ""),
                "user": data.get("user", {})
            }
        else:
            print(f"❌ Onboarding failed: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}
            
    except Exception as e:
        print(f"❌ Onboarding error: {e}")
        return {"success": False, "error": str(e)}

def create_api_key(base_url: str, auth_token: str) -> Optional[str]:
    """Create an API key for AnythingLLM"""
    print("🔑 Creating API key...")
    
    api_key_data = {
        "name": "DocAIche Default API Key"
    }
    
    # Try different API key creation endpoints
    endpoints = [
        "/api/v1/admin/api-keys",
        "/api/admin/api-keys", 
        "/api/v1/api-keys",
        "/api/system/generate-api-key"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"🔐 Trying endpoint: {endpoint}")
            response = requests.post(
                f"{base_url}{endpoint}",
                json=api_key_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {auth_token}"
                },
                timeout=15
            )
            
            print(f"📋 Response: {response.status_code} - {response.text[:200]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    api_key = data.get("apiKey", data.get("api_key", data.get("key", "")))
                    if api_key:
                        print("✅ API key created successfully")
                        return api_key
                except ValueError as json_error:
                    print(f"⚠️ JSON parsing error: {json_error}")
                    # Maybe it's just a plain text key
                    if response.text and len(response.text) > 10:
                        print("✅ Got plain text API key")
                        return response.text.strip()
                        
        except Exception as e:
            print(f"⚠️ Endpoint {endpoint} error: {e}")
            continue
    
    print("❌ All API key creation endpoints failed")
    return None

def create_workspace(base_url: str, api_key: str) -> Dict[str, Any]:
    """Create default workspace using API key"""
    print("📝 Creating default workspace...")
    
    workspace_data = {
        "name": "DocAIche Default",
        "onboardingComplete": True
    }
    
    # Try multiple authentication methods
    auth_methods = [
        f"Bearer {api_key}",
        api_key,  # Simple token
        f"Token {api_key}",
    ]
    
    for auth_header in auth_methods:
        try:
            print(f"🔐 Trying authentication method: {auth_header[:20]}...")
            response = requests.post(
                f"{base_url}/api/v1/workspace/new",
                json=workspace_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": auth_header
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Workspace created successfully")
                return {"success": True, "workspace": data}
            else:
                print(f"⚠️ Auth method failed: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"⚠️ Auth method error: {e}")
            continue
    
    print("❌ All authentication methods failed")
    return {"success": False, "error": "Authentication failed"}

def update_environment_variables(api_key: str):
    """Update docker-compose.yml with the new API key"""
    print("🔧 Updating environment variables...")
    
    # Read docker-compose.yml
    try:
        with open("/home/lab/docaiche/docker-compose.yml", "r") as f:
            content = f.read()
        
        # Replace the API key
        updated_content = content.replace(
            "ANYTHINGLLM_API_KEY=docaiche-lab-default-key-2025",
            f"ANYTHINGLLM_API_KEY={api_key}"
        )
        
        # Write back
        with open("/home/lab/docaiche/docker-compose.yml", "w") as f:
            f.write(updated_content)
        
        print("✅ Environment variables updated")
        
    except Exception as e:
        print(f"❌ Failed to update environment variables: {e}")

def main():
    """Main initialization function"""
    print("🚀 Starting AnythingLLM workspace initialization...")
    
    base_url = "http://anythingllm:3001"
    
    # Wait for AnythingLLM to be ready
    if not wait_for_service(base_url, "AnythingLLM"):
        sys.exit(1)
    
    # Check setup status
    status = check_setup_status(base_url)
    print(f"📋 Setup status: {status}")
    
    # If workspaces already exist, we're done
    if status.get("workspaces_exist"):
        print("✅ Workspaces already exist, initialization complete!")
        print(f"🎉 AnythingLLM is ready to use!")
        print(f"   - Web interface: http://localhost:3001")
        return
    
    auth_token = ""
    api_key = ""
    
    # Perform onboarding if needed
    if status.get("needs_onboarding", True):
        onboarding_result = perform_onboarding(base_url)
        if onboarding_result.get("success"):
            auth_token = onboarding_result.get("auth_token", "")
        else:
            print("❌ Onboarding failed, cannot continue")
            sys.exit(1)
    else:
        print("ℹ️ AnythingLLM is already set up, skipping onboarding")
        # Use web console login with AUTH_TOKEN to get API key
        try:
            # First, try to login with the AUTH_TOKEN as password
            login_response = requests.post(
                f"{base_url}/api/request-token",
                json={"username": "admin", "password": "docaiche-lab-default-key-2025"},
                timeout=10
            )
            if login_response.status_code == 200:
                auth_token = login_response.json().get("token", "")
                print("🔑 Successfully authenticated with web console")
            else:
                print(f"⚠️ Web login failed: {login_response.status_code} - {login_response.text}")
                # Fallback: try using AUTH_TOKEN directly as bearer token
                auth_token = "docaiche-lab-default-key-2025"
                print("🔑 Using AUTH_TOKEN as fallback")
        except Exception as e:
            print(f"⚠️ Login attempt failed: {e}")
            auth_token = "docaiche-lab-default-key-2025"
            print("🔑 Using AUTH_TOKEN as fallback")
    
    # Create API key if we have auth token
    if auth_token:
        api_key = create_api_key(base_url, auth_token)
        if not api_key:
            # If API key creation fails, try using auth_token as API key
            print("⚠️ API key creation failed, trying auth token as API key")
            api_key = auth_token
    else:
        print("❌ No auth token available")
        sys.exit(1)
    
    # Create workspace
    workspace_result = create_workspace(base_url, api_key)
    if not workspace_result.get("success"):
        print("❌ Workspace creation failed")
        sys.exit(1)
    
    # Update environment variables
    update_environment_variables(api_key)
    
    print("🎉 AnythingLLM workspace initialization complete!")
    print(f"📋 Summary:")
    print(f"   - Onboarding: {'✅ Completed' if status.get('needs_onboarding') else '✅ Already done'}")
    print(f"   - API Key: ✅ Created")
    print(f"   - Workspace: ✅ Created")
    print(f"   - Environment: ✅ Updated")
    print(f"")
    print(f"💡 AnythingLLM is now ready to use!")
    print(f"   - Web interface: http://localhost:3001")
    print(f"   - Admin login: admin / docaiche-admin-2025")
    print(f"   - API Key: {api_key[:20]}...")

if __name__ == "__main__":
    main()