"""
Enhanced Search Orchestrator with LLM-powered intelligence
Implements the full intelligent documentation search and caching pipeline
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from src.search.orchestrator import SearchOrchestrator
from src.api.schemas import SearchResponse
from src.search.llm_query_analyzer import LLMQueryAnalyzer, QueryIntent
from src.enrichment.llm_source_finder import LLMSourceFinder, DocumentationSource
from src.clients.github_enhanced import SmartGitHubClient
from src.clients.smart_scraper import SmartWebScraper
from src.ingestion.smart_pipeline import SmartIngestionPipeline
from src.llm.client import LLMProviderClient
from src.clients.anythingllm import AnythingLLMClient
from src.database.manager import DatabaseManager
from src.cache.manager import CacheManager
from src.document_processing.models import DocumentContent

logger = logging.getLogger(__name__)


class EnhancedSearchOrchestrator(SearchOrchestrator):
    """Enhanced orchestrator with intelligent documentation discovery and processing"""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager,
        anythingllm_client: AnythingLLMClient,
        llm_client: LLMProviderClient,
        **kwargs
    ):
        super().__init__(
            db_manager=db_manager,
            cache_manager=cache_manager,
            anythingllm_client=anythingllm_client,
            **kwargs
        )
        
        # Initialize LLM-powered components
        self.llm_client = llm_client
        self.query_analyzer = LLMQueryAnalyzer(llm_client)
        self.source_finder = LLMSourceFinder(llm_client)
        self.github_client = SmartGitHubClient(llm_client)
        self.web_scraper = SmartWebScraper(llm_client)
        self.pipeline = SmartIngestionPipeline(
            llm_client=llm_client,
            anythingllm_client=anythingllm_client,
            db_manager=db_manager
        )
        
    async def search(self, query: str, limit: int = 10) -> SearchResponse:
        """
        Perform intelligent search with dynamic documentation discovery
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            SearchResponse with results
        """
        start_time = time.time()
        
        try:
            # 1. Check cache first
            cached_response = await self._check_cache(query)
            if cached_response:
                logger.info(f"Cache hit for query: {query}")
                return cached_response
            
            logger.info(f"Cache miss for query: {query}")
            
            # 2. Analyze query intent using LLM
            logger.info("Analyzing query intent...")
            intent = await self.query_analyzer.analyze_query(query)
            logger.info(f"Query intent: technology={intent.technology}, "
                       f"topics={intent.topics}, doc_type={intent.doc_type}")
            
            # 3. Check if we already have content for this technology
            existing_content = await self._check_existing_content(intent)
            
            if existing_content:
                # Search existing content in AnythingLLM
                logger.info(f"Found existing content for {intent.technology}")
                results = await self._search_existing_content(query, intent)
            else:
                # 4. Find documentation sources dynamically
                logger.info("Discovering documentation sources...")
                sources = await self.source_finder.find_sources(intent)
                logger.info(f"Found {len(sources)} potential sources")
                
                # 5. Fetch documentation from top sources
                all_content = []
                for source in sources[:3]:  # Limit to top 3 sources
                    logger.info(f"Fetching from {source.name} ({source.url})")
                    
                    if source.source_type == "github":
                        try:
                            contents = await self.github_client.fetch_docs_intelligently(
                                source.url, intent
                            )
                            all_content.extend(contents)
                            logger.info(f"Fetched {len(contents)} documents from {source.name}")
                        except Exception as e:
                            logger.error(f"Failed to fetch from {source.name}: {e}")
                            continue
                    else:
                        # Use web scraper for other sources
                        logger.info(f"Fetching from web source: {source.name} ({source.url})")
                        try:
                            contents = await self.web_scraper.fetch_docs_intelligently(
                                source.url, intent
                            )
                            all_content.extend(contents)
                            logger.info(f"Fetched {len(contents)} documents from {source.name}")
                        except Exception as e:
                            logger.error(f"Failed to fetch from {source.name}: {e}")
                            continue
                
                # 6. Process and store documentation
                if all_content:
                    logger.info(f"Processing {len(all_content)} documents...")
                    
                    for content in all_content:
                        try:
                            result = await self.pipeline.process_documentation(
                                content, intent
                            )
                            if result.success:
                                logger.info(f"Successfully processed {result.chunks_processed} "
                                          f"chunks to workspace {result.workspace_slug}")
                            else:
                                logger.error(f"Failed to process document: {result.error_message}")
                        except Exception as e:
                            logger.error(f"Processing error: {e}")
                            continue
                
                # 7. Search in AnythingLLM after processing
                results = await self._search_anythingllm(query, intent)
            
            # 8. Format and cache results
            response = self._format_response(results, query, intent, time.time() - start_time)
            await self._cache_results(query, response)
            
            # 9. Track search in database
            await self._track_search(query, intent, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            # Fall back to basic search
            return await super().search(query, limit)
    
    async def _check_existing_content(self, intent: QueryIntent) -> bool:
        """
        Check if we already have content for this technology
        
        Args:
            intent: Query intent
            
        Returns:
            True if content exists
        """
        try:
            query = """
            SELECT COUNT(*) as count
            FROM content_metadata
            WHERE technology = :technology
            """
            
            result = await self.db_manager.fetch_one(
                query, {"technology": intent.technology}
            )
            
            return result and result.get("count", 0) > 0
            
        except Exception as e:
            logger.error(f"Failed to check existing content: {e}")
            return False
    
    async def _search_existing_content(
        self, 
        query: str, 
        intent: QueryIntent
    ) -> List[Dict[str, Any]]:
        """
        Search existing content in AnythingLLM
        
        Args:
            query: Search query
            intent: Query intent
            
        Returns:
            List of search results
        """
        try:
            # Get workspace for this technology
            workspace_slug = f"{intent.technology}-docs"
            
            # Enhance query for better results
            enhanced_query = await self.query_analyzer.enhance_query(query, intent)
            
            # Search in AnythingLLM
            results = await self.anythingllm_client.search(
                workspace_slug=workspace_slug,
                query=enhanced_query,
                limit=10
            )
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"Failed to search existing content: {e}")
            return []
    
    async def _search_anythingllm(
        self, 
        query: str, 
        intent: QueryIntent
    ) -> List[Dict[str, Any]]:
        """
        Search in AnythingLLM workspace
        
        Args:
            query: Search query
            intent: Query intent
            
        Returns:
            List of search results
        """
        try:
            workspace_slug = f"{intent.technology}-docs"
            
            # Use enhanced query
            enhanced_query = await self.query_analyzer.enhance_query(query, intent)
            
            results = await self.anythingllm_client.search(
                workspace_slug=workspace_slug,
                query=enhanced_query,
                limit=10
            )
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"AnythingLLM search failed: {e}")
            return []
    
    def _format_response(
        self, 
        results: List[Dict[str, Any]], 
        query: str, 
        intent: QueryIntent,
        search_time: float
    ) -> SearchResponse:
        """
        Format search results into response
        
        Args:
            results: Raw search results
            query: Original query
            intent: Query intent
            search_time: Time taken for search
            
        Returns:
            Formatted SearchResponse
        """
        formatted_results = []
        
        for i, result in enumerate(results):
            formatted_results.append({
                "id": f"result_{i}",
                "title": result.get("title", f"{intent.technology} Documentation"),
                "content": result.get("content", result.get("text", "")),
                "source": result.get("source", ""),
                "relevance_score": result.get("score", result.get("similarity", 0.0)),
                "metadata": {
                    "technology": intent.technology,
                    "topics": intent.topics,
                    "doc_type": intent.doc_type,
                    **result.get("metadata", {})
                }
            })
        
        return SearchResponse(
            query=query,
            results=formatted_results,
            total_count=len(formatted_results),
            search_time_ms=int(search_time * 1000),
            cached=False,
            metadata={
                "intent": intent.dict(),
                "enhanced": True
            }
        )
    
    async def _track_search(
        self, 
        query: str, 
        intent: QueryIntent, 
        response: SearchResponse
    ):
        """
        Track search in database for analytics
        
        Args:
            query: Search query
            intent: Query intent
            response: Search response
        """
        try:
            # Generate query hash
            query_hash = hashlib.md5(query.encode()).hexdigest()
            
            # Store in search_cache table
            query_insert = """
            INSERT INTO search_cache (
                query_hash,
                original_query,
                search_params,
                result_count,
                cache_hit,
                execution_time_ms,
                created_at,
                access_count
            ) VALUES (
                :query_hash,
                :original_query,
                :search_params,
                :result_count,
                :cache_hit,
                :execution_time_ms,
                :created_at,
                1
            )
            ON CONFLICT(query_hash) DO UPDATE SET
                access_count = search_cache.access_count + 1,
                updated_at = :created_at
            """
            
            params = {
                "query_hash": query_hash,
                "original_query": query,
                "search_params": json.dumps({
                    "technology": intent.technology,
                    "topics": intent.topics,
                    "doc_type": intent.doc_type
                }),
                "result_count": response.total_count,
                "cache_hit": response.cached,
                "execution_time_ms": response.search_time_ms,
                "created_at": datetime.utcnow()
            }
            
            await self.db_manager.execute(query_insert, params)
            
        except Exception as e:
            logger.error(f"Failed to track search: {e}")