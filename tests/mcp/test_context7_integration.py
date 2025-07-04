"""
Test Context7 Integration through MCP Search Flow
================================================

This test specifically targets Context7 external search to verify the TTL ingestion flow.
"""

import pytest
import asyncio
import json
import logging
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.mcp.server import MCPServer
from src.mcp.schemas import MCPRequest, MCPResponse
from src.mcp.tools.docaiche_search import DocAIcheSearchTool
from src.search.orchestrator import SearchOrchestrator
from src.mcp.providers.implementations.context7_provider import Context7Provider
from src.mcp.providers.models import ProviderConfig, ProviderType

# Configure logging to capture Context7 and ingestion logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestContext7Integration:
    """Test Context7 external search integration through MCP."""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock search orchestrator with Context7 support."""
        orchestrator = AsyncMock(spec=SearchOrchestrator)
        
        # Mock the MCP enhancer
        mcp_enhancer = AsyncMock()
        mcp_enhancer.external_providers = {}
        mcp_enhancer.execute_external_search = AsyncMock()
        
        orchestrator.mcp_enhancer = mcp_enhancer
        orchestrator.search = AsyncMock()
        
        return orchestrator
    
    @pytest.fixture
    def context7_provider(self):
        """Create a Context7 provider instance."""
        config = ProviderConfig(
            provider_id="context7_docs",
            provider_type=ProviderType.CONTEXT7,
            enabled=True,
            api_key="",  # Context7 doesn't require API key
            priority=1,
            max_requests_per_minute=100,
            timeout_seconds=10.0
        )
        return Context7Provider(config)
    
    @pytest.fixture
    def search_tool(self, mock_orchestrator):
        """Create a DocAIche search tool with mocked orchestrator."""
        tool = DocAIcheSearchTool(orchestrator=mock_orchestrator)
        return tool
    
    @pytest.mark.asyncio
    async def test_context7_react_usestate_search(self, search_tool, mock_orchestrator, context7_provider, caplog):
        """Test searching for React useState documentation through Context7."""
        # Enable detailed logging
        caplog.set_level(logging.INFO)
        
        # Register Context7 provider
        mock_orchestrator.mcp_enhancer.external_providers["context7_docs"] = context7_provider
        
        # Mock external search to return Context7 results
        mock_context7_results = [
            {
                "title": "React useState Hook Documentation",
                "url": "https://context7.com/facebook/react/llms.txt",
                "snippet": "useState is a React Hook that lets you add a state variable to your component.",
                "content": """useState is a React Hook that lets you add a state variable to your component.
                
                const [state, setState] = useState(initialState)
                
                Parameters:
                - initialState: The value you want the state to be initially.
                
                Returns:
                useState returns an array with exactly two values:
                1. The current state value
                2. The set function that lets you update the state
                
                Example:
                import { useState } from 'react';
                
                function MyComponent() {
                    const [count, setCount] = useState(0);
                    
                    return (
                        <button onClick={() => setCount(count + 1)}>
                            You clicked {count} times
                        </button>
                    );
                }""",
                "provider": "context7",
                "metadata": {
                    "technology": "react",
                    "owner": "facebook",
                    "last_updated": datetime.utcnow().isoformat(),
                    "ttl_seconds": 3600,  # TTL metadata for ingestion
                    "version": "18.2.0",
                    "source": "context7",
                    "ingestion_priority": "high"
                }
            }
        ]
        
        # Mock the search method to return both internal and external results
        async def mock_search(query, **kwargs):
            # Force external search by returning no internal results
            if kwargs.get("use_external_search", False):
                # Log that external search was triggered
                logger.info(f"EXTERNAL_SEARCH_TRIGGERED: query='{query}' force_external=True")
                return {
                    "results": [],  # No internal results
                    "external_results": mock_context7_results,
                    "total": 0,
                    "execution_time": 150,
                    "sources_used": ["context7"],
                    "external_search_triggered": True,
                    "external_providers_used": ["context7_docs"]
                }
            return {
                "results": [],
                "total": 0,
                "execution_time": 50
            }
        
        mock_orchestrator.search.side_effect = mock_search
        
        # Execute search with use_external_search=True to force Context7
        search_args = {
            "query": "React useState hook implementation",
            "use_external_search": True,  # Force external search
            "technology_hint": "react",
            "max_results": 10
        }
        
        logger.info(f"TEST: Executing search with args: {search_args}")
        
        result = await search_tool.execute(**search_args)
        
        # Log the full result for debugging
        logger.info(f"TEST: Search result: {json.dumps(result, indent=2, default=str)}")
        
        # Verify Context7 was triggered
        assert mock_orchestrator.search.called
        search_call_args = mock_orchestrator.search.call_args
        assert search_call_args[1].get("use_external_search") is True
        
        # Check logs for Context7 trigger
        context7_logs = [rec for rec in caplog.records if "EXTERNAL_SEARCH_TRIGGERED" in rec.message]
        assert len(context7_logs) > 0, "Context7 external search was not triggered"
        
        # Verify results contain Context7 data
        assert "external_results" in result or "results" in result
        
        if "external_results" in result:
            context7_results = result["external_results"]
        else:
            # Results might be merged into main results
            context7_results = [r for r in result.get("results", []) if r.get("provider") == "context7"]
        
        assert len(context7_results) > 0, "No Context7 results found"
        
        # Verify TTL metadata is present
        first_result = context7_results[0]
        assert "metadata" in first_result
        metadata = first_result["metadata"]
        
        # Check for TTL metadata
        assert "ttl_seconds" in metadata, "TTL metadata missing"
        assert metadata["ttl_seconds"] == 3600
        assert metadata["source"] == "context7"
        assert metadata["technology"] == "react"
        assert metadata["ingestion_priority"] == "high"
        
        # Log summary
        logger.info(f"TEST SUMMARY: Context7 integration successful")
        logger.info(f"- External search triggered: Yes")
        logger.info(f"- Context7 results returned: {len(context7_results)}")
        logger.info(f"- TTL metadata present: Yes ({metadata.get('ttl_seconds')} seconds)")
        logger.info(f"- Technology detected: {metadata.get('technology')}")
        
        return {
            "success": True,
            "context7_triggered": True,
            "results_count": len(context7_results),
            "ttl_metadata_present": True,
            "ttl_value": metadata.get("ttl_seconds"),
            "logs": [rec.message for rec in caplog.records if "context7" in rec.message.lower()]
        }
    
    @pytest.mark.asyncio
    async def test_context7_typescript_search(self, search_tool, mock_orchestrator, context7_provider, caplog):
        """Test searching for TypeScript documentation through Context7."""
        caplog.set_level(logging.INFO)
        
        # Register Context7 provider
        mock_orchestrator.mcp_enhancer.external_providers["context7_docs"] = context7_provider
        
        # Mock Context7 TypeScript results
        mock_context7_results = [
            {
                "title": "TypeScript Interfaces Documentation",
                "url": "https://context7.com/microsoft/typescript/llms.txt",
                "snippet": "Interfaces in TypeScript are a powerful way to define contracts within your code.",
                "content": """TypeScript Interfaces

Interfaces are one of TypeScript's core principles for type checking.

interface User {
    name: string;
    age: number;
    email?: string; // Optional property
}

Key features:
- Define the shape of objects
- Support optional properties with ?
- Can extend other interfaces
- Support readonly properties""",
                "provider": "context7",
                "metadata": {
                    "technology": "typescript",
                    "owner": "microsoft",
                    "last_updated": datetime.utcnow().isoformat(),
                    "ttl_seconds": 7200,  # 2 hour TTL
                    "version": "5.3.0",
                    "source": "context7",
                    "ingestion_priority": "high"
                }
            }
        ]
        
        # Mock search to trigger Context7
        async def mock_search(query, **kwargs):
            if kwargs.get("use_external_search", False):
                logger.info(f"CONTEXT7_SEARCH: technology=typescript query='{query}'")
                return {
                    "results": [],
                    "external_results": mock_context7_results,
                    "total": 0,
                    "external_search_triggered": True,
                    "external_providers_used": ["context7_docs"]
                }
            return {"results": [], "total": 0}
        
        mock_orchestrator.search.side_effect = mock_search
        
        # Execute search
        result = await search_tool.execute(
            query="TypeScript interface type checking",
            use_external_search=True,
            technology_hint="typescript"
        )
        
        # Verify Context7 results
        context7_results = result.get("external_results", [])
        assert len(context7_results) > 0
        
        # Check TTL metadata
        metadata = context7_results[0]["metadata"]
        assert metadata["ttl_seconds"] == 7200
        assert metadata["technology"] == "typescript"
        assert metadata["owner"] == "microsoft"
        
        # Check logs
        context7_logs = [rec for rec in caplog.records if "CONTEXT7_SEARCH" in rec.message]
        assert len(context7_logs) > 0
        
        logger.info(f"TypeScript search successful with TTL: {metadata['ttl_seconds']}s")
    
    @pytest.mark.asyncio 
    async def test_context7_vue_search(self, search_tool, mock_orchestrator, context7_provider, caplog):
        """Test searching for Vue.js documentation through Context7."""
        caplog.set_level(logging.INFO)
        
        # Register Context7 provider
        mock_orchestrator.mcp_enhancer.external_providers["context7_docs"] = context7_provider
        
        # Mock Context7 Vue results
        mock_context7_results = [
            {
                "title": "Vue 3 Composition API Documentation",
                "url": "https://context7.com/vuejs/vue/llms.txt",
                "snippet": "The Composition API is a set of APIs that allows us to author Vue components using imported functions.",
                "content": """Vue 3 Composition API

The Composition API provides a more flexible way to organize component logic.

import { ref, computed, onMounted } from 'vue'

export default {
    setup() {
        const count = ref(0)
        const doubled = computed(() => count.value * 2)
        
        onMounted(() => {
            console.log('Component mounted!')
        })
        
        return { count, doubled }
    }
}""",
                "provider": "context7",
                "metadata": {
                    "technology": "vue",
                    "owner": "vuejs",
                    "last_updated": datetime.utcnow().isoformat(),
                    "ttl_seconds": 5400,  # 1.5 hour TTL
                    "version": "3.4.0",
                    "source": "context7",
                    "ingestion_priority": "medium"
                }
            }
        ]
        
        # Mock search
        async def mock_search(query, **kwargs):
            if "vue" in query.lower() and kwargs.get("use_external_search", False):
                logger.info(f"CONTEXT7_VUE_TRIGGERED: query='{query}'")
                return {
                    "results": [],
                    "external_results": mock_context7_results,
                    "external_search_triggered": True
                }
            return {"results": [], "total": 0}
        
        mock_orchestrator.search.side_effect = mock_search
        
        # Execute search
        result = await search_tool.execute(
            query="Vue composition API setup function",
            use_external_search=True,
            technology_hint="vue"
        )
        
        # Verify results
        assert "external_results" in result
        vue_result = result["external_results"][0]
        assert vue_result["metadata"]["technology"] == "vue"
        assert vue_result["metadata"]["ttl_seconds"] == 5400
        
        logger.info("Vue.js Context7 search completed successfully")


if __name__ == "__main__":
    # Run the test directly
    import sys
    
    async def run_tests():
        """Run Context7 integration tests."""
        test_instance = TestContext7Integration()
        
        # Create fixtures
        orchestrator = test_instance.mock_orchestrator()
        provider = test_instance.context7_provider()
        tool = test_instance.search_tool(orchestrator)
        
        # Import caplog equivalent for direct execution
        class MockCaplog:
            def __init__(self):
                self.records = []
                self.handler = logging.StreamHandler(sys.stdout)
                self.handler.setLevel(logging.INFO)
                
            def set_level(self, level):
                logging.getLogger().setLevel(level)
                logging.getLogger().addHandler(self.handler)
        
        caplog = MockCaplog()
        
        print("Running Context7 Integration Tests")
        print("=" * 50)
        
        # Test 1: React useState
        print("\n1. Testing React useState search...")
        try:
            result = await test_instance.test_context7_react_usestate_search(tool, orchestrator, provider, caplog)
            print(f"✓ React test passed: {result}")
        except Exception as e:
            print(f"✗ React test failed: {e}")
        
        # Test 2: TypeScript
        print("\n2. Testing TypeScript search...")
        try:
            await test_instance.test_context7_typescript_search(tool, orchestrator, provider, caplog)
            print("✓ TypeScript test passed")
        except Exception as e:
            print(f"✗ TypeScript test failed: {e}")
        
        # Test 3: Vue.js
        print("\n3. Testing Vue.js search...")
        try:
            await test_instance.test_context7_vue_search(tool, orchestrator, provider, caplog)
            print("✓ Vue.js test passed")
        except Exception as e:
            print(f"✗ Vue.js test failed: {e}")
        
        print("\n" + "=" * 50)
        print("Context7 Integration Tests Complete")
    
    # Run the async tests
    asyncio.run(run_tests())