#!/usr/bin/env python3
"""
Test Context7 HTTP provider directly
"""

import asyncio
import aiohttp
import sys

async def test_context7():
    """Test Context7 API directly"""
    base_url = "https://context7.com/vercel"
    technology = "next.js"
    url = f"{base_url}/{technology}/llms.txt"
    
    print(f"Testing Context7 API: {url}")
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("Making request...")
            async with session.get(url) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    content = await response.text()
                    print(f"Content length: {len(content)} characters")
                    print("First 500 characters:")
                    print(content[:500])
                    print("\n" + "="*50)
                    print("SUCCESS: Context7 API is working!")
                    return True
                else:
                    print(f"ERROR: Got status {response.status}")
                    error_text = await response.text()
                    print(f"Error content: {error_text[:200]}")
                    return False
                    
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_context7())
    sys.exit(0 if result else 1)