#\!/usr/bin/env python3
"""
Test MCP through Traefik and trace the request
"""
import json
import time
import subprocess
import uuid

def trace_mcp_request():
    request_id = f"traefik-{uuid.uuid4().hex[:8]}"
    timestamp = int(time.time())
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "docaiche_search",
            "arguments": {
                "query": f"kubernetes deployment strategies {timestamp}",
                "technology": "kubernetes",
                "limit": 3
            }
        },
        "id": request_id
    }
    
    print(f"=== MCP Request Trace ===")
    print(f"Request ID: {request_id}")
    print(f"Query: {request['params']['arguments']['query']}")
    print(f"Endpoint: http://localhost:4080/mcp (Traefik)")
    
    # Send request
    cmd = [
        "curl", "-s", "-X", "POST",
        "http://localhost:4080/mcp",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(request)
    ]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start
    
    print(f"\nResponse time: {duration:.2f}s")
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            if "error" in response:
                print(f"❌ Error: {response['error']}")
            else:
                # Extract results
                content = response.get("result", {}).get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        search_results = json.loads(c.get("text", "{}"))
                        print(f"✅ Success\!")
                        print(f"   Total results: {search_results.get('total_count', 0)}")
                        print(f"   Cache hit: {search_results.get('cache_hit', False)}")
                        print(f"   External search: {search_results.get('external_search_used', False)}")
                        print(f"   Execution time: {search_results.get('execution_time_ms', 0)}ms")
                        break
        except Exception as e:
            print(f"❌ Failed to parse response: {e}")
    else:
        print(f"❌ Request failed: {result.stderr}")
    
    # Check logs for trace
    print("\n=== Checking Logs ===")
    time.sleep(1)  # Give logs time to write
    
    log_cmd = ["docker-compose", "logs", "api", "--tail", "200"]
    log_result = subprocess.run(log_cmd, capture_output=True, text=True)
    
    # Look for our request
    log_patterns = [
        (f"kubernetes.*{timestamp}", "Query found in logs"),
        ("MCP request received", "MCP handler activated"),
        ("SearchTool.execute", "Search tool executed"),
        ("TextAI", "LLM integration active"),
        ("external_search_decision", "External search decision made"),
        ("PIPELINE_METRICS", "Pipeline metrics logged"),
        (request_id, "Request ID traced")
    ]
    
    for pattern, desc in log_patterns:
        if pattern in log_result.stdout:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")

if __name__ == "__main__":
    trace_mcp_request()
