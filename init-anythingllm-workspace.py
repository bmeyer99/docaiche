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
            if response.status_code < 400:
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
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/admin/api-keys",
            json=api_key_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            api_key = data.get("apiKey", "")
            print("✅ API key created successfully")
            return api_key
        else:
            print(f"❌ API key creation failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API key creation error: {e}")
        return None

def create_workspace(base_url: str, api_key: str) -> Dict[str, Any]:
    """Create default workspace using API key"""
    print("📝 Creating default workspace...")
    
    workspace_data = {
        "name": "DocAIche Default",
        "onboardingComplete": True
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/workspace/new",
            json=workspace_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Workspace created successfully")
            return {"success": True, "workspace": data}
        else:
            print(f"❌ Workspace creation failed: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}
            
    except Exception as e:
        print(f"❌ Workspace creation error: {e}")
        return {"success": False, "error": str(e)}

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
    
    base_url = "http://localhost:3001"
    
    # Wait for AnythingLLM to be ready
    if not wait_for_service(base_url, "AnythingLLM"):
        sys.exit(1)
    
    # Check setup status
    status = check_setup_status(base_url)
    print(f"📋 Setup status: {status}")
    
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
        # Try to use existing admin credentials to get a token
        try:
            login_response = requests.post(
                f"{base_url}/api/request-token",
                json={"username": "admin", "password": "docaiche-admin-2025"},
                timeout=10
            )
            if login_response.status_code == 200:
                auth_token = login_response.json().get("token", "")
        except:
            pass
    
    # Create API key
    if auth_token:
        api_key = create_api_key(base_url, auth_token)
        if not api_key:
            print("❌ Failed to create API key")
            sys.exit(1)
    else:
        print("❌ No auth token available, cannot create API key")
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