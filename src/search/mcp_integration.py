"""
MCP Integration for Existing Search System
==========================================

Integration layer that adds MCP capabilities to the existing search
orchestrator without duplicating functionality.
"""

import logging
from typing import Optional, Dict, Any, List

from src.mcp.text_ai.llm_adapter import TextAILLMAdapter
from src.mcp.core.models import NormalizedQuery
from src.llm.client import LLMProviderClient
from src.search.llm_query_analyzer import LLMQueryAnalyzer

logger = logging.getLogger(__name__)


class MCPSearchEnhancer:
    """
    Enhances existing search orchestrator with MCP capabilities.
    
    This class provides MCP features like external search providers
    and enhanced AI capabilities without replacing existing functionality.
    """
    
    def __init__(
        self,
        llm_client: LLMProviderClient,
        query_analyzer: Optional[LLMQueryAnalyzer] = None
    ):
        """
        Initialize MCP enhancer.
        
        Args:
            llm_client: Existing LLM client
            query_analyzer: Existing query analyzer
        """
        self.text_ai = TextAILLMAdapter(llm_client, query_analyzer)
        self.external_providers = {}  # Will be populated with MCP providers
        logger.info("MCPSearchEnhancer initialized")
    
    def register_external_provider(self, provider_id: str, provider: Any) -> None:
        """
        Register an external search provider from MCP.
        
        Args:
            provider_id: Unique provider identifier
            provider: MCP search provider instance
        """
        self.external_providers[provider_id] = provider
        logger.info(f"Registered external provider: {provider_id}")
    
    async def enhance_workspace_selection(
        self,
        query: str,
        available_workspaces: List[Dict[str, Any]],
        technology_hint: Optional[str] = None
    ) -> List[str]:
        """
        Use MCP Text AI to enhance workspace selection.
        
        Args:
            query: Search query
            available_workspaces: Available workspaces
            technology_hint: Optional technology context
            
        Returns:
            Selected workspace IDs
        """
        # Create normalized query for MCP
        normalized = NormalizedQuery(
            original_query=query,
            normalized_text=query.lower().strip(),
            technology_hint=technology_hint,
            query_hash="",  # Not needed for selection
            tokens=[]
        )
        
        # Use Text AI for selection
        return await self.text_ai.select_workspaces(normalized, available_workspaces)
    
    async def get_external_search_query(
        self,
        query: str,
        technology_hint: Optional[str] = None
    ) -> str:
        """
        Generate optimized query for external search.
        
        Args:
            query: Original query
            technology_hint: Optional technology context
            
        Returns:
            Optimized external search query
        """
        normalized = NormalizedQuery(
            original_query=query,
            normalized_text=query.lower().strip(),
            technology_hint=technology_hint,
            query_hash="",
            tokens=[]
        )
        
        # Simple evaluation for external query generation
        from src.mcp.core.models import EvaluationResult
        evaluation = EvaluationResult(
            overall_quality=0.3,  # Low to trigger external search
            relevance_assessment=0.3,
            completeness_score=0.3,
            needs_refinement=False,
            needs_external_search=True,
            missing_information=[],
            confidence_level=0.7,
            reasoning="Generating external query for enhanced search results"
        )
        
        return await self.text_ai.generate_external_query(normalized, evaluation)
    
    async def execute_external_search(
        self,
        query: str,
        provider_ids: Optional[List[str]] = None,
        technology_hint: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Execute high-performance external search using optimized orchestrator.
        
        Args:
            query: Search query
            provider_ids: Specific providers to use (None = auto-select)
            technology_hint: Technology context for provider selection
            max_results: Maximum results to return
            
        Returns:
            Optimized results from external providers
        """
        if not hasattr(self, '_external_orchestrator'):
            # Initialize orchestrator lazily
            await self._init_external_orchestrator()
        
        if not self._external_orchestrator:
            logger.warning("External search orchestrator not available")
            return []
        
        try:
            # Execute optimized search
            search_results = await self._external_orchestrator.search(
                query=query,
                technology_hint=technology_hint,
                max_results=max_results,
                provider_ids=provider_ids
            )
            
            # Convert to dict format for compatibility
            results = []
            for result in search_results.results:
                result_dict = {
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'content_type': result.content_type.value if hasattr(result.content_type, 'value') else str(result.content_type),
                    'provider_rank': result.provider_rank,
                    'published_date': result.published_date.isoformat() if result.published_date else None,
                    'language': result.language,
                    'metadata': result.metadata,
                    'provider': search_results.provider
                }
                results.append(result_dict)
            
            logger.info(
                f"External search completed: {len(results)} results in {search_results.execution_time_ms}ms"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Optimized external search failed: {e}")
            # Fallback to simple search
            return await self._execute_simple_external_search(query, provider_ids)
    
    async def _init_external_orchestrator(self) -> None:
        """Initialize the high-performance external search orchestrator."""
        try:
            from src.mcp.providers.registry import ProviderRegistry
            from src.mcp.providers.search_orchestrator import ExternalSearchOrchestrator
            from src.search.optimized_cache import OptimizedCacheManager
            from src.database.connection import create_cache_manager
            
            # Get cache manager
            cache_manager = await create_cache_manager()
            if not cache_manager:
                logger.warning("Cache manager not available for external search")
                self._external_orchestrator = None
                return
            
            # Create optimized cache
            optimized_cache = OptimizedCacheManager(
                redis_cache=cache_manager,
                l1_size=100,
                compress_threshold=1024,
                enable_stats=True
            )
            
            # Create provider registry
            provider_registry = ProviderRegistry()
            
            # Initialize orchestrator
            self._external_orchestrator = ExternalSearchOrchestrator(
                provider_registry=provider_registry,
                cache_manager=optimized_cache,
                enable_hedged_requests=True,
                hedged_delay=0.2,
                max_concurrent_providers=3
            )
            
            logger.info("External search orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize external search orchestrator: {e}")
            self._external_orchestrator = None
    
    async def _execute_simple_external_search(
        self,
        query: str,
        provider_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback to simple external search without orchestrator.
        
        Args:
            query: Search query
            provider_ids: Specific providers to use
            
        Returns:
            Simple search results
        """
        results = []
        
        # Get providers to use
        providers_to_use = self.external_providers
        if provider_ids:
            providers_to_use = {
                pid: p for pid, p in self.external_providers.items()
                if pid in provider_ids
            }
        
        # Execute searches
        for provider_id, provider in providers_to_use.items():
            try:
                # Assume simple search interface
                if hasattr(provider, 'search'):
                    provider_results = await provider.search(query, limit=10)
                else:
                    # Legacy interface
                    provider_results = await provider.execute_search(query, limit=10)
                
                # Add provider info to results
                for result in provider_results:
                    if isinstance(result, dict):
                        result['provider'] = provider_id
                        results.append(result)
                    else:
                        # Convert object to dict
                        result_dict = {
                            'title': getattr(result, 'title', ''),
                            'url': getattr(result, 'url', ''),
                            'snippet': getattr(result, 'snippet', ''),
                            'provider': provider_id
                        }
                        results.append(result_dict)
                        
            except Exception as e:
                logger.error(f"Simple external search failed for {provider_id}: {e}")
        
        return results
    
    def is_external_search_available(self) -> bool:
        """Check if any external providers are available."""
        return len(self.external_providers) > 0 or hasattr(self, '_external_orchestrator')
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from orchestrator."""
        if hasattr(self, '_external_orchestrator') and self._external_orchestrator:
            return self._external_orchestrator.get_performance_stats()
        return {}


# Factory function for easy integration
def create_mcp_enhancer(
    llm_client: LLMProviderClient,
    query_analyzer: Optional[LLMQueryAnalyzer] = None,
    enable_external_providers: bool = True
) -> MCPSearchEnhancer:
    """
    Create MCP enhancer with optional external providers.
    
    Args:
        llm_client: Existing LLM client
        query_analyzer: Existing query analyzer
        enable_external_providers: Whether to load MCP external providers
        
    Returns:
        Configured MCPSearchEnhancer instance
    """
    enhancer = MCPSearchEnhancer(llm_client, query_analyzer)
    
    if enable_external_providers:
        # Import and register MCP providers with real configuration
        try:
            from src.mcp.providers.implementations.brave import BraveSearchProvider
            from src.mcp.providers.implementations.duckduckgo import DuckDuckGoSearchProvider
            from src.mcp.providers.models import ProviderConfig, ProviderType
            from src.core.config import get_system_configuration
            import os
            
            # Get configuration
            config = get_system_configuration()
            mcp_config = getattr(config, 'mcp', None) if config else None
            providers_config = getattr(mcp_config, 'external_search', {}).get('providers', {}) if mcp_config else {}
            
            registered_count = 0
            
            # Register Brave Search if enabled and API key available
            brave_config = providers_config.get('brave_search', {})
            if brave_config.get('enabled', False):
                brave_api_key = os.getenv('BRAVE_API_KEY') or brave_config.get('api_key', '').replace('${BRAVE_API_KEY}', '')
                if brave_api_key and brave_api_key != '${BRAVE_API_KEY}':
                    provider_config = ProviderConfig(
                        provider_id="brave_search",
                        provider_type=ProviderType.BRAVE,
                        enabled=True,
                        api_key=brave_api_key,
                        priority=brave_config.get('priority', 1),
                        max_requests_per_minute=brave_config.get('max_requests_per_minute', 60),
                        timeout_seconds=brave_config.get('timeout_seconds', 3),
                        custom_headers={}
                    )
                    brave_provider = BraveSearchProvider(provider_config)
                    enhancer.register_external_provider('brave_search', brave_provider)
                    registered_count += 1
                    logger.info("Registered Brave Search provider")
                else:
                    logger.warning("Brave Search enabled but no API key found (set BRAVE_API_KEY)")
            
            # Register DuckDuckGo (no API key required)
            ddg_config = providers_config.get('duckduckgo', {})
            if ddg_config.get('enabled', True):  # Default enabled since no API key needed
                provider_config = ProviderConfig(
                    provider_id="duckduckgo",
                    provider_type=ProviderType.DUCKDUCKGO,
                    enabled=True,
                    api_key="",  # Not required
                    priority=ddg_config.get('priority', 3),
                    max_requests_per_minute=ddg_config.get('max_requests_per_minute', 30),
                    timeout_seconds=ddg_config.get('timeout_seconds', 4),
                    custom_headers={}
                )
                ddg_provider = DuckDuckGoSearchProvider(provider_config)
                enhancer.register_external_provider('duckduckgo', ddg_provider)
                registered_count += 1
                logger.info("Registered DuckDuckGo provider")
            
            print(f"MCP SUCCESS: Registered {registered_count} external providers")
            logger.info(f"MCP external providers registered: {registered_count} providers")
            
        except ImportError as e:
            # Use print for debugging since logging might not show
            print(f"MCP IMPORT ERROR: {e}")
            print(f"Import error details: {type(e).__name__}: {str(e)}")
            logger.warning(f"MCP providers import failed: {e}")
        except Exception as e:
            print(f"MCP EXCEPTION: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"MCP TRACEBACK: {traceback.format_exc()}")
            logger.error(f"Failed to register MCP providers: {type(e).__name__}: {str(e)}")
    
    return enhancer