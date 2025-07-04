"""
Context7 HTTP Provider
=====================

Provider that fetches real-time documentation via Context7 HTTP API.
Uses direct HTTP requests to Context7 endpoints in format:
https://context7.com/vercel/{technology}/llms.txt
"""

import asyncio
import json
import logging
import time
import uuid
import aiohttp
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
    Context7 HTTP provider for real-time documentation retrieval.
    
    This provider uses direct HTTP requests to Context7 API in the format:
    https://context7.com/vercel/{technology}/llms.txt
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize Context7 provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        self.base_url = "https://context7.com"
        self.session = None
        
        # Cache for documentation
        self._doc_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = config.config.get('cache_ttl', 3600)  # 1 hour default
        
        # HTTP client timeout
        self.timeout = aiohttp.ClientTimeout(total=30)
        
        logger.info(f"Initialized Context7Provider with base URL: {self.base_url}")
    
    async def initialize(self) -> None:
        """Initialize HTTP session for Context7 API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'DocAIche-Context7-Provider/1.0'
                    }
                )
            
            logger.info("Context7 HTTP provider initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Context7 HTTP provider: {e}")
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
        correlation_id = f"ctx7_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"PIPELINE_METRICS: step=context7_search_start correlation_id={correlation_id} "
                   f"query=\"{options.query}\" provider=context7")
        
        try:
            # Skip circuit breaker check for now - Context7 is reliable
            # TODO: Implement proper circuit breaker if needed
            
            # Extract technology info from query
            tech_info = self._extract_technology_info(options.query)
            if not tech_info:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(f"PIPELINE_METRICS: step=context7_tech_extraction duration_ms={duration_ms} "
                           f"correlation_id={correlation_id} decision=no_technology_detected success=false")
                return SearchResults(
                    results=[],
                    total_results=0,
                    execution_time_ms=duration_ms,
                    provider="context7",
                    query=options.query,
                    error="No technology name detected in query"
                )
            
            owner = tech_info['owner']
            technology = tech_info['technology']
            
            tech_extraction_time = int((time.time() - start_time) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_tech_extraction duration_ms={tech_extraction_time} "
                       f"correlation_id={correlation_id} technology={technology} owner={owner} success=true")
            
            # Ensure HTTP session is initialized
            if not self.session:
                await self.initialize()
            
            # Fetch documentation content
            content = await self._fetch_documentation(owner, technology, correlation_id)
            if not content:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(f"PIPELINE_METRICS: step=context7_fetch_complete duration_ms={duration_ms} "
                           f"correlation_id={correlation_id} technology={technology} owner={owner} "
                           f"success=false reason=no_content_found")
                return SearchResults(
                    results=[],
                    total_results=0,
                    execution_time_ms=duration_ms,
                    provider="context7",
                    query=options.query,
                    error=f"No documentation found for '{owner}/{technology}'"
                )
            
            # Create search result from documentation content
            results = []
            if content:
                # Split content into chunks for better relevance
                content_chunks = self._split_content(content, options.query)
                
                for i, chunk in enumerate(content_chunks[:5]):  # Limit to top 5 chunks
                    results.append(SearchResult(
                        title=f"{technology.title()} Documentation - Section {i+1}",
                        url=f"https://context7.com/{owner}/{technology}/llms.txt",
                        snippet=chunk[:500],
                        content=chunk,
                        score=self._calculate_relevance(chunk, options.query),
                        source_domain="context7.com",  # Add required field
                        provider_rank=i + 1,  # Add required field (1-based ranking)
                        content_type=SearchResultType.DOCUMENTATION,  # Use enum directly
                        metadata={
                            'owner': owner,
                            'technology': technology,
                            'section': i+1,
                            'total_sections': len(content_chunks),
                            'last_updated': str(datetime.now()),
                            'source': 'context7',
                            'type': SearchResultType.DOCUMENTATION.value,
                            'ttl_seconds': 3600,  # Add TTL metadata for ingestion
                            'ingestion_priority': 'high'  # High priority for fresh docs
                        }
                    ))
            
            search_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"PIPELINE_METRICS: step=context7_search_complete duration_ms={search_time} "
                       f"correlation_id={correlation_id} technology={technology} owner={owner} "
                       f"result_count={len(results)} success=true")
            
            return SearchResults(
                results=results,
                total_results=len(results),
                execution_time_ms=search_time,
                provider="context7",
                query=options.query,
                metadata={
                    'correlation_id': correlation_id,
                    'technology': technology,
                    'owner': owner,
                    'content_length': len(content) if content else 0
                }
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Context7 search failed: {e}")
            logger.info(f"PIPELINE_METRICS: step=context7_search_error duration_ms={duration_ms} "
                       f"correlation_id={correlation_id} error=\"{str(e)}\" success=false")
            
            return SearchResults(
                results=[],
                total_results=0,
                execution_time_ms=duration_ms,
                provider="context7",
                query=options.query,
                error=str(e),
                metadata={'correlation_id': correlation_id}
            )
    
    async def _fetch_documentation(self, owner: str, technology: str, correlation_id: str = None) -> Optional[str]:
        """
        Fetch documentation content from Context7 API.
        
        Args:
            owner: Repository owner (e.g., 'vercel', 'microsoft')
            technology: Technology name (e.g., 'next.js', 'typescript')
            
        Returns:
            Documentation content or None if not found
        """
        fetch_start_time = time.time()
        if correlation_id is None:
            correlation_id = f"ctx7_fetch_{uuid.uuid4().hex[:8]}"
        
        # Check cache first
        cache_key = f"docs_{owner}_{technology}"
        if cache_key in self._doc_cache:
            cached = self._doc_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                cache_hit_time = int((time.time() - fetch_start_time) * 1000)
                logger.debug(f"Returning cached documentation for {owner}/{technology}")
                logger.info(f"PIPELINE_METRICS: step=context7_cache_hit duration_ms={cache_hit_time} "
                           f"correlation_id={correlation_id} technology={technology} owner={owner} "
                           f"content_length={len(cached['content'])}")
                return cached['content']
        
        try:
            url = f"{self.base_url}/{owner}/{technology}/llms.txt"
            logger.info(f"Fetching Context7 documentation from: {url}")
            logger.info(f"PIPELINE_METRICS: step=context7_http_request_start "
                       f"correlation_id={correlation_id} url={url} technology={technology} owner={owner}")
            
            async with self.session.get(url) as response:
                http_duration = int((time.time() - fetch_start_time) * 1000)
                
                if response.status == 200:
                    content = await response.text()
                    
                    # Cache the result
                    self._doc_cache[cache_key] = {
                        'content': content,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"Successfully fetched {len(content)} characters for {owner}/{technology}")
                    logger.info(f"PIPELINE_METRICS: step=context7_http_request_success duration_ms={http_duration} "
                               f"correlation_id={correlation_id} status_code={response.status} "
                               f"content_length={len(content)} technology={technology} owner={owner}")
                    return content
                else:
                    logger.warning(f"Context7 API returned status {response.status} for {owner}/{technology}")
                    logger.info(f"PIPELINE_METRICS: step=context7_http_request_failed duration_ms={http_duration} "
                               f"correlation_id={correlation_id} status_code={response.status} "
                               f"technology={technology} owner={owner} reason=non_200_status")
                    return None
            
        except Exception as e:
            http_duration = int((time.time() - fetch_start_time) * 1000)
            logger.error(f"Failed to fetch documentation for '{owner}/{technology}': {e}")
            logger.info(f"PIPELINE_METRICS: step=context7_http_request_error duration_ms={http_duration} "
                       f"correlation_id={correlation_id} error=\"{str(e)}\" "
                       f"technology={technology} owner={owner}")
            return None
    
    def _split_content(self, content: str, query: str) -> List[str]:
        """
        Split documentation content into relevant chunks.
        
        Args:
            content: Full documentation content
            query: Search query for relevance filtering
            
        Returns:
            List of content chunks
        """
        # Split by common documentation delimiters
        chunks = []
        
        # Split by double newlines (common section delimiter)
        sections = content.split('\n\n')
        
        for section in sections:
            section = section.strip()
            if len(section) > 100:  # Only include substantial sections
                # Further split large sections
                if len(section) > 2000:
                    # Split by single newlines and group
                    lines = section.split('\n')
                    current_chunk = []
                    current_length = 0
                    
                    for line in lines:
                        if current_length + len(line) > 1500:
                            if current_chunk:
                                chunks.append('\n'.join(current_chunk))
                            current_chunk = [line]
                            current_length = len(line)
                        else:
                            current_chunk.append(line)
                            current_length += len(line)
                    
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                else:
                    chunks.append(section)
        
        # Sort chunks by relevance to query
        query_lower = query.lower()
        scored_chunks = []
        
        for chunk in chunks:
            score = self._calculate_relevance(chunk, query)
            scored_chunks.append((score, chunk))
        
        # Sort by score (descending) and return chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks]
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """
        Calculate relevance score for content against query.
        
        Args:
            content: Content to score
            query: Search query
            
        Returns:
            Relevance score between 0 and 1
        """
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Simple relevance calculation
        score = 0.0
        query_words = query_lower.split()
        
        for word in query_words:
            if word in content_lower:
                # Count occurrences
                occurrences = content_lower.count(word)
                score += min(occurrences * 0.1, 0.3)  # Cap contribution per word
        
        # Normalize by query length
        if query_words:
            score = min(score / len(query_words), 1.0)
        
        # Boost score for exact phrase matches
        if query_lower in content_lower:
            score += 0.2
        
        return max(0.1, score)  # Minimum score of 0.1
    
    def _extract_technology_info(self, query: str) -> Optional[Dict[str, str]]:
        """
        Extract technology name and owner from search query.
        
        Args:
            query: Search query
            
        Returns:
            Dict with 'technology' and 'owner' keys, or None
        """
        # Common patterns for technology mentions
        query_lower = query.lower()
        
        # Known technologies with their owners on Context7
        # Format: technology_name -> (owner, normalized_name)
        known_technologies = {
            # Vercel projects
            'next.js': ('vercel', 'next.js'),
            'nextjs': ('vercel', 'next.js'),
            'next': ('vercel', 'next.js'),
            'turbo': ('vercel', 'turbo'),
            'turborepo': ('vercel', 'turbo'),
            'swr': ('vercel', 'swr'),
            
            # Facebook/Meta projects
            'react': ('facebook', 'react'),
            'reactjs': ('facebook', 'react'),
            'react.js': ('facebook', 'react'),
            
            # Microsoft projects
            'typescript': ('microsoft', 'typescript'),
            'ts': ('microsoft', 'typescript'),
            'vscode': ('microsoft', 'vscode'),
            'playwright': ('microsoft', 'playwright'),
            
            # Vue projects
            'vue': ('vuejs', 'vue'),
            'vuejs': ('vuejs', 'vue'),
            'vue.js': ('vuejs', 'vue'),
            'nuxt': ('nuxt', 'nuxt'),
            'nuxtjs': ('nuxt', 'nuxt'),
            'nuxt.js': ('nuxt', 'nuxt'),
            
            # Angular
            'angular': ('angular', 'angular'),
            'angularjs': ('angular', 'angular'),
            
            # Other frameworks
            'svelte': ('sveltejs', 'svelte'),
            'sveltekit': ('sveltejs', 'kit'),
            'express': ('expressjs', 'express'),
            'expressjs': ('expressjs', 'express'),
            'fastify': ('fastify', 'fastify'),
            'nestjs': ('nestjs', 'nest'),
            'nest': ('nestjs', 'nest'),
            'koa': ('koajs', 'koa'),
            'koajs': ('koajs', 'koa'),
            'gatsby': ('gatsbyjs', 'gatsby'),
            'gatsbyjs': ('gatsbyjs', 'gatsby'),
            
            # CSS frameworks
            'tailwind': ('tailwindlabs', 'tailwindcss'),
            'tailwindcss': ('tailwindlabs', 'tailwindcss'),
            'bootstrap': ('twbs', 'bootstrap'),
            'material-ui': ('mui', 'material-ui'),
            'mui': ('mui', 'material-ui'),
            
            # State management
            'redux': ('reduxjs', 'redux'),
            'mobx': ('mobxjs', 'mobx'),
            'zustand': ('pmndrs', 'zustand'),
            
            # Languages and runtimes
            'javascript': ('tc39', 'javascript'),
            'js': ('tc39', 'javascript'),
            'node': ('nodejs', 'node'),
            'nodejs': ('nodejs', 'node'),
            'node.js': ('nodejs', 'node'),
            'deno': ('denoland', 'deno'),
            'bun': ('oven-sh', 'bun'),
            
            # Python frameworks
            'django': ('django', 'django'),
            'flask': ('pallets', 'flask'),
            'fastapi': ('tiangolo', 'fastapi'),
            
            # Testing frameworks
            'jest': ('jestjs', 'jest'),
            'mocha': ('mochajs', 'mocha'),
            'cypress': ('cypress-io', 'cypress'),
            'vitest': ('vitest-dev', 'vitest'),
        }
        
        # Direct matches
        for tech_variant, (owner, tech_name) in known_technologies.items():
            if tech_variant in query_lower:
                return {'owner': owner, 'technology': tech_name}
        
        # Try to extract from patterns like "X documentation" or "how to use X"
        import re
        patterns = [
            r'(\w+(?:\.\w+)?)\s+documentation',
            r'(\w+(?:\.\w+)?)\s+docs',
            r'how\s+to\s+use\s+(\w+(?:\.\w+)?)',
            r'(\w+(?:\.\w+)?)\s+tutorial',
            r'(\w+(?:\.\w+)?)\s+guide',
            r'learn\s+(\w+(?:\.\w+)?)',
            r'(\w+(?:\.\w+)?)\s+api'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                potential_tech = match.group(1)
                if len(potential_tech) > 2:  # Skip very short matches
                    # Check if it's a known technology
                    for tech_variant, (owner, tech_name) in known_technologies.items():
                        if potential_tech == tech_variant or potential_tech in tech_variant:
                            return {'owner': owner, 'technology': tech_name}
        
        return None
    
    
    
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
        health_correlation_id = f"ctx7_health_{uuid.uuid4().hex[:8]}"
        
        try:
            # Ensure session is initialized
            if not self.session:
                await self.initialize()
            
            # Try a simple health check by fetching a known technology
            start_time = time.time()
            test_url = f"{self.base_url}/vercel/next.js/llms.txt"
            
            logger.info(f"PIPELINE_METRICS: step=context7_health_check_start "
                       f"correlation_id={health_correlation_id} test_url={test_url}")
            
            async with self.session.head(test_url) as response:
                latency = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    logger.info(f"PIPELINE_METRICS: step=context7_health_check_success duration_ms={latency} "
                               f"correlation_id={health_correlation_id} status_code={response.status} "
                               f"health_status=healthy")
                    return HealthCheck(
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency
                    )
                elif response.status in [404, 403]:
                    logger.info(f"PIPELINE_METRICS: step=context7_health_check_degraded duration_ms={latency} "
                               f"correlation_id={health_correlation_id} status_code={response.status} "
                               f"health_status=degraded")
                    return HealthCheck(
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        error=f"API returned {response.status}"
                    )
                else:
                    logger.info(f"PIPELINE_METRICS: step=context7_health_check_unhealthy duration_ms={latency} "
                               f"correlation_id={health_correlation_id} status_code={response.status} "
                               f"health_status=unhealthy")
                    return HealthCheck(
                        status=HealthStatus.UNHEALTHY,
                        latency_ms=latency,
                        error=f"Unexpected status {response.status}"
                    )
                
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_health_check_error duration_ms={latency} "
                       f"correlation_id={health_correlation_id} error=\"{str(e)}\" "
                       f"health_status=unhealthy")
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                error=str(e)
            )
    
    async def validate_config(self) -> bool:
        """
        Validate Context7 provider configuration.
        
        Returns:
            True if configuration is valid
        """
        # Context7 HTTP provider doesn't need special configuration
        # Just check that base URL is accessible
        try:
            if not self.session:
                await self.initialize()
            
            # Test connectivity
            health = await self.check_health()
            return health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            
        except Exception as e:
            logger.error(f"Context7 configuration validation failed: {e}")
            return False
    
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
        """Clean up Context7 HTTP session."""
        if self.session:
            try:
                await self.session.close()
                self.session = None
                logger.info("Context7 HTTP session closed")
            except Exception as e:
                logger.error(f"Error closing Context7 HTTP session: {e}")