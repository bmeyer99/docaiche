#!/usr/bin/env python3
"""
MCP Client Example
==================

This example demonstrates how to use the DocaiChe MCP server from a Python client.
It covers authentication, tool usage, resource access, and error handling.
"""

import asyncio
import os
from typing import Dict, Any, Optional
import httpx
import json
from datetime import datetime


class MCPClient:
    """Simple MCP client for DocaiChe."""
    
    def __init__(self, endpoint: str, client_id: str, client_secret: str):
        self.endpoint = endpoint.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def authenticate(self) -> str:
        """Authenticate and get access token."""
        # Check if we have a valid token
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        # Request new token
        response = await self.session.post(
            f"{self.endpoint}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "resource": "urn:docaiche:api:v1",
                "scope": "search:read ingest:write collections:read feedback:write status:read"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.text}")
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expires = datetime.fromtimestamp(
            datetime.now().timestamp() + token_data["expires_in"] - 60  # Refresh 1 minute early
        )
        
        return self.access_token
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        token = await self.authenticate()
        
        response = await self.session.post(
            f"{self.endpoint}/mcp/tools/call",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": f"tool-{datetime.now().timestamp()}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Tool call failed: {response.text}")
        
        result = response.json()
        if "error" in result:
            raise Exception(f"Tool error: {result['error']}")
        
        return result.get("result", {})
    
    async def read_resource(self, uri: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Read an MCP resource."""
        token = await self.authenticate()
        
        response = await self.session.post(
            f"{self.endpoint}/mcp/resources/read",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": f"resource-{datetime.now().timestamp()}",
                "method": "resources/read",
                "params": {
                    "uri": uri,
                    **(params or {})
                }
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Resource read failed: {response.text}")
        
        result = response.json()
        if "error" in result:
            raise Exception(f"Resource error: {result['error']}")
        
        return result.get("result", {})
    
    async def close(self):
        """Close the client session."""
        await self.session.aclose()


async def main():
    """Example usage of MCP client."""
    
    # Initialize client
    client = MCPClient(
        endpoint=os.getenv("MCP_ENDPOINT", "http://localhost:8000"),
        client_id=os.getenv("MCP_CLIENT_ID", "demo_client"),
        client_secret=os.getenv("MCP_CLIENT_SECRET", "demo_secret")
    )
    
    try:
        print("=== MCP Client Example ===\n")
        
        # 1. Search for documentation
        print("1. Searching for authentication documentation...")
        search_results = await client.call_tool(
            "docaiche/search",
            {
                "query": "authentication OAuth",
                "max_results": 5,
                "include_metadata": True
            }
        )
        
        print(f"Found {search_results['total_count']} results:")
        for i, result in enumerate(search_results['results'], 1):
            print(f"  {i}. {result['title']} (score: {result['score']:.2f})")
            print(f"     {result['snippet'][:100]}...")
            print()
        
        # 2. Get available collections
        print("\n2. Getting available collections...")
        collections = await client.read_resource("docaiche://collections")
        
        print("Available collections:")
        for collection in collections['collections']:
            print(f"  - {collection['display_name']} ({collection['document_count']} docs)")
            print(f"    {collection['description']}")
            print()
        
        # 3. Check system status
        print("\n3. Checking system status...")
        status = await client.read_resource("docaiche://status")
        
        print(f"System Status: {status['status'].upper()}")
        print(f"Version: {status['version']}")
        print(f"Uptime: {status['uptime_seconds'] // 3600} hours")
        print("\nComponent Status:")
        for component, info in status['components'].items():
            print(f"  - {component}: {info['status']}")
        
        # 4. Ingest a document (with consent)
        print("\n4. Ingesting a new document...")
        ingest_result = await client.call_tool(
            "docaiche/ingest",
            {
                "uri": "https://example.com/docs/new-guide",
                "content": """# New API Guide

## Introduction

This guide demonstrates how to use our new API endpoints.

## Authentication

All API requests require authentication using OAuth 2.0.

### Getting Started

1. Register your application
2. Obtain client credentials
3. Request access token
4. Use token in API requests

### Example

```python
import requests

response = requests.post('https://api.example.com/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret'
})
```
""",
                "metadata": {
                    "title": "New API Guide",
                    "author": "Documentation Team",
                    "tags": ["api", "authentication", "oauth"],
                    "collection": "api-docs"
                },
                "consent": {
                    "user_confirmed": True,
                    "purpose": "Adding new API documentation"
                }
            }
        )
        
        print(f"Ingestion Status: {ingest_result['status']}")
        print(f"Document ID: {ingest_result['document_id']}")
        print(f"Indexing Time: {ingest_result['indexing_time_ms']}ms")
        
        # 5. Submit feedback
        print("\n5. Submitting feedback...")
        feedback_result = await client.call_tool(
            "docaiche/feedback",
            {
                "type": "search_relevance",
                "query": "authentication OAuth",
                "rating": 5,
                "comment": "Search results were very relevant and helpful!",
                "metadata": {
                    "user_role": "developer",
                    "use_case": "implementing authentication"
                }
            }
        )
        
        print(f"Feedback ID: {feedback_result['feedback_id']}")
        print(f"Status: {feedback_result['status']}")
        
        # 6. Error handling example
        print("\n6. Testing error handling...")
        try:
            await client.call_tool(
                "docaiche/search",
                {
                    "query": "",  # Invalid: empty query
                    "max_results": 1000  # Invalid: too many results
                }
            )
        except Exception as e:
            print(f"Expected error caught: {e}")
        
        # 7. Streaming example (if WebSocket transport is available)
        print("\n7. Monitoring real-time updates (simulated)...")
        print("Would connect to WebSocket for real-time updates...")
        print("Example: ws://localhost:8000/mcp/ws")
        
    except Exception as e:
        print(f"\nError: {e}")
        
    finally:
        await client.close()
        print("\n=== Example Complete ===")


async def advanced_example():
    """Advanced usage examples."""
    
    client = MCPClient(
        endpoint=os.getenv("MCP_ENDPOINT", "http://localhost:8000"),
        client_id=os.getenv("MCP_CLIENT_ID", "demo_client"),
        client_secret=os.getenv("MCP_CLIENT_SECRET", "demo_secret")
    )
    
    try:
        # Batch operations
        print("=== Advanced Examples ===\n")
        
        # 1. Parallel searches
        print("1. Performing parallel searches...")
        search_tasks = [
            client.call_tool("docaiche/search", {"query": "authentication"}),
            client.call_tool("docaiche/search", {"query": "authorization"}),
            client.call_tool("docaiche/search", {"query": "security"})
        ]
        
        results = await asyncio.gather(*search_tasks)
        for query, result in zip(["authentication", "authorization", "security"], results):
            print(f"  {query}: {result['total_count']} results")
        
        # 2. Collection-specific search
        print("\n2. Searching within specific collection...")
        api_docs = await client.call_tool(
            "docaiche/search",
            {
                "query": "endpoint",
                "collection": "api-docs",
                "max_results": 3
            }
        )
        print(f"  Found {api_docs['total_count']} API documentation results")
        
        # 3. Bulk feedback submission
        print("\n3. Submitting bulk feedback...")
        feedback_tasks = []
        for doc_uri in ["doc1", "doc2", "doc3"]:
            feedback_tasks.append(
                client.call_tool(
                    "docaiche/feedback",
                    {
                        "type": "doc_quality",
                        "target_uri": doc_uri,
                        "rating": 4,
                        "comment": "Good documentation, could use more examples"
                    }
                )
            )
        
        feedback_results = await asyncio.gather(*feedback_tasks)
        print(f"  Submitted {len(feedback_results)} feedback items")
        
    finally:
        await client.close()


def sync_example():
    """Synchronous wrapper for environments that don't support async."""
    
    async def _run():
        await main()
    
    # Run in event loop
    asyncio.run(_run())


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Uncomment to run advanced examples
    # asyncio.run(advanced_example())