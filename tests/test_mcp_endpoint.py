#\!/usr/bin/env python3
"""
Test MCP endpoint end-to-end
"""
import json
import subprocess
import time
import uuid

def test_mcp_search():
    """Test the MCP search endpoint with a proper JSON-RPC request"""
    
    request_id = str(uuid.uuid4())
    
    # MCP JSON-RPC request format
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "docaiche_search",
            "arguments": {
                "query": f"python async await tutorial documentation {int(time.time())}",
                "technology": "python", 
                "limit": 5
            }
        },
        "id": request_id
    }
    
    print(f"Testing MCP endpoint with request ID: {request_id}")
    print(f"Query: {mcp_request['params']['arguments']['query']}")
    
    # Make the request via admin-ui proxy
    cmd = [
        "curl", "-s", "-X", "POST",
        "http://localhost:4080/api/v1/mcp",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(mcp_request)
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    if result.returncode != 0:
        print(f"❌ Request failed: {result.stderr}")
        return False
    
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        print(f"Raw response: {result.stdout}")
        return False
    
    # Check JSON-RPC response format
    if response.get("jsonrpc") != "2.0":
        print(f"❌ Invalid JSON-RPC version: {response.get('jsonrpc')}")
        return False
    
    if response.get("id") != request_id:
        print(f"❌ Request ID mismatch: expected {request_id}, got {response.get('id')}")
        return False
    
    if "error" in response:
        print(f"❌ Error response: {response['error']}")
        return False
    
    if "result" not in response:
        print(f"❌ No result in response")
        return False
    
    # Extract search results from MCP response format
    result_content = response["result"].get("content", [])
    if not result_content:
        print(f"❌ No content in result")
        return False
    
    text_content = None
    for content in result_content:
        if content.get("type") == "text":
            text_content = content.get("text")
            break
    
    if not text_content:
        print(f"❌ No text content in result")
        return False
    
    # Parse text content if it's a string
    if isinstance(text_content, str):
        try:
            text_content = json.loads(text_content)
        except json.JSONDecodeError:
            print(f"❌ Failed to parse text content as JSON")
            return False
    
    # Verify search results structure
    if not isinstance(text_content, dict):
        print(f"❌ Text content is not a dict: {type(text_content)}")
        return False
    
    required_fields = ["query", "results", "total_count", "execution_time_ms"]
    for field in required_fields:
        if field not in text_content:
            print(f"❌ Missing required field: {field}")
            return False
    
    print(f"✅ MCP endpoint test successful\!")
    print(f"   Request ID: {request_id}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Results: {text_content['total_count']}")
    print(f"   Cache hit: {text_content.get('cache_hit', False)}")
    print(f"   External search: {text_content.get('external_search_used', False)}")
    print(f"   Execution time: {text_content['execution_time_ms']}ms")
    
    if text_content['results']:
        print(f"\n   First result:")
        first = text_content['results'][0]
        print(f"   - Title: {first.get('title', 'N/A')}")
        print(f"   - Technology: {first.get('technology', 'N/A')}")
        print(f"   - Source: {first.get('workspace', 'N/A')}")
    
    return True

def check_logs():
    """Check logs for MCP processing"""
    print("\n=== Checking MCP logs ===")
    
    cmd = ["docker-compose", "logs", "api", "--tail", "100"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    log_checks = [
        ("MCP request received", "JSON-RPC request processed"),
        ("SearchTool.execute", "Search tool executed"),
        ("SearchOrchestrator", "Search orchestration ran"),
        ("TextAI", "LLM decision making used"),
        ("external", "External search executed"),
        ("PIPELINE_METRICS", "Pipeline metrics logged")
    ]
    
    for pattern, description in log_checks:
        if pattern in result.stdout:
            print(f"✅ {description}")
        else:
            print(f"❌ {description} not found")

if __name__ == "__main__":
    success = test_mcp_search()
    if success:
        check_logs()
    else:
        print("\n❌ MCP endpoint test failed\!")
