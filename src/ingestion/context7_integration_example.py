"""
Context7 Integration Example
============================

Example showing how to integrate Context7IngestionService with SearchOrchestrator
for intelligent documentation processing with TTL support.
"""

import asyncio
import logging
from typing import List

from src.ingestion.context7_ingestion_service import Context7IngestionService, TTLConfig
from src.search.orchestrator import SearchOrchestrator
from src.search.llm_query_analyzer import QueryIntent
from src.llm.client import LLMProviderClient
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.core.config.models import WeaviateConfig, LLMConfig

logger = logging.getLogger(__name__)


class Context7OrchestrationExample:
    """
    Example class showing Context7IngestionService integration with SearchOrchestrator.
    
    Demonstrates:
    - Search orchestration with Context7 provider
    - Intelligent ingestion with TTL support
    - Quality assessment and metadata enrichment
    - Batch processing and cleanup operations
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        weaviate_config: WeaviateConfig,
        db_manager: DatabaseManager
    ):
        self.llm_client = LLMProviderClient(llm_config)
        self.weaviate_client = WeaviateVectorClient(weaviate_config)
        self.db_manager = db_manager
        
        # Configure TTL settings for Context7 documents
        self.ttl_config = TTLConfig(
            default_days=30,
            min_days=1,
            max_days=90,
            technology_multipliers={
                # Frontend frameworks - frequent updates
                "react": 1.5,
                "vue": 1.5,
                "angular": 1.5,
                "svelte": 1.3,
                
                # Meta-frameworks - moderate updates
                "next.js": 2.0,
                "nuxt": 1.8,
                "gatsby": 1.6,
                "sveltekit": 1.5,
                
                # Languages - stable but evolving
                "typescript": 2.0,
                "javascript": 1.2,
                "python": 1.5,
                
                # Backend frameworks - moderate stability
                "express": 1.3,
                "fastapi": 1.6,
                "django": 1.8,
                "flask": 1.4,
                "nestjs": 1.7,
                
                # Build tools - frequent updates
                "webpack": 1.2,
                "vite": 1.4,
                "rollup": 1.3,
                "parcel": 1.2,
                
                # CSS frameworks - moderate stability
                "tailwind": 1.2,
                "bootstrap": 1.0,
                "material-ui": 1.3,
                
                # Testing frameworks - stable
                "jest": 1.5,
                "cypress": 1.6,
                "playwright": 1.7,
                "vitest": 1.4,
                
                # State management - stable
                "redux": 1.8,
                "mobx": 1.6,
                "zustand": 1.4,
            },
            doc_type_multipliers={
                # Reference documentation - long-lasting
                "api": 2.5,
                "reference": 2.5,
                
                # Educational content - moderately lasting
                "guide": 1.8,
                "tutorial": 1.5,
                "best_practices": 2.2,
                "cookbook": 1.7,
                
                # Getting started - stable basics
                "getting_started": 1.6,
                "installation": 1.4,
                "configuration": 2.0,
                
                # Support content - moderately lasting
                "troubleshooting": 1.9,
                "faq": 1.7,
                
                # News and updates - short-lived
                "changelog": 0.4,
                "release_notes": 0.6,
                "migration": 1.2,
                "news": 0.3,
                "announcement": 0.5,
                "blog": 0.8,
                
                # Examples - moderately lasting
                "examples": 1.3,
            }
        )
        
        # Initialize Context7 ingestion service
        self.context7_service = Context7IngestionService(
            llm_client=self.llm_client,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            ttl_config=self.ttl_config
        )
        
        # Initialize search orchestrator
        self.search_orchestrator = SearchOrchestrator(
            db_manager=self.db_manager,
            llm_client=self.llm_client
        )
    
    async def initialize(self):
        """Initialize all services"""
        await self.weaviate_client.connect()
        logger.info("Context7 orchestration example initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.weaviate_client.disconnect()
        logger.info("Context7 orchestration example cleaned up")
    
    async def intelligent_documentation_search_and_ingest(
        self,
        query: str,
        technology: str,
        max_results: int = 10
    ) -> dict:
        """
        Perform intelligent search and ingestion workflow.
        
        Args:
            query: Search query
            technology: Technology to search for
            max_results: Maximum number of results to process
            
        Returns:
            Dict with search and ingestion results
        """
        try:
            logger.info(f"Starting intelligent search and ingest for: {query}")
            
            # Step 1: Analyze query intent
            intent = QueryIntent(
                intent="documentation",
                technology=technology,
                topics=[],  # Will be extracted from query
                doc_type="documentation",
                user_level="intermediate",
                specific_question=query,
                context_needed=True,
                priority="high"
            )
            
            # Step 2: Search using Context7 provider
            search_results = await self.search_orchestrator.search_with_provider(
                query=query,
                provider_type="context7",
                max_results=max_results
            )
            
            if not search_results or not search_results.results:
                return {
                    "success": False,
                    "message": "No Context7 results found",
                    "search_results": 0,
                    "ingested_documents": 0
                }
            
            logger.info(f"Found {len(search_results.results)} Context7 results")
            
            # Step 3: Process results with intelligent ingestion
            ingestion_results = await self.context7_service.process_context7_results(
                search_results.results, intent
            )
            
            successful_ingestions = [r for r in ingestion_results if r.success]
            
            # Step 4: Generate summary
            result = {
                "success": True,
                "query": query,
                "technology": technology,
                "search_results": len(search_results.results),
                "ingestion_attempts": len(ingestion_results),
                "successful_ingestions": len(successful_ingestions),
                "total_chunks_processed": sum(r.chunks_processed for r in successful_ingestions),
                "workspaces_created": list(set(r.workspace_slug for r in successful_ingestions if r.workspace_slug)),
                "execution_time_ms": search_results.execution_time_ms,
                "provider": search_results.provider
            }
            
            logger.info(f"Intelligent search and ingest completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed intelligent search and ingest: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "technology": technology
            }
    
    async def batch_technology_ingestion(
        self,
        technologies: List[str],
        base_queries: List[str] = None
    ) -> dict:
        """
        Perform batch ingestion for multiple technologies.
        
        Args:
            technologies: List of technologies to process
            base_queries: Base queries to use for each technology
            
        Returns:
            Dict with batch processing results
        """
        if base_queries is None:
            base_queries = [
                "getting started guide",
                "API reference",
                "best practices",
                "tutorial",
                "configuration"
            ]
        
        try:
            logger.info(f"Starting batch ingestion for {len(technologies)} technologies")
            
            batch_results = {
                "total_technologies": len(technologies),
                "successful_technologies": 0,
                "failed_technologies": 0,
                "total_documents_ingested": 0,
                "total_chunks_processed": 0,
                "results_by_technology": {},
                "errors": []
            }
            
            for technology in technologies:
                logger.info(f"Processing technology: {technology}")
                tech_results = {
                    "technology": technology,
                    "queries_processed": 0,
                    "documents_ingested": 0,
                    "chunks_processed": 0,
                    "workspaces": [],
                    "errors": []
                }
                
                try:
                    for base_query in base_queries:
                        query = f"{technology} {base_query}"
                        
                        result = await self.intelligent_documentation_search_and_ingest(
                            query=query,
                            technology=technology,
                            max_results=5  # Limit for batch processing
                        )
                        
                        if result["success"]:
                            tech_results["queries_processed"] += 1
                            tech_results["documents_ingested"] += result["successful_ingestions"]
                            tech_results["chunks_processed"] += result["total_chunks_processed"]
                            tech_results["workspaces"].extend(result["workspaces_created"])
                        else:
                            tech_results["errors"].append(f"Query '{query}': {result.get('error', 'Unknown error')}")
                    
                    # Remove duplicate workspaces
                    tech_results["workspaces"] = list(set(tech_results["workspaces"]))
                    
                    if tech_results["documents_ingested"] > 0:
                        batch_results["successful_technologies"] += 1
                    else:
                        batch_results["failed_technologies"] += 1
                    
                    batch_results["total_documents_ingested"] += tech_results["documents_ingested"]
                    batch_results["total_chunks_processed"] += tech_results["chunks_processed"]
                    batch_results["results_by_technology"][technology] = tech_results
                    
                    logger.info(f"Completed {technology}: {tech_results['documents_ingested']} documents, {tech_results['chunks_processed']} chunks")
                    
                except Exception as e:
                    logger.error(f"Failed processing technology {technology}: {e}")
                    batch_results["failed_technologies"] += 1
                    batch_results["errors"].append(f"{technology}: {str(e)}")
            
            logger.info(f"Batch ingestion completed: {batch_results}")
            return batch_results
            
        except Exception as e:
            logger.error(f"Batch ingestion failed: {e}")
            return {
                "total_technologies": len(technologies),
                "successful_technologies": 0,
                "failed_technologies": len(technologies),
                "error": str(e)
            }
    
    async def cleanup_expired_content(self, workspace_slugs: List[str] = None) -> dict:
        """
        Clean up expired content across workspaces.
        
        Args:
            workspace_slugs: Specific workspaces to clean, or None for all
            
        Returns:
            Dict with cleanup results
        """
        try:
            logger.info("Starting expired content cleanup")
            
            if workspace_slugs is None:
                # Get all workspaces
                workspaces = await self.weaviate_client.list_workspaces()
                workspace_slugs = [w.get("slug") for w in workspaces if w.get("slug")]
            
            cleanup_results = {
                "total_workspaces": len(workspace_slugs),
                "workspaces_cleaned": 0,
                "total_documents_deleted": 0,
                "total_chunks_deleted": 0,
                "results_by_workspace": {},
                "errors": []
            }
            
            for workspace_slug in workspace_slugs:
                try:
                    result = await self.context7_service.cleanup_expired_documents(workspace_slug)
                    
                    cleanup_results["workspaces_cleaned"] += 1
                    cleanup_results["total_documents_deleted"] += result["weaviate_cleanup"]["deleted_documents"]
                    cleanup_results["total_chunks_deleted"] += result["weaviate_cleanup"]["deleted_chunks"]
                    cleanup_results["results_by_workspace"][workspace_slug] = result
                    
                    logger.info(f"Cleaned workspace {workspace_slug}: {result['weaviate_cleanup']['deleted_documents']} documents")
                    
                except Exception as e:
                    logger.error(f"Failed to cleanup workspace {workspace_slug}: {e}")
                    cleanup_results["errors"].append(f"{workspace_slug}: {str(e)}")
            
            logger.info(f"Cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {
                "total_workspaces": len(workspace_slugs) if workspace_slugs else 0,
                "workspaces_cleaned": 0,
                "error": str(e)
            }
    
    async def get_ttl_statistics(self, workspace_slugs: List[str] = None) -> dict:
        """
        Get TTL statistics across workspaces.
        
        Args:
            workspace_slugs: Specific workspaces to analyze
            
        Returns:
            Dict with TTL statistics
        """
        try:
            if workspace_slugs is None:
                workspaces = await self.weaviate_client.list_workspaces()
                workspace_slugs = [w.get("slug") for w in workspaces if w.get("slug")]
            
            overall_stats = {
                "total_workspaces": len(workspace_slugs),
                "total_documents": 0,
                "expired_documents": 0,
                "expiring_soon_documents": 0,
                "long_term_documents": 0,
                "stats_by_workspace": {},
                "technology_breakdown": {},
                "doc_type_breakdown": {}
            }
            
            for workspace_slug in workspace_slugs:
                try:
                    stats = await self.weaviate_client.get_expiration_statistics(workspace_slug)
                    
                    overall_stats["total_documents"] += stats["total_documents"]
                    overall_stats["expired_documents"] += stats["expired_documents"]
                    overall_stats["expiring_soon_documents"] += stats["expiring_soon_documents"]
                    overall_stats["stats_by_workspace"][workspace_slug] = stats
                    
                    # Aggregate technology and doc type breakdowns
                    for tech, count in stats.get("technology_breakdown", {}).items():
                        overall_stats["technology_breakdown"][tech] = overall_stats["technology_breakdown"].get(tech, 0) + count
                    
                    for doc_type, count in stats.get("doc_type_breakdown", {}).items():
                        overall_stats["doc_type_breakdown"][doc_type] = overall_stats["doc_type_breakdown"].get(doc_type, 0) + count
                    
                except Exception as e:
                    logger.error(f"Failed to get stats for workspace {workspace_slug}: {e}")
            
            overall_stats["long_term_documents"] = (
                overall_stats["total_documents"] - 
                overall_stats["expired_documents"] - 
                overall_stats["expiring_soon_documents"]
            )
            
            return overall_stats
            
        except Exception as e:
            logger.error(f"Failed to get TTL statistics: {e}")
            return {"error": str(e)}


async def example_usage():
    """Example usage of Context7 orchestration"""
    # This would be configured with actual config objects
    example_config = {
        "llm_config": None,  # LLMConfig instance
        "weaviate_config": None,  # WeaviateConfig instance  
        "db_manager": None  # DatabaseManager instance
    }
    
    # For demonstration purposes only
    logger.info("This is an example of how to use Context7IngestionService")
    logger.info("Please configure with actual LLM, Weaviate, and DB instances")
    
    # Example workflow:
    # 1. Initialize orchestration
    # orchestrator = Context7OrchestrationExample(**example_config)
    # await orchestrator.initialize()
    
    # 2. Intelligent search and ingest
    # result = await orchestrator.intelligent_documentation_search_and_ingest(
    #     query="React hooks tutorial",
    #     technology="react"
    # )
    
    # 3. Batch processing
    # batch_result = await orchestrator.batch_technology_ingestion([
    #     "react", "vue", "angular", "typescript", "next.js"
    # ])
    
    # 4. Cleanup expired content
    # cleanup_result = await orchestrator.cleanup_expired_content()
    
    # 5. Get TTL statistics
    # stats = await orchestrator.get_ttl_statistics()
    
    # 6. Cleanup
    # await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(example_usage())