"""
Search Strategies Implementation - PRD-009
Multi-workspace search strategy and workspace selection logic.

Implements the exact WorkspaceSearchStrategy from PRD-009 with intelligent
workspace selection and parallel search execution.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from collections import defaultdict

from .models import WorkspaceInfo, SearchResult, SearchStrategy
from .exceptions import WorkspaceSelectionError, VectorSearchError, SearchTimeoutError
from src.database.connection import DatabaseManager
from src.clients.anythingllm import AnythingLLMClient

logger = logging.getLogger(__name__)


class WorkspaceSearchStrategy:
    """
    Intelligent workspace selection and parallel search execution.
    
    Implements the exact WorkspaceSearchStrategy from PRD-009 with workspace
    selection based on query analysis and technology hints.
    """
    
    def __init__(self, db_manager: DatabaseManager, anythingllm_client: AnythingLLMClient):
        """
        Initialize workspace search strategy.
        
        Args:
            db_manager: Database manager for workspace metadata queries
            anythingllm_client: AnythingLLM client for vector search operations
        """
        self.db_manager = db_manager
        self.anythingllm_client = anythingllm_client
        
        # Technology keyword patterns for workspace matching
        self.technology_patterns = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'pytorch', 'tensorflow'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'express', 'next'],
            'typescript': ['typescript', 'ts', 'angular', 'react', 'vue', 'nest'],
            'java': ['java', 'spring', 'maven', 'gradle', 'junit', 'hibernate'],
            'csharp': ['c#', 'csharp', 'dotnet', '.net', 'asp.net', 'entity'],
            'go': ['go', 'golang', 'gin', 'gorilla', 'echo'],
            'rust': ['rust', 'cargo', 'tokio', 'serde'],
            'php': ['php', 'laravel', 'symfony', 'composer'],
            'ruby': ['ruby', 'rails', 'gem', 'bundler'],
            'docker': ['docker', 'container', 'dockerfile', 'compose'],
            'kubernetes': ['kubernetes', 'k8s', 'kubectl', 'helm'],
            'aws': ['aws', 'amazon', 'ec2', 's3', 'lambda', 'cloudformation'],
            'azure': ['azure', 'microsoft', 'resource group', 'app service'],
            'gcp': ['gcp', 'google cloud', 'compute engine', 'cloud functions']
        }
        
        logger.info("WorkspaceSearchStrategy initialized")
    
    async def identify_relevant_workspaces(
        self, 
        query: str, 
        technology_hint: Optional[str] = None
    ) -> List[WorkspaceInfo]:
        """
        Intelligent workspace selection based on query analysis.
        
        Strategy from PRD-009:
        1. If technology_hint provided, prioritize matching workspaces
        2. Extract technology keywords from query (e.g., "python", "react", "docker")
        3. Query database for workspace-technology mappings
        4. Default to searching all workspaces if no clear technology match
        5. Limit to max 5 workspaces for performance
        
        Returns workspaces ordered by relevance score
        
        Args:
            query: Search query string
            technology_hint: Optional technology filter hint
            
        Returns:
            List of WorkspaceInfo ordered by relevance score
            
        Raises:
            WorkspaceSelectionError: If workspace selection fails
        """
        try:
            logger.info(f"Identifying relevant workspaces for query: {query[:100]}...")
            
            # Step 1: Get all available workspaces from database
            available_workspaces = await self._get_available_workspaces()
            
            if not available_workspaces:
                logger.warning("No workspaces available in database")
                return []
            
            # Step 2: Calculate relevance scores for each workspace
            workspace_scores = {}
            
            # Step 3: Apply technology hint priority
            if technology_hint:
                logger.info(f"Applying technology hint: {technology_hint}")
                for workspace in available_workspaces:
                    if workspace['technology'].lower() == technology_hint.lower():
                        workspace_scores[workspace['slug']] = workspace_scores.get(workspace['slug'], 0.0) + 0.5
            
            # Step 4: Extract technology keywords from query
            detected_technologies = self._extract_technology_keywords(query)
            logger.info(f"Detected technologies in query: {detected_technologies}")
            
            # Step 5: Score workspaces based on detected technologies
            for workspace in available_workspaces:
                workspace_tech = workspace['technology'].lower()
                base_score = workspace_scores.get(workspace['slug'], 0.0)
                
                # Direct technology match
                if workspace_tech in detected_technologies:
                    workspace_scores[workspace['slug']] = base_score + 0.8
                
                # Related technology match
                for tech, keywords in self.technology_patterns.items():
                    if workspace_tech == tech:
                        for keyword in keywords:
                            if keyword.lower() in query.lower():
                                workspace_scores[workspace['slug']] = base_score + 0.3
                                break
                
                # Default score for all workspaces
                if workspace['slug'] not in workspace_scores:
                    workspace_scores[workspace['slug']] = 0.1
            
            # Step 6: Create WorkspaceInfo objects with scores
            workspace_infos = []
            for workspace in available_workspaces:
                workspace_info = WorkspaceInfo(
                    slug=workspace['slug'],
                    technology=workspace['technology'],
                    relevance_score=workspace_scores.get(workspace['slug'], 0.1),
                    last_updated=workspace.get('last_updated', datetime.utcnow()),
                    document_count=workspace.get('document_count', 0)
                )
                workspace_infos.append(workspace_info)
            
            # Step 7: Sort by relevance score and limit to max 5
            workspace_infos.sort(key=lambda w: w.relevance_score, reverse=True)
            top_workspaces = workspace_infos[:5]
            
            logger.info(f"Selected {len(top_workspaces)} workspaces for search")
            for ws in top_workspaces:
                logger.debug(f"Workspace: {ws.slug}, tech: {ws.technology}, score: {ws.relevance_score:.2f}")
            
            return top_workspaces
            
        except Exception as e:
            logger.error(f"Failed to identify relevant workspaces: {e}")
            raise WorkspaceSelectionError(
                f"Workspace selection failed: {str(e)}",
                query=query,
                technology_hint=technology_hint,
                error_context={"error": str(e)}
            )
    
    async def execute_parallel_search(
        self, 
        query: str, 
        workspaces: List[WorkspaceInfo]
    ) -> List[SearchResult]:
        """
        Execute search across multiple workspaces in parallel.
        
        Process from PRD-009:
        1. Launch concurrent searches (max 5 simultaneous)
        2. Apply per-workspace timeout (2 seconds each)
        3. Collect results as they complete
        4. Handle individual workspace failures gracefully
        5. Aggregate and deduplicate results by content hash
        6. Apply technology-based ranking boost
        7. Return top 20 results across all workspaces
        
        Args:
            query: Search query string
            workspaces: List of workspaces to search
            
        Returns:
            List of SearchResult objects
            
        Raises:
            VectorSearchError: If all workspace searches fail
        """
        try:
            logger.info(f"Executing parallel search across {len(workspaces)} workspaces")
            
            if not workspaces:
                logger.warning("No workspaces provided for search")
                return []
            
            # Step 1: Create search tasks with timeout (max 5 simultaneous)
            semaphore = asyncio.Semaphore(5)
            search_tasks = []
            
            for workspace in workspaces:
                task = self._search_single_workspace(
                    query, workspace, semaphore, timeout_seconds=2.0
                )
                search_tasks.append(task)
            
            # Step 2: Execute searches and collect results
            logger.info("Launching concurrent workspace searches...")
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Step 3: Process results and handle failures gracefully
            all_results = []
            successful_searches = 0
            failed_searches = 0
            
            for i, result in enumerate(search_results):
                workspace_slug = workspaces[i].slug
                
                if isinstance(result, Exception):
                    logger.warning(f"Search failed for workspace {workspace_slug}: {result}")
                    failed_searches += 1
                elif isinstance(result, list):
                    logger.info(f"Search completed for workspace {workspace_slug}: {len(result)} results")
                    all_results.extend(result)
                    successful_searches += 1
                else:
                    logger.warning(f"Unexpected result type from workspace {workspace_slug}: {type(result)}")
                    failed_searches += 1
            
            # Step 4: Check if any searches succeeded
            if successful_searches == 0:
                raise VectorSearchError(
                    f"All workspace searches failed ({failed_searches} failures)",
                    query=query,
                    error_context={"failed_workspaces": failed_searches}
                )
            
            logger.info(f"Parallel search completed: {successful_searches} successful, {failed_searches} failed")
            
            # Step 5: Aggregate and deduplicate results by content hash
            deduplicated_results = self._deduplicate_results(all_results)
            logger.info(f"Deduplicated {len(all_results)} results to {len(deduplicated_results)}")
            
            # Step 6: Apply technology-based ranking boost
            ranked_results = self._apply_technology_ranking(deduplicated_results, workspaces)
            
            # Step 7: Return top 20 results
            top_results = ranked_results[:20]
            logger.info(f"Returning top {len(top_results)} results")
            
            return top_results
            
        except VectorSearchError:
            # Re-raise vector search errors
            raise
        except Exception as e:
            logger.error(f"Parallel search execution failed: {e}")
            raise VectorSearchError(
                f"Parallel search failed: {str(e)}",
                query=query,
                error_context={"error": str(e), "workspace_count": len(workspaces)}
            )
    
    async def _search_single_workspace(
        self, 
        query: str, 
        workspace: WorkspaceInfo, 
        semaphore: asyncio.Semaphore,
        timeout_seconds: float = 2.0
    ) -> List[SearchResult]:
        """
        Search a single workspace with timeout and error handling.
        
        Args:
            query: Search query
            workspace: Workspace to search
            semaphore: Concurrency control semaphore
            timeout_seconds: Timeout for workspace search
            
        Returns:
            List of SearchResult objects
            
        Raises:
            SearchTimeoutError: If search times out
            VectorSearchError: If search fails
        """
        async with semaphore:
            try:
                logger.debug(f"Starting search in workspace: {workspace.slug}")
                
                # Execute search with timeout
                search_coro = self.anythingllm_client.search_workspace(
                    workspace.slug, query, limit=10
                )
                
                raw_results = await asyncio.wait_for(search_coro, timeout=timeout_seconds)
                
                # Convert raw results to SearchResult objects
                search_results = []
                for raw_result in raw_results:
                    search_result = self._convert_raw_result(raw_result, workspace)
                    search_results.append(search_result)
                
                logger.debug(f"Workspace {workspace.slug} search completed: {len(search_results)} results")
                return search_results
                
            except asyncio.TimeoutError:
                logger.warning(f"Search timeout in workspace {workspace.slug} after {timeout_seconds}s")
                raise SearchTimeoutError(
                    f"Workspace search timed out: {workspace.slug}",
                    timeout_seconds=timeout_seconds,
                    operation=f"search_workspace_{workspace.slug}"
                )
            except Exception as e:
                logger.error(f"Search failed in workspace {workspace.slug}: {e}")
                raise VectorSearchError(
                    f"Workspace search failed: {str(e)}",
                    workspace_slug=workspace.slug,
                    query=query,
                    error_context={"error": str(e)}
                )
    
    async def _get_available_workspaces(self) -> List[Dict[str, Any]]:
        """
        Get available workspaces from database.
        
        Returns:
            List of workspace dictionaries with metadata
        """
        try:
            # Query content_metadata table for available workspaces
            query = """
                SELECT DISTINCT 
                    anythingllm_workspace as slug,
                    technology,
                    MAX(updated_at) as last_updated,
                    COUNT(*) as document_count
                FROM content_metadata 
                WHERE anythingllm_workspace IS NOT NULL 
                    AND processing_status = 'completed'
                GROUP BY anythingllm_workspace, technology
                ORDER BY document_count DESC
            """
            
            rows = await self.db_manager.fetch_all(query)
            
            workspaces = []
            for row in rows:
                workspace = {
                    'slug': row.slug,
                    'technology': row.technology,
                    'last_updated': row.last_updated,
                    'document_count': row.document_count
                }
                workspaces.append(workspace)
            
            return workspaces
            
        except Exception as e:
            logger.error(f"Failed to get available workspaces: {e}")
            return []
    
    def _extract_technology_keywords(self, query: str) -> Set[str]:
        """
        Extract technology keywords from search query.
        
        Args:
            query: Search query string
            
        Returns:
            Set of detected technology keywords
        """
        detected = set()
        query_lower = query.lower()
        
        # Check for direct technology matches
        for tech, keywords in self.technology_patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected.add(tech)
                    break
        
        return detected
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Deduplicate search results by content hash.
        
        Args:
            results: List of search results to deduplicate
            
        Returns:
            List of deduplicated results
        """
        seen_hashes = set()
        deduplicated = []
        
        for result in results:
            # Use content_id as hash for deduplication
            content_hash = result.content_id
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(result)
        
        return deduplicated
    
    def _apply_technology_ranking(
        self, 
        results: List[SearchResult], 
        workspaces: List[WorkspaceInfo]
    ) -> List[SearchResult]:
        """
        Apply technology-based ranking boost to results.
        
        Args:
            results: List of search results
            workspaces: List of workspace info for ranking context
            
        Returns:
            List of results sorted by adjusted relevance score
        """
        # Create workspace relevance lookup
        workspace_relevance = {ws.slug: ws.relevance_score for ws in workspaces}
        
        # Apply ranking boost based on workspace relevance
        for result in results:
            workspace_boost = workspace_relevance.get(result.workspace_slug, 0.1)
            # Boost relevance score by workspace relevance (max 20% boost)
            result.relevance_score = min(1.0, result.relevance_score + (workspace_boost * 0.2))
        
        # Sort by adjusted relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        return results
    
    def _convert_raw_result(self, raw_result: Dict[str, Any], workspace: WorkspaceInfo) -> SearchResult:
        """
        Convert raw AnythingLLM result to SearchResult object.
        
        Args:
            raw_result: Raw result from AnythingLLM
            workspace: Workspace info for context
            
        Returns:
            SearchResult object
        """
        # Extract content snippet (first 200 chars)
        content = raw_result.get('content', '')
        snippet = content[:200] + '...' if len(content) > 200 else content
        
        # Extract metadata
        metadata = raw_result.get('metadata', {})
        
        return SearchResult(
            content_id=metadata.get('document_id', raw_result.get('id', 'unknown')),
            title=metadata.get('document_title', 'Untitled'),
            content_snippet=snippet,
            source_url=metadata.get('source_url', ''),
            relevance_score=raw_result.get('score', 0.5),
            metadata=metadata,
            technology=workspace.technology,
            workspace_slug=workspace.slug,
            chunk_index=metadata.get('chunk_index')
        )