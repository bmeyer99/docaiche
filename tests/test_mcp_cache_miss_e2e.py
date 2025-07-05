#!/usr/bin/env python3
"""
MCP E2E Test - Cache Miss Query
================================

Tests the search flow end-to-end through the :4080/mcp endpoint for a cache miss query.
This will trigger the full search flow including potential Context7 external search.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_mcp_request(url: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send JSON-RPC 2.0 request to MCP endpoint.
    
    Args:
        url: MCP endpoint URL
        request_data: JSON-RPC request payload
        
    Returns:
        JSON-RPC response
    """
    start_time = time.time()
    
    logger.info(f"Sending MCP request to {url}")
    logger.info(f"Request payload: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60.0
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response time: {duration_ms}ms")
        
        response_data = response.json()
        logger.info(f"Response payload: {json.dumps(response_data, indent=2)}")
        
        return {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {
            "status_code": 0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "error": str(e)
        }


def test_cache_miss_search():
    """
    Test MCP search with a unique query that will result in a cache miss.
    """
    # Generate a unique query to ensure cache miss
    unique_id = uuid.uuid4().hex[:8]
    # Use a simpler query that might match existing content
    test_query = f"React hooks useState useEffect test_{unique_id}"
    
    # Create JSON-RPC 2.0 request for docaiche_search tool
    request_data = {
        "jsonrpc": "2.0",
        "id": f"test_{unique_id}",
        "method": "tools/call",
        "params": {
            "name": "docaiche_search",
            "arguments": {
                "query": test_query,
                "technology": "react",
                "limit": 10
                # Note: workspace and use_external_search are not part of the search tool schema
            }
        }
    }
    
    # MCP endpoint URL
    mcp_url = "http://localhost:4080/mcp"
    
    logger.info("=" * 80)
    logger.info("MCP E2E Test - Cache Miss Query")
    logger.info("=" * 80)
    logger.info(f"Test ID: {unique_id}")
    logger.info(f"Test Query: {test_query}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    # Send the request
    result = send_mcp_request(mcp_url, request_data)
    
    # Analyze the response
    logger.info("\n" + "=" * 80)
    logger.info("Test Results Summary")
    logger.info("=" * 80)
    
    if result["status_code"] == 200:
        response_data = result["data"]
        
        # Check if it's an error response
        if "error" in response_data:
            logger.error(f"JSON-RPC Error: {response_data['error']}")
            return
        
        # Extract result data
        if "result" in response_data and "content" in response_data["result"]:
            content = response_data["result"]["content"]
            if content and len(content) > 0 and "text" in content[0]:
                try:
                    # Parse the JSON response from the tool
                    search_results = json.loads(content[0]["text"])
                    
                    logger.info(f"✓ Request successful")
                    logger.info(f"✓ Response time: {result['duration_ms']}ms")
                    logger.info(f"✓ Cache hit: {search_results.get('cache_hit', False)}")
                    logger.info(f"✓ Results returned: {search_results.get('returned_count', 0)}")
                    logger.info(f"✓ Total results: {search_results.get('total_count', 0)}")
                    logger.info(f"✓ Execution time: {search_results.get('execution_time_ms', 0)}ms")
                    
                    # Check if external search was triggered
                    results = search_results.get('results', [])
                    external_triggered = any(
                        'external' in str(r.get('workspace', '')).lower() or
                        'context7' in str(r.get('source_url', '')).lower()
                        for r in results
                    )
                    
                    logger.info(f"✓ External search triggered: {external_triggered}")
                    
                    # Log first few results
                    logger.info("\nTop Results:")
                    for i, result in enumerate(results[:3]):
                        logger.info(f"\n{i+1}. {result.get('title', 'No title')}")
                        logger.info(f"   Source: {result.get('source_url', 'No URL')}")
                        logger.info(f"   Score: {result.get('relevance_score', 0)}")
                        logger.info(f"   Workspace: {result.get('workspace', 'Unknown')}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse search results: {e}")
                    logger.error(f"Raw content: {content[0]['text']}")
        else:
            logger.error("Unexpected response format")
            logger.error(f"Response: {response_data}")
    else:
        logger.error(f"✗ Request failed with status {result['status_code']}")
        if "error" in result:
            logger.error(f"✗ Error: {result['error']}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Test Complete")
    logger.info("=" * 80)


def test_basic_search():
    """
    Test basic MCP search without unique ID to see if any results exist.
    """
    # Simple query without unique ID
    test_query = "React hooks useState"
    
    # Create JSON-RPC 2.0 request for docaiche_search tool
    request_data = {
        "jsonrpc": "2.0",
        "id": "test_basic",
        "method": "tools/call",
        "params": {
            "name": "docaiche_search",
            "arguments": {
                "query": test_query,
                "technology": "react",
                "limit": 5
            }
        }
    }
    
    # MCP endpoint URL
    mcp_url = "http://localhost:4080/mcp"
    
    logger.info("\n" + "=" * 80)
    logger.info("MCP E2E Test - Basic Search")
    logger.info("=" * 80)
    logger.info(f"Test Query: {test_query}")
    logger.info("=" * 80)
    
    # Send the request
    result = send_mcp_request(mcp_url, request_data)
    
    # Log basic result
    if result["status_code"] == 200:
        response_data = result["data"]
        if "result" in response_data and "content" in response_data["result"]:
            content = response_data["result"]["content"]
            if content and len(content) > 0 and "text" in content[0]:
                try:
                    search_results = json.loads(content[0]["text"])
                    logger.info(f"✓ Basic search returned {search_results.get('returned_count', 0)} results")
                except:
                    pass


def main():
    """Main entry point."""
    try:
        # Run basic search first
        test_basic_search()
        
        # Run cache miss test
        test_cache_miss_search()
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)


if __name__ == "__main__":
    main()