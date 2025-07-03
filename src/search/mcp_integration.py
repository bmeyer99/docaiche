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
logger.setLevel(logging.DEBUG)


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
    
    def unregister_external_provider(self, provider_id: str) -> bool:
        """
        Unregister an external search provider from MCP.
        
        Args:
            provider_id: Unique provider identifier
            
        Returns:
            True if provider was removed, False if not found
        """
        if provider_id in self.external_providers:
            del self.external_providers[provider_id]
            logger.info(f"Unregistered external provider: {provider_id}")
            return True
        return False
    
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
        from src.search.models import EvaluationResult
        evaluation = EvaluationResult(
            overall_quality=0.3,  # Low to trigger external search
            relevance_assessment=0.3,
            completeness_score=0.3,
            needs_enrichment=True,  # Changed from needs_external_search
            enrichment_topics=[],  # Changed from missing_information
            confidence_level=0.7,
            reasoning="Generating external query for enhanced search results"
        )
        
        return await self.text_ai.generate_external_query(normalized, evaluation)
    
    async def execute_external_search(
        self,
        query: str,
        provider_ids: Optional[List[str]] = None,
        technology_hint: Optional[str] = None,
        max_results: int = 10,
        trace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute high-performance external search using optimized orchestrator.
        
        Args:
            query: Search query
            provider_ids: Specific providers to use (None = auto-select)
            technology_hint: Technology context for provider selection
            max_results: Maximum results to return
            trace_id: Optional trace ID for request tracking
            
        Returns:
            Optimized results from external providers
        """
        # Generate trace ID if not provided
        if not trace_id:
            import uuid
            trace_id = f"mcp-{uuid.uuid4().hex[:8]}"
            
        logger.info(f"[{trace_id}] execute_external_search called with query: {query}")
        logger.info(f"[{trace_id}] Available providers: {list(self.external_providers.keys())}")
        logger.info(f"[{trace_id}] Requested provider_ids: {provider_ids}")
        logger.info(f"[{trace_id}] Max results: {max_results}")
        
        if not hasattr(self, '_external_orchestrator'):
            # Initialize orchestrator lazily
            logger.info(f"[{trace_id}] Initializing external orchestrator")
            await self._init_external_orchestrator()
        
        if not self._external_orchestrator:
            logger.warning(f"[{trace_id}] External search orchestrator not available, falling back to simple search")
            return await self._execute_simple_external_search(query, provider_ids, trace_id)
        
        try:
            logger.info(f"[{trace_id}] Calling orchestrator search method")
            # Execute optimized search
            search_results = await self._external_orchestrator.search(
                query=query,
                technology_hint=technology_hint,
                max_results=max_results,
                provider_ids=provider_ids
            )
            
            logger.info(f"[{trace_id}] Orchestrator returned search_results type: {type(search_results)}")
            logger.info(f"[{trace_id}] Results count: {len(search_results.results) if hasattr(search_results, 'results') else 'N/A'}")
            
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
                f"[{trace_id}] External search completed: {len(results)} results in {search_results.execution_time_ms}ms"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[{trace_id}] Optimized external search failed: {e}", exc_info=True)
            # Fallback to simple search
            return await self._execute_simple_external_search(query, provider_ids, trace_id)
    
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
            
            # Create provider registry and register our providers
            provider_registry = ProviderRegistry()
            
            # Register all external providers to the registry
            for provider_id, provider in self.external_providers.items():
                await provider_registry.add_provider(provider_id, provider, validate=False)
                logger.info(f"Registered {provider_id} to external orchestrator registry")
            
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
        provider_ids: Optional[List[str]] = None,
        trace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback to simple external search without orchestrator.
        
        Args:
            query: Search query
            provider_ids: Specific providers to use
            trace_id: Trace ID for request tracking
            
        Returns:
            Simple search results
        """
        if not trace_id:
            import uuid
            trace_id = f"simple-{uuid.uuid4().hex[:8]}"
            
        logger.info(f"[{trace_id}] Executing simple external search for: {query}, providers: {provider_ids}")
        results = []
        
        # Get providers to use
        providers_to_use = self.external_providers
        logger.info(f"[{trace_id}] Available providers: {list(self.external_providers.keys())}")
        if provider_ids:
            providers_to_use = {
                pid: p for pid, p in self.external_providers.items()
                if pid in provider_ids
            }
            logger.info(f"[{trace_id}] Using filtered providers: {list(providers_to_use.keys())}")
        
        # Execute searches
        for provider_id, provider in providers_to_use.items():
            try:
                logger.info(f"[{trace_id}] Executing search with provider: {provider_id}")
                
                # Create SearchOptions for the provider
                from src.mcp.providers.models import SearchOptions
                search_options = SearchOptions(query=query, max_results=max_results or 10)
                
                # Assume simple search interface
                if hasattr(provider, 'search'):
                    logger.debug(f"[{trace_id}] Calling {provider_id}.search() with query: {query}")
                    search_results = await provider.search(search_options)
                    
                    # Log results info
                    if hasattr(search_results, 'error') and search_results.error:
                        logger.error(f"[{trace_id}] Provider {provider_id} returned error: {search_results.error}")
                    else:
                        logger.info(f"[{trace_id}] Provider {provider_id} returned {len(search_results.results) if hasattr(search_results, 'results') else 0} results")
                    
                    # Extract results from SearchResults object
                    provider_results = []
                    if hasattr(search_results, 'results'):
                        for result in search_results.results:
                            provider_results.append({
                                'title': result.title,
                                'url': result.url,
                                'snippet': result.snippet,
                                'content_type': str(getattr(result, 'content_type', 'unknown')),
                                'source_domain': getattr(result, 'source_domain', '')
                            })
                else:
                    # Legacy interface
                    logger.debug(f"[{trace_id}] Using legacy execute_search for {provider_id}")
                    provider_results = await provider.execute_search(query, limit=10)
                
                logger.info(f"[{trace_id}] Provider {provider_id} processing {len(provider_results)} results")
                
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
                logger.error(f"[{trace_id}] Simple external search failed for {provider_id}: {e}", exc_info=True)
        
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
    print(f"MCP DEBUG: create_mcp_enhancer called with enable_external_providers={enable_external_providers}")
    logger.info(f"MCP DEBUG: create_mcp_enhancer called with enable_external_providers={enable_external_providers}")
    enhancer = MCPSearchEnhancer(llm_client, query_analyzer)
    
    if enable_external_providers:
        print("MCP DEBUG: enable_external_providers is True, starting provider registration")
        logger.info("MCP DEBUG: enable_external_providers is True, starting provider registration")
        # Import and register MCP providers with real configuration
        try:
            print("MCP DEBUG: Starting imports...")
            from src.mcp.providers.implementations.brave import BraveSearchProvider
            print("MCP DEBUG: Imported BraveSearchProvider")
            # DuckDuckGo removed - no official API available
            from src.mcp.providers.models import ProviderConfig, ProviderType
            print("MCP DEBUG: Imported models")
            from src.core.config import get_system_configuration
            from src.core.config.manager import ConfigurationManager
            import os
            print("MCP DEBUG: All imports successful")
            
            # Get both structured config and raw config
            config = get_system_configuration()
            config_manager = ConfigurationManager()
            raw_config_dict = config_manager.get_raw_configuration()
            
            print(f"MCP DEBUG: Full config type: {type(config)}")
            print(f"MCP DEBUG: Raw config dict keys: {list(raw_config_dict.keys())}")
            
            # Get MCP configuration from raw dict (includes database overrides)
            raw_mcp_config = raw_config_dict.get('mcp', {})
            raw_external_search = raw_mcp_config.get('external_search', {})
            raw_providers = raw_external_search.get('providers', {})
            
            print(f"MCP DEBUG: Raw MCP config: {raw_mcp_config}")
            print(f"MCP DEBUG: Raw providers from database: {list(raw_providers.keys())}")
            
            # Use raw providers config (includes database overrides)
            providers_config = raw_providers
            
            # Log what we're getting from each source
            if config and hasattr(config, 'mcp') and config.mcp:
                structured_providers = config.mcp.external_search.providers if hasattr(config.mcp.external_search, 'providers') else {}
                print(f"MCP DEBUG: Structured config providers: {list(structured_providers.keys())}")
            print(f"MCP DEBUG: Using raw config providers: {list(providers_config.keys())}")
                
            # Also load raw YAML config for Context7 custom fields
            raw_config = {}
            try:
                import yaml
                with open('config.yaml', 'r') as f:
                    raw_yaml = yaml.safe_load(f)
                    if raw_yaml and 'mcp' in raw_yaml and 'external_search' in raw_yaml['mcp']:
                        raw_config = raw_yaml['mcp']['external_search'].get('providers', {})
                        print(f"MCP DEBUG: Raw Context7 config: {raw_config.get('context7', {})}")
            except Exception as e:
                logger.warning(f"Failed to load raw YAML config: {e}")
            
            print(f"MCP DEBUG: Config loaded - providers_config has {len(providers_config)} providers")
            print(f"MCP DEBUG: providers_config: {list(providers_config.keys())}")
            
            registered_count = 0
            
            # Register all providers from configuration
            for provider_id, provider_config_data in providers_config.items():
                print(f"MCP DEBUG: Processing provider {provider_id}, data type: {type(provider_config_data)}")
                print(f"MCP DEBUG: Provider data: {provider_config_data}")
                
                # Handle both dict and object access patterns
                if isinstance(provider_config_data, dict):
                    enabled = provider_config_data.get('enabled', True)
                    api_key_from_config = provider_config_data.get('api_key')
                    priority = provider_config_data.get('priority', 100)
                    max_requests = provider_config_data.get('max_requests_per_minute', 60)
                    timeout = provider_config_data.get('timeout_seconds', 5.0)
                else:
                    enabled = getattr(provider_config_data, 'enabled', True)
                    api_key_from_config = getattr(provider_config_data, 'api_key', None)
                    priority = getattr(provider_config_data, 'priority', 100)
                    max_requests = getattr(provider_config_data, 'max_requests_per_minute', 60)
                    timeout = getattr(provider_config_data, 'timeout_seconds', 5.0)
                
                if not provider_config_data or not enabled:
                    print(f"MCP DEBUG: Skipping disabled provider {provider_id}")
                    continue
                    
                # Determine provider type
                provider_type = None
                if 'brave' in provider_id.lower():
                    provider_type = ProviderType.BRAVE
                elif 'google' in provider_id.lower():
                    provider_type = ProviderType.GOOGLE
                elif 'searxng' in provider_id.lower():
                    provider_type = ProviderType.SEARXNG
                elif 'perplexity' in provider_id.lower():
                    provider_type = ProviderType.PERPLEXITY
                elif 'kagi' in provider_id.lower():
                    provider_type = ProviderType.KAGI
                elif 'context7' in provider_id.lower():
                    provider_type = ProviderType.CONTEXT7
                else:
                    logger.warning(f"Unknown provider type for {provider_id}, skipping")
                    continue
                
                # Get API key
                api_key = None
                if provider_type == ProviderType.BRAVE:
                    env_key = os.getenv('BRAVE_API_KEY')
                    logger.debug(f"Provider {provider_id}: env_key={env_key}, config_key={api_key_from_config}")
                    
                    api_key = env_key
                    if not api_key:
                        # Only use config key if it's not an environment variable placeholder
                        if api_key_from_config and api_key_from_config != '${BRAVE_API_KEY}':
                            api_key = api_key_from_config
                            logger.debug(f"Using config key for {provider_id}: {api_key[:10]}...")
                    
                    if not api_key:
                        logger.warning(f"Brave provider {provider_id} enabled but no API key found")
                        continue
                elif provider_type == ProviderType.CONTEXT7:
                    # Context7 doesn't need an API key
                    api_key = "not_required"
                else:
                    # For other providers, get API key from config
                    api_key = api_key_from_config
                    if not api_key:
                        logger.warning(f"Provider {provider_id} enabled but no API key found")
                        continue
                
                # Create provider config
                provider_config = ProviderConfig(
                    provider_id=provider_id,
                    provider_type=provider_type,
                    enabled=True,
                    api_key=api_key,
                    priority=priority,
                    max_requests_per_minute=max_requests,
                    timeout_seconds=timeout,
                    custom_headers={}
                )
                
                # Create and register provider
                print(f"MCP DEBUG: Attempting to create provider {provider_id} of type {provider_type}")
                logger.info(f"MCP DEBUG: Attempting to create provider {provider_id} of type {provider_type}")
                try:
                    if provider_type == ProviderType.BRAVE:
                        provider = BraveSearchProvider(provider_config)
                    elif provider_type == ProviderType.CONTEXT7:
                        from src.mcp.providers.implementations.context7_provider import Context7Provider
                        # Get Context7-specific config from raw YAML
                        context7_raw = raw_config.get('context7', {})
                        provider_config.config = {
                            'command': context7_raw.get('command', 'npx'),
                            'args': context7_raw.get('args', ['-y', '@upstash/context7-mcp']),
                            'cache_ttl': context7_raw.get('cache_ttl', 3600)
                        }
                        print(f"MCP DEBUG: Creating Context7Provider with config: {provider_config.config}")
                        provider = Context7Provider(provider_config)
                        print(f"MCP DEBUG: Context7Provider created successfully")
                    else:
                        logger.warning(f"No implementation for provider type {provider_type}")
                        continue
                    
                    enhancer.register_external_provider(provider_id, provider)
                    registered_count += 1
                    print(f"MCP DEBUG: Successfully registered {provider_id} provider (type: {provider_type})")
                    logger.info(f"Registered {provider_id} provider (type: {provider_type})")
                except Exception as e:
                    print(f"MCP ERROR: Failed to create provider {provider_id}: {e}")
                    logger.error(f"Failed to create provider {provider_id}: {e}", exc_info=True)
            
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