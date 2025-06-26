#!/usr/bin/env python3
"""
Simple script to recreate API calls from HAR file
Made immutable with "chattr +i bulk_endpoint_test.py"
Make mutable with "sudo chattr -i bulk_endpoint_test.py"
"""

import requests
import json
import sys

def main():
    print("🚀 Starting API Recreation Script")
    print(f"Python version: {sys.version}")
    
    base_url = "http://web_ui:8080"
    print(f"Base URL: {base_url}")
    
    # Test basic connectivity first
    print("\n1. Testing basic connectivity...")
    try:
        response = requests.get(f"{base_url}/config", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.text)} chars")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to {base_url}")
        print("   💡 Make sure the server is running and accessible")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test health endpoint
    print("\n2. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test config endpoint
    print("\n3. Testing config endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/config", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            config_keys = list(data.get('config', {}).keys()) if 'config' in data else list(data.keys())
            print(f"   Found {len(config_keys)} config items")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test LLM connection (from your HAR file)
    print("\n4. Testing LLM connection...")
    try:
        payload = {
            "provider": "ollama",
            "base_url": "http://192.168.4.204:11434/api",
            "api_key": None
        }
        
        response = requests.post(
            f"{base_url}/api/v1/llm/test-connection",
            json=payload,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   ✅ Connection successful!")
                print(f"   Found {data.get('model_count', 0)} models")
            else:
                print(f"   ❌ Connection failed: {data.get('message')}")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test bulk config endpoint (this failed in your HAR)
    print("\n5. Testing bulk config endpoint...")
    try:
        # Minimal payload for testing
        test_payload = [
            {"key": "test.key", "value": "test_value"}
        ]
        
        response = requests.post(
            f"{base_url}/api/v1/config/bulk",
            json=test_payload,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 404:
            print("   ❌ Endpoint not found (404)")
            print("   💡 The bulk config endpoint doesn't exist")
        elif response.status_code == 200:
            print("   ✅ Endpoint exists and responded successfully")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
        # Test configuration persistence after bulk update
    print("\n6. Testing configuration persistence...")
    try:
        import time
        # Give the system a moment to process the bulk update
        time.sleep(1)
        
        # Retrieve config again to see if our test value was persisted
        response = requests.get(f"{base_url}/api/v1/config", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            config_data = data.get('config', data)
            
            # Check if our test key was persisted
            test_value = config_data.get('test.key') or config_data.get('test', {}).get('key')
            
            if test_value == "test_value":
                print("   ✅ Configuration persistence working!")
                print(f"   Found persisted value: {test_value}")
            elif test_value:
                print(f"   ⚠️  Found different value than expected: {test_value}")
                print("   (Configuration may be working but with data transformation)")
            else:
                print("   ❌ Configuration not persisted")
                print("   💡 The bulk config update may not be saving to database")
                
                # Show a sample of current config for debugging
                sample_keys = list(config_data.keys())[:5]
                print(f"   Current config keys (sample): {sample_keys}")
        else:
            print(f"   ❌ Failed to retrieve config: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error checking persistence: {e}")
    
    print("\n✅ Script completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Script interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()