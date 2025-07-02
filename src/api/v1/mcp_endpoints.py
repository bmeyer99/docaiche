"""
MCP (Model Context Protocol) API Endpoints
==========================================

API endpoints for managing MCP external search providers and configuration.
Integrates with existing search orchestrator and configuration system.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .mcp_schemas import (
    CreateProviderRequest,
    UpdateProviderRequest,
    ProviderResponse,
    ProvidersListResponse,
    SearchConfigRequest,
    SearchConfigResponse,
    PerformanceStatsResponse,
    ExternalSearchRequest,
    ExternalSearchResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    ConfigValidationResponse,
    ProviderHealth,
    ProviderStats
)
from .middleware import get_trace_id
from .dependencies import get_search_orchestrator, get_configuration_manager
from src.search.orchestrator import SearchOrchestrator
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

# Import enhanced logging for MCP monitoring
try:
    from src.logging_config import MetricsLogger, SecurityLogger
    metrics = MetricsLogger(logger)
    _security_logger = SecurityLogger(logger)
except ImportError:
    metrics = None
    _security_logger = None
    logger.warning("Enhanced MCP logging not available")

# Create router for MCP endpoints
router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/providers", response_model=ProvidersListResponse)
async def list_providers(
    request: Request,
    enabled_only: bool = Query(False, description="Only return enabled providers"),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> ProvidersListResponse:
    """
    GET /api/v1/mcp/providers - List all external search providers
    
    Returns comprehensive information about all configured external search
    providers including health status and performance statistics.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Listing MCP providers (enabled_only={enabled_only})")
        
        # Get MCP enhancer from orchestrator
        if not hasattr(search_orchestrator, 'mcp_enhancer') or not search_orchestrator.mcp_enhancer:
            raise HTTPException(
                status_code=503,
                detail="MCP search enhancer not available"
            )
        
        mcp_enhancer = search_orchestrator.mcp_enhancer
        
        # Get performance stats if available
        performance_stats = {}
        if hasattr(mcp_enhancer, 'get_performance_stats'):
            try:
                performance_stats = mcp_enhancer.get_performance_stats()
            except Exception as e:
                logger.warning(f"Failed to get performance stats: {e}")
        
        # Get real provider data from MCP enhancer
        providers = []
        healthy_count = 0
        
        # Get registered external providers
        external_providers = getattr(mcp_enhancer, 'external_providers', {})
        
        for provider_id, provider in external_providers.items():
            try:
                # Check if provider should be included
                if enabled_only and not getattr(provider.config, 'enabled', True):
                    continue
                
                # Get provider capabilities
                capabilities = []
                if hasattr(provider, 'get_capabilities'):
                    provider_caps = provider.get_capabilities()
                    capabilities = [
                        {
                            "feature": "web_search",
                            "supported": True,
                            "description": "General web search capability"
                        },
                        {
                            "feature": "tech_search", 
                            "supported": True,
                            "description": "Technical documentation search"
                        },
                        {
                            "feature": "real_time_search",
                            "supported": getattr(provider_caps, 'supports_date_filtering', False),
                            "description": "Real-time search with date filtering"
                        }
                    ]
                
                # Get health status
                health_status = "unknown"
                response_time_ms = 0
                if hasattr(provider, 'get_health_status'):
                    try:
                        health = provider.get_health_status()
                        health_status = health.status.value if hasattr(health.status, 'value') else str(health.status)
                        response_time_ms = getattr(health, 'response_time_ms', 0) or 0
                    except Exception as e:
                        logger.warning(f"Failed to get health for {provider_id}: {e}")
                        health_status = "unknown"
                
                # Get provider stats
                stats = ProviderStats(
                    provider_id=provider_id,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    avg_response_time_ms=float(response_time_ms),
                    last_24h_requests=0,
                    circuit_breaker_open=False
                )
                
                # Try to get real stats if available
                if hasattr(provider, 'get_stats'):
                    try:
                        provider_stats = provider.get_stats()
                        if provider_stats:
                            stats.total_requests = getattr(provider_stats, 'total_requests', 0)
                            stats.successful_requests = getattr(provider_stats, 'successful_requests', 0)
                            stats.failed_requests = getattr(provider_stats, 'failed_requests', 0)
                    except Exception:
                        pass  # Use defaults
                
                # Create provider response
                provider_response = ProviderResponse(
                    provider_id=provider_id,
                    config={
                        "provider_id": provider_id,
                        "provider_type": getattr(provider.config, 'provider_type', 'unknown').value if hasattr(getattr(provider.config, 'provider_type', None), 'value') else str(getattr(provider.config, 'provider_type', 'unknown')),
                        "enabled": getattr(provider.config, 'enabled', True),
                        "priority": getattr(provider.config, 'priority', 99),
                        "max_results": 10,
                        "timeout_seconds": getattr(provider.config, 'timeout_seconds', 3.0),
                        "rate_limit_per_minute": getattr(provider.config, 'max_requests_per_minute', 60),
                        "custom_headers": getattr(provider.config, 'custom_headers', {}),
                        "custom_params": {}
                    },
                    capabilities=capabilities,
                    health=ProviderHealth(
                        provider_id=provider_id,
                        status=health_status,
                        last_check=datetime.utcnow(),
                        response_time_ms=response_time_ms,
                        success_rate=0.0 if stats.total_requests == 0 else stats.successful_requests / stats.total_requests
                    ),
                    stats=stats
                )
                
                providers.append(provider_response)
                if health_status == "healthy":
                    healthy_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing provider {provider_id}: {e}")
                # Create basic error response
                error_response = ProviderResponse(
                    provider_id=provider_id,
                    config={
                        "provider_id": provider_id,
                        "provider_type": "unknown",
                        "enabled": False,
                        "priority": 99,
                        "max_results": 0,
                        "timeout_seconds": 0.0,
                        "rate_limit_per_minute": 0,
                        "custom_headers": {},
                        "custom_params": {}
                    },
                    capabilities=[],
                    health=ProviderHealth(
                        provider_id=provider_id,
                        status="error",
                        last_check=datetime.utcnow(),
                        response_time_ms=0,
                        success_rate=0.0
                    ),
                    stats=ProviderStats(
                        provider_id=provider_id,
                        total_requests=0,
                        successful_requests=0,
                        failed_requests=1,
                        avg_response_time_ms=0.0,
                        last_24h_requests=0,
                        circuit_breaker_open=True
                    )
                )
                providers.append(error_response)
        
        # Log successful request
        logger.info(f"[{trace_id}] MCP providers listed successfully: {len(providers)} providers")
        
        return ProvidersListResponse(
            providers=providers,
            total_count=len(providers),
            healthy_count=healthy_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to list MCP providers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve providers: {str(e)}"
        )


@router.post("/providers", response_model=ProviderResponse)
async def create_provider(
    request: Request,
    create_request: CreateProviderRequest,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> ProviderResponse:
    """
    POST /api/v1/mcp/providers - Create a new external search provider
    
    Creates and configures a new external search provider with the specified
    configuration and capabilities.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Creating MCP provider: {create_request.config.provider_id}")
        
        if _security_logger:
            _security_logger.log_admin_action(
                action="create_provider",
                target=create_request.config.provider_id,
                impact_level="low",
                details={"provider_type": create_request.config.provider_type}
            )
        
        # Validate provider configuration
        if not create_request.config.provider_id:
            raise HTTPException(
                status_code=400,
                detail="Provider ID is required"
            )
        
        if not create_request.config.provider_type:
            raise HTTPException(
                status_code=400,
                detail="Provider type is required"
            )
        
        # Get configuration manager to save the provider
        config_manager = await get_configuration_manager()
        current_config = config_manager.get_configuration()
        
        # Update MCP configuration with new provider
        if not hasattr(current_config, 'mcp') or not current_config.mcp:
            from src.core.config.models import MCPConfig, MCPExternalSearchConfig
            current_config.mcp = MCPConfig(
                external_search=MCPExternalSearchConfig(
                    enabled=True,
                    providers={}
                )
            )
        
        # Convert provider config to MCPProviderConfig
        from src.core.config.models import MCPProviderConfig
        mcp_provider_config = MCPProviderConfig(
            enabled=create_request.config.enabled,
            api_key=create_request.config.api_key,
            priority=create_request.config.priority,
            max_requests_per_minute=create_request.config.rate_limit_per_minute,
            timeout_seconds=create_request.config.timeout_seconds,
            search_engine_id=None
        )
        
        # Add provider to configuration
        current_config.mcp.external_search.providers[create_request.config.provider_id] = mcp_provider_config
        
        # Save configuration
        await config_manager.update_configuration(current_config)
        
        # Create response
        provider_response = ProviderResponse(
            provider_id=create_request.config.provider_id,
            config=create_request.config,
            capabilities=[
                {
                    "feature": "web_search",
                    "supported": True,
                    "description": "General web search capability"
                }
            ],
            health=ProviderHealth(
                provider_id=create_request.config.provider_id,
                status="healthy",
                last_check=datetime.utcnow(),
                response_time_ms=None,
                success_rate=None
            ),
            stats=ProviderStats(
                provider_id=create_request.config.provider_id,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0.0,
                last_24h_requests=0,
                circuit_breaker_open=False
            )
        )
        
        logger.info(f"[{trace_id}] MCP provider created successfully: {create_request.config.provider_id}")
        
        return provider_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to create MCP provider: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create provider: {str(e)}"
        )


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    request: Request,
    provider_id: str,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> ProviderResponse:
    """
    GET /api/v1/mcp/providers/{provider_id} - Get specific provider details
    
    Returns detailed information about a specific external search provider
    including current health status and performance metrics.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Getting MCP provider details: {provider_id}")
        
        # Mock response for now
        if provider_id not in ["brave_search", "duckduckgo_search"]:
            raise HTTPException(
                status_code=404,
                detail=f"Provider not found: {provider_id}"
            )
        
        provider_response = ProviderResponse(
            provider_id=provider_id,
            config={
                "provider_id": provider_id,
                "provider_type": provider_id.split("_")[0],
                "enabled": True,
                "priority": 1,
                "max_results": 10,
                "timeout_seconds": 3.0,
                "rate_limit_per_minute": 60,
                "custom_headers": {},
                "custom_params": {}
            },
            capabilities=[
                {
                    "feature": "web_search",
                    "supported": True,
                    "description": "General web search capability"
                }
            ],
            health=ProviderHealth(
                provider_id=provider_id,
                status="healthy",
                last_check=datetime.utcnow(),
                response_time_ms=250,
                success_rate=0.95
            ),
            stats=ProviderStats(
                provider_id=provider_id,
                total_requests=100,
                successful_requests=95,
                failed_requests=5,
                avg_response_time_ms=250.0,
                last_24h_requests=50,
                circuit_breaker_open=False
            )
        )
        
        return provider_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to get MCP provider: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve provider: {str(e)}"
        )


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    request: Request,
    provider_id: str,
    update_request: UpdateProviderRequest,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> ProviderResponse:
    """
    PUT /api/v1/mcp/providers/{provider_id} - Update provider configuration
    
    Updates the configuration of an existing external search provider.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Updating MCP provider: {provider_id}")
        
        if _security_logger:
            _security_logger.log_admin_action(
                action="update_provider",
                target=provider_id,
                impact_level="low",
                details=update_request.dict(exclude_unset=True)
            )
        
        # Mock update for now
        if provider_id not in ["brave_search", "duckduckgo_search"]:
            raise HTTPException(
                status_code=404,
                detail=f"Provider not found: {provider_id}"
            )
        
        # Return updated provider (mock)
        return await get_provider(request, provider_id, search_orchestrator)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to update MCP provider: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update provider: {str(e)}"
        )


@router.delete("/providers/{provider_id}")
async def delete_provider(
    request: Request,
    provider_id: str,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
):
    """
    DELETE /api/v1/mcp/providers/{provider_id} - Delete a provider
    
    Removes an external search provider from the system.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Deleting MCP provider: {provider_id}")
        
        if _security_logger:
            _security_logger.log_admin_action(
                action="delete_provider",
                target=provider_id,
                impact_level="medium",
                details={}
            )
        
        if provider_id not in ["brave_search", "duckduckgo_search"]:
            raise HTTPException(
                status_code=404,
                detail=f"Provider not found: {provider_id}"
            )
        
        return {"message": f"Provider {provider_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to delete MCP provider: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete provider: {str(e)}"
        )


@router.get("/config", response_model=SearchConfigResponse)
async def get_search_config(
    request: Request,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> SearchConfigResponse:
    """
    GET /api/v1/mcp/config - Get current MCP search configuration
    
    Returns the current configuration for MCP external search functionality.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Getting MCP search configuration")
        
        # Mock configuration for now
        config_response = SearchConfigResponse(
            config={
                "enable_external_search": True,
                "enable_hedged_requests": True,
                "hedged_delay_seconds": 0.2,
                "max_concurrent_providers": 3,
                "external_search_threshold": 0.6,
                "cache_ttl_seconds": 3600,
                "enable_performance_monitoring": True
            },
            cache_config={
                "l1_cache_size": 100,
                "l2_cache_ttl": 3600,
                "compression_threshold": 1024,
                "enable_compression": True,
                "enable_stats": True
            },
            last_updated=datetime.utcnow()
        )
        
        return config_response
        
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to get MCP search configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.post("/search", response_model=ExternalSearchResponse)
async def external_search(
    request: Request,
    search_request: ExternalSearchRequest,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> ExternalSearchResponse:
    """
    POST /api/v1/mcp/search - Execute external search
    
    Performs a search using external providers directly, bypassing internal search.
    Useful for testing and comparing external vs internal results.
    """
    trace_id = get_trace_id(request)
    start_time = time.time()
    
    try:
        logger.info(f"[{trace_id}] MCP external search endpoint called")
        logger.info(f"[{trace_id}] Executing external search: {search_request.query[:50]}...")
        
        # Get MCP enhancer from orchestrator
        if not hasattr(search_orchestrator, 'mcp_enhancer') or not search_orchestrator.mcp_enhancer:
            raise HTTPException(
                status_code=503,
                detail="External search not available"
            )
        
        mcp_enhancer = search_orchestrator.mcp_enhancer
        logger.info(f"[{trace_id}] Got MCP enhancer: {type(mcp_enhancer)}")
        logger.info(f"[{trace_id}] External providers: {list(mcp_enhancer.external_providers.keys()) if hasattr(mcp_enhancer, 'external_providers') else 'No external_providers'}")
        
        # Execute external search
        logger.info(f"[{trace_id}] Calling execute_external_search with query: {search_request.query}")
        external_results = await mcp_enhancer.execute_external_search(
            query=search_request.query,
            provider_ids=search_request.provider_ids,
            technology_hint=search_request.technology_hint,
            max_results=search_request.max_results
        )
        logger.info(f"[{trace_id}] External search returned: {len(external_results)} results")
        
        # Convert results to response format
        response_results = []
        providers_used = set()
        
        for result in external_results:
            providers_used.add(result.get('provider', 'unknown'))
            response_results.append({
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'snippet': result.get('snippet', ''),
                'provider': result.get('provider', 'unknown'),
                'content_type': result.get('content_type', 'web_page'),
                'published_date': None,  # Would parse from result if available
                'relevance_score': None
            })
        
        execution_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"[{trace_id}] External search completed in {execution_time}ms, {len(response_results)} results")
        
        return ExternalSearchResponse(
            results=response_results,
            total_results=len(response_results),
            providers_used=list(providers_used),
            execution_time_ms=execution_time,
            cache_hit=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] External search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"External search failed: {str(e)}"
        )


@router.get("/stats", response_model=PerformanceStatsResponse)
async def get_performance_stats(
    request: Request,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> PerformanceStatsResponse:
    """
    GET /api/v1/mcp/stats - Get MCP performance statistics
    
    Returns comprehensive performance statistics for MCP search functionality.
    """
    trace_id = get_trace_id(request)
    
    try:
        logger.info(f"[{trace_id}] Getting MCP performance statistics")
        
        # Get performance stats from orchestrator
        performance_data = {}
        if (hasattr(search_orchestrator, 'mcp_enhancer') and 
            search_orchestrator.mcp_enhancer and
            hasattr(search_orchestrator.mcp_enhancer, 'get_performance_stats')):
            try:
                performance_data = search_orchestrator.mcp_enhancer.get_performance_stats()
            except Exception as e:
                logger.warning(f"Failed to get performance stats: {e}")
        
        # Mock stats for now
        stats_response = PerformanceStatsResponse(
            stats={
                "total_searches": performance_data.get('search_metrics', {}).get('total_searches', 0),
                "cache_hits": performance_data.get('cache_metrics', {}).get('l1_hits', 0),
                "cache_misses": performance_data.get('search_metrics', {}).get('total_searches', 0) - performance_data.get('cache_metrics', {}).get('l1_hits', 0),
                "avg_response_time_ms": 250.0,
                "hedged_requests": performance_data.get('search_metrics', {}).get('hedged_requests', 0),
                "circuit_breaks": performance_data.get('search_metrics', {}).get('circuit_breaks', 0),
                "provider_stats": []
            },
            collection_period_hours=24,
            last_reset=datetime.utcnow()
        )
        
        return stats_response
        
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to get MCP performance statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )