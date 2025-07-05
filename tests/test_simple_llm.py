#!/usr/bin/env python3
"""
Simple test to verify LLM external search is working
"""
import subprocess
import json
import time

def run_search():
    timestamp = int(time.time())
    query = f"test LLM external search {timestamp}"
    
    cmd = [
        "docker-compose", "exec", "-T", "api",
        "curl", "-s", "-X", "POST",
        "http://localhost:4000/api/v1/search",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"query": query, "limit": 5})
    ]
    
    print(f"Testing with query: {query}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Give logs time to write
    time.sleep(2)
    
    # Check logs for TextAI activity
    log_cmd = ["docker-compose", "logs", "api", "--tail", "200"]
    log_result = subprocess.run(log_cmd, capture_output=True, text=True)
    
    textai_calls = log_result.stdout.count("TextAI.generate_external_query called")
    llm_calls = log_result.stdout.count("LLM external query generation")
    external_decisions = log_result.stdout.count("external search decision: True")
    
    # Count total LLM activity
    total_llm_activity = textai_calls + llm_calls
    
    print(f"TextAI calls found: {textai_calls}")
    print(f"LLM calls found: {llm_calls}")
    print(f"External search decisions: {external_decisions}")
    print(f"Total LLM activity: {total_llm_activity}")
    
    if total_llm_activity > 0:
        print("✅ LLM external search is working!")
        return True
    else:
        print("❌ LLM external search not detected")
        print("Recent log excerpt:")
        print(log_result.stdout[-1000:])
        return False

if __name__ == "__main__":
    run_search()