"""
Context7 MCP Provider
=====================

Provider that fetches real-time documentation via Context7 MCP server.
Uses stdio transport to communicate with the Context7 subprocess.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base import SearchProvider
from ..models import (
    SearchOptions,
    SearchResults,
    SearchResult,
    SearchResultType,
    ProviderCapabilities,
    ProviderType,
    HealthCheck,
    HealthStatus,
    ProviderConfig
)

logger = logging.getLogger(__name__)


class Context7Provider(SearchProvider):
    """
    Context7 MCP provider for real-time documentation retrieval.
    
    This provider uses the Context7 MCP server to fetch up-to-date
    documentation for various libraries and frameworks.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Context7 provider.
        
        Args:
            config: Provider configuration including MCP command
        """
        super().__init__(config)
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.request_id = 0
        self._lock = asyncio.Lock()
        
        # MCP configuration
        self.command = config.config.get('command', 'npx')
        self.args = config.config.get('args', ['-y', '@upstash/context7-mcp'])
        
        # Cache for library IDs
        self._library_cache: Dict[str, str] = {}
        self._cache_ttl = config.config.get('cache_ttl', 3600)  # 1 hour default
        self._last_cache_update = 0
        
        logger.info(f"Initialized Context7Provider with command: {self.command} {' '.join(self.args)}")
    
    async def initialize(self) -> None:
        """Start the Context7 MCP subprocess."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize JSON-RPC communication
            await self._send_request({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {}
                },
                "id": self._get_next_id()
            })
            
            logger.info("Context7 MCP subprocess initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Context7 subprocess: {e}")
            raise
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """
        Search for documentation using Context7.
        
        Args:
            options: Search parameters
            
        Returns:
            Documentation results
        """
        start_time = time.time()
        
        try:
            # Skip circuit breaker check for now - Context7 is reliable
            # TODO: Implement proper circuit breaker if needed
            
            # Extract library name from query
            library_name = self._extract_library_name(options.query)
            if not library_name:
                return SearchResults(
                    results=[],
                    total_results=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    provider="context7",
                    query=options.query,
                    error="No library name detected in query"
                )
            
            # Ensure subprocess is running
            if not self.process or self.process.returncode is not None:
                await self.initialize()
            
            # Get library ID
            library_id = await self._resolve_library_id(library_name)
            if not library_id:
                return SearchResults(
                    results=[],
                    total_results=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    provider="context7",
                    query=options.query,
                    error=f"Library '{library_name}' not found"
                )
            
            # Fetch documentation
            docs = await self._get_library_docs(library_id, options.query)
            
            # Convert to search results
            results = []
            for doc in docs:
                results.append(SearchResult(
                    title=doc.get('title', f"{library_name} Documentation"),
                    url=doc.get('url', ''),
                    snippet=doc.get('content', '')[:500],
                    content=doc.get('content', ''),
                    score=doc.get('relevance', 0.8),
                    metadata={
                        'library': library_name,
                        'library_id': library_id,
                        'version': doc.get('version', 'latest'),
                        'last_updated': doc.get('last_updated', str(datetime.now())),
                        'source': 'context7'
                    }
                ))
            
            search_time = int((time.time() - start_time) * 1000)
            # TODO: Implement metrics tracking if needed
            
            return SearchResults(
                results=results,
                total_results=len(results),
                execution_time_ms=search_time,
                provider="context7",
                query=options.query
            )
            
        except Exception as e:
            logger.error(f"Context7 search failed: {e}")
            # TODO: Implement metrics and circuit breaker if needed
            
            return SearchResults(
                results=[],
                total_results=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                provider="context7",
                query=options.query,
                error=str(e)
            )
    
    async def _resolve_library_id(self, library_name: str) -> Optional[str]:
        """
        Resolve library name to Context7 ID.
        
        Args:
            library_name: Name of the library
            
        Returns:
            Library ID or None if not found
        """
        # Check cache first
        if library_name in self._library_cache:
            return self._library_cache[library_name]
        
        try:
            response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "resolve-library-id",
                    "arguments": {
                        "libraryName": library_name
                    }
                },
                "id": self._get_next_id()
            })
            
            if response and response.get('result'):
                library_id = response['result'].get('libraryId')
                if library_id:
                    self._library_cache[library_name] = library_id
                    return library_id
            
        except Exception as e:
            logger.error(f"Failed to resolve library ID for '{library_name}': {e}")
        
        return None
    
    async def _get_library_docs(self, library_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Fetch documentation for a library.
        
        Args:
            library_id: Context7 library ID
            query: Search query for filtering docs
            
        Returns:
            List of documentation entries
        """
        try:
            response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get-library-docs",
                    "arguments": {
                        "libraryId": library_id,
                        "topic": query  # Use query as topic filter
                    }
                },
                "id": self._get_next_id()
            })
            
            if response and response.get('result'):
                docs = response['result'].get('documentation', [])
                return docs
            
        except Exception as e:
            logger.error(f"Failed to fetch docs for library '{library_id}': {e}")
        
        return []
    
    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send JSON-RPC request to Context7 subprocess.
        
        Args:
            request: JSON-RPC request
            
        Returns:
            JSON-RPC response
        """
        async with self._lock:
            if not self.process or self.process.stdin is None:
                raise RuntimeError("Context7 subprocess not initialized")
            
            # Send request
            request_str = json.dumps(request) + '\n'
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response
            if self.process.stdout:
                response_line = await self.process.stdout.readline()
                if response_line:
                    return json.loads(response_line.decode())
            
            return None
    
    def _extract_library_name(self, query: str) -> Optional[str]:
        """
        Extract library name from search query.
        
        Args:
            query: Search query
            
        Returns:
            Library name or None
        """
        # Common patterns for library mentions
        # This is a simple implementation - could be enhanced with NLP
        query_lower = query.lower()
        
        # Known libraries (extend this list)
        known_libraries = [
            'react', 'vue', 'angular', 'svelte',
            'express', 'fastify', 'nestjs', 'koa',
            'django', 'flask', 'fastapi',
            'numpy', 'pandas', 'scikit-learn', 'tensorflow', 'pytorch',
            'axios', 'lodash', 'moment', 'dayjs',
            'tailwind', 'bootstrap', 'material-ui',
            'redux', 'mobx', 'zustand', 'recoil',
            'next', 'nuxt', 'gatsby',
            'jest', 'mocha', 'cypress', 'playwright'
        ]
        
        for lib in known_libraries:
            if lib in query_lower:
                return lib
        
        # Try to extract from patterns like "X documentation" or "how to use X"
        import re
        patterns = [
            r'(\w+)\s+documentation',
            r'(\w+)\s+docs',
            r'how\s+to\s+use\s+(\w+)',
            r'(\w+)\s+tutorial',
            r'(\w+)\s+guide'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                potential_lib = match.group(1)
                if len(potential_lib) > 2:  # Skip very short matches
                    return potential_lib
        
        return None
    
    def _get_next_id(self) -> int:
        """Get next request ID for JSON-RPC."""
        self.request_id += 1
        return self.request_id
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Context7 provider capabilities."""
        return ProviderCapabilities(
            provider_type=ProviderType.CONTEXT7,
            supports_date_filtering=False,
            supports_site_search=False,
            supports_safe_search=False,
            supports_pagination=False,
            supports_language_filter=False,
            supports_country_filter=False,
            max_results_per_request=20,
            rate_limit_requests_per_minute=100,
            requires_api_key=False,
            supports_batch_queries=False,
            result_types=[SearchResultType.DOCUMENTATION],
            special_features=["real-time-docs", "library-version-tracking"],
            estimated_latency_ms=150,
            reliability_score=0.95
        )
    
    async def check_health(self) -> HealthCheck:
        """Check Context7 provider health."""
        try:
            # Check if subprocess is running
            if not self.process or self.process.returncode is not None:
                return HealthCheck(
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    error="Subprocess not running"
                )
            
            # Try a simple request
            start_time = time.time()
            response = await self._send_request({
                "jsonrpc": "2.0",
                "method": "health",
                "id": self._get_next_id()
            })
            
            latency = int((time.time() - start_time) * 1000)
            
            if response:
                return HealthCheck(
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency
                )
            else:
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    error="No response from subprocess"
                )
                
        except Exception as e:
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                error=str(e)
            )
    
    async def validate_config(self) -> bool:
        """
        Validate Context7 provider configuration.
        
        Returns:
            True if configuration is valid
        """
        # Context7 doesn't need API key validation
        # Just check that command is available
        if not self.command:
            raise ValueError("Context7 command not specified")
        return True
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows request."""
        # Always allow for Context7 - it's reliable
        return True
    
    def _update_metrics(self, success: bool, latency_ms: int = 0) -> None:
        """Update provider metrics."""
        # TODO: Implement metrics tracking if needed
        pass
    
    def _handle_circuit_breaker_failure(self) -> None:
        """Handle circuit breaker failure."""
        # TODO: Implement circuit breaker if needed
        pass
    
    async def cleanup(self) -> None:
        """Clean up Context7 subprocess."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
                logger.info("Context7 subprocess terminated")
            except Exception as e:
                logger.error(f"Error terminating Context7 subprocess: {e}")