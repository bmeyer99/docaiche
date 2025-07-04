#!/usr/bin/env python3
"""
Test script for the prompt enhancement API endpoint.
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE_URL = "http://localhost:4080/api/v1/admin/search/text-ai"

async def test_prompt_enhancement():
    """Test the prompt enhancement endpoint."""
    async with httpx.AsyncClient() as client:
        # Test enhancing different prompt types
        prompt_types = [
            "query_understanding",
            "result_relevance",
            "external_search_decision"
        ]
        
        for prompt_type in prompt_types:
            print(f"\n{'='*60}")
            print(f"Testing enhancement for: {prompt_type}")
            print(f"{'='*60}")
            
            try:
                # First, get the current prompt
                response = await client.get(f"{API_BASE_URL}/prompts/{prompt_type}")
                if response.status_code == 200:
                    current_prompt = response.json()
                    print(f"\nCurrent version: {current_prompt['version']}")
                    print(f"Current template (first 200 chars):")
                    print(current_prompt['template'][:200] + "...")
                
                # Now enhance it
                print(f"\nEnhancing prompt...")
                response = await client.post(f"{API_BASE_URL}/prompts/{prompt_type}/enhance")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"\nEnhancement successful!")
                    print(f"New version: {result['data']['new_version']}")
                    print(f"Improvements: {json.dumps(result['data']['improvements'], indent=2)}")
                    print(f"\nEnhanced prompt (first 300 chars):")
                    print(result['data']['enhanced_prompt'][:300] + "...")
                elif response.status_code == 503:
                    print(f"\nTextAI provider not configured: {response.json()['detail']}")
                else:
                    print(f"\nError {response.status_code}: {response.json()['detail']}")
                    
            except Exception as e:
                print(f"\nError testing {prompt_type}: {str(e)}")

async def test_deprecated_endpoint():
    """Test that the old endpoint is properly deprecated."""
    async with httpx.AsyncClient() as client:
        print(f"\n{'='*60}")
        print("Testing deprecated endpoint")
        print(f"{'='*60}")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/prompts/test_id/enhance",
                json={
                    "prompt_id": "test_id",
                    "optimization_goal": "clarity"
                }
            )
            
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.json()}")
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("Testing Prompt Enhancement API")
    print(f"Timestamp: {datetime.now()}")
    
    # Run tests
    asyncio.run(test_prompt_enhancement())
    asyncio.run(test_deprecated_endpoint())
    
    print("\n\nTests completed!")