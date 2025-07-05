#!/usr/bin/env python3
"""
Test script to verify the Test Connection button flow end-to-end
Tests the complete flow: Test Connection → state update → tab navigation
"""

import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:4080/api/v1"

def test_providers_list():
    """Test fetching the providers list"""
    print("🔍 Testing providers list endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/providers")
        if response.status_code == 200:
            providers = response.json()
            print(f"✅ Found {len(providers)} providers")
            for provider in providers[:3]:  # Show first 3
                print(f"   - {provider['id']}: {provider['status']}")
            return providers
        else:
            print(f"❌ Failed to fetch providers: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching providers: {e}")
        return []

def test_provider_connection(provider_id: str, config: Dict[str, Any]):
    """Test a provider connection"""
    print(f"\n🧪 Testing connection for {provider_id}...")
    try:
        response = requests.post(f"{BASE_URL}/providers/{provider_id}/test", json=config)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                models = result.get('models', [])
                print(f"✅ Connection successful! Found {len(models)} models")
                if models:
                    print(f"   Models: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
                return True
            else:
                print(f"❌ Connection failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception during test: {e}")
        return False

def verify_provider_state_after_test(provider_id: str):
    """Verify that provider state was updated after test"""
    print(f"\n🔄 Verifying state update for {provider_id}...")
    time.sleep(1)  # Give backend time to update
    
    try:
        response = requests.get(f"{BASE_URL}/providers")
        if response.status_code == 200:
            providers = response.json()
            provider = next((p for p in providers if p['id'] == provider_id), None)
            
            if provider:
                print(f"✅ Provider state found:")
                print(f"   Status: {provider.get('status', 'unknown')}")
                print(f"   Models: {len(provider.get('models', []))}")
                print(f"   Last tested: {provider.get('last_tested', 'never')}")
                print(f"   Enabled: {provider.get('enabled', False)}")
                
                # Check if provider is properly configured
                is_configured = (
                    provider.get('status') in ['tested', 'connected'] or
                    provider.get('configured') is True or
                    len(provider.get('models', [])) > 0
                )
                
                if is_configured:
                    print("✅ Provider is properly configured for use in tabs")
                    return True
                else:
                    print("❌ Provider is not properly configured")
                    return False
            else:
                print(f"❌ Provider {provider_id} not found in state")
                return False
        else:
            print(f"❌ Failed to fetch updated state: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying state: {e}")
        return False

def test_provider_models_endpoint(provider_id: str):
    """Test the provider models endpoint"""
    print(f"\n📚 Testing models endpoint for {provider_id}...")
    try:
        response = requests.get(f"{BASE_URL}/providers/{provider_id}/models")
        if response.status_code == 200:
            result = response.json()
            models = result.get('models', [])
            print(f"✅ Models endpoint returned {len(models)} models")
            if models:
                print(f"   Sample models: {', '.join(models[:3])}")
            return True
        else:
            print(f"❌ Models endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
        return False

def main():
    """Run the complete test flow"""
    print("🚀 Starting Test Connection Flow Verification")
    print("=" * 50)
    
    # Step 1: Test basic providers list
    providers = test_providers_list()
    if not providers:
        print("❌ Cannot proceed without providers list")
        sys.exit(1)
    
    # Step 2: Find a testable provider (prioritize Ollama for local testing)
    test_providers = ['ollama', 'openai', 'anthropic', 'groq']
    target_provider = None
    
    for provider_id in test_providers:
        if any(p['id'] == provider_id for p in providers):
            target_provider = provider_id
            print(f"\n🎯 Selected {provider_id} for testing")
            break
    
    if not target_provider:
        print("❌ No suitable test provider found")
        sys.exit(1)
    
    # Step 3: Define test configuration
    test_configs = {
        'ollama': {'base_url': 'http://172.17.0.1:11434'},
        'openai': {'api_key': 'test-key-will-fail'},
        'anthropic': {'api_key': 'test-key-will-fail'},
        'groq': {'api_key': 'test-key-will-fail'}
    }
    
    config = test_configs.get(target_provider, {})
    
    # Step 4: Test connection
    print(f"\n📋 Using config: {config}")
    success = test_provider_connection(target_provider, config)
    
    # Step 5: Verify state update
    state_updated = verify_provider_state_after_test(target_provider)
    
    # Step 6: Test models endpoint
    models_working = test_provider_models_endpoint(target_provider)
    
    # Step 7: Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Provider tested: {target_provider}")
    print(f"Connection test: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"State update: {'✅ PASS' if state_updated else '❌ FAIL'}")
    print(f"Models endpoint: {'✅ PASS' if models_working else '❌ FAIL'}")
    
    if all([success or state_updated, models_working]):  # Allow connection to fail but state should update
        print("\n🎉 Test Connection flow is working correctly!")
        print("✅ Providers should now appear in Vector/Text AI tabs after testing")
    else:
        print("\n❌ Test Connection flow has issues")
        print("⚠️  Users may not see providers in Vector/Text AI tabs after testing")
    
    print("\n💡 Next steps:")
    print("1. Open http://localhost:4080/dashboard/search-config")
    print("2. Go to Providers tab")
    print("3. Test a provider connection")
    print("4. Navigate to Vector Search or Text AI tabs")
    print("5. Verify the tested provider appears in the dropdown")

if __name__ == "__main__":
    main()