"""
Enhanced GitHub Client with LLM-powered intelligent documentation fetching
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from src.clients.github import GitHubClient
from src.llm.client import LLMProviderClient
from src.search.llm_query_analyzer import QueryIntent
from src.document_processing.models import DocumentContent

logger = logging.getLogger(__name__)


class SmartGitHubClient(GitHubClient):
    """Enhanced GitHub client with intelligent documentation discovery"""
    
    def __init__(self, llm_client: LLMProviderClient, config=None, db_manager=None):
        # Create a minimal config object if not provided
        if config is None:
            from types import SimpleNamespace
            config = SimpleNamespace(
                api_token=None,
                circuit_breaker_failure_threshold=5,
                circuit_breaker_recovery_timeout=300,
                circuit_breaker_timeout_seconds=30
            )
        super().__init__(config, db_manager)
        self.llm = llm_client
        
    def _parse_github_url(self, url: str) -> Tuple[str, str]:
        """
        Extract owner and repo from GitHub URL
        
        Args:
            url: GitHub URL
            
        Returns:
            Tuple of (owner, repo)
        """
        parsed = urlparse(url)
        parts = parsed.path.strip('/').split('/')
        
        if len(parts) >= 2:
            return parts[0], parts[1]
        else:
            raise ValueError(f"Invalid GitHub URL: {url}")
    
    async def fetch_docs_intelligently(
        self, 
        repo_url: str, 
        intent: QueryIntent
    ) -> List[DocumentContent]:
        """
        Intelligently fetch documentation from GitHub based on query intent
        
        Args:
            repo_url: GitHub repository URL
            intent: Analyzed query intent
            
        Returns:
            List of relevant documentation content
        """
        try:
            owner, repo = self._parse_github_url(repo_url)
            
            # First, discover documentation structure
            doc_paths = await self._discover_doc_structure(owner, repo, intent)
            
            # Then fetch the identified files
            contents = []
            for path in doc_paths:
                try:
                    content = await self.fetch_file(owner, repo, path)
                    if content:
                        # Enhance metadata with intent information
                        content.metadata = content.metadata or {}
                        content.metadata.update({
                            "technology": intent.technology,
                            "topics": intent.topics,
                            "doc_type": intent.doc_type,
                            "user_level": intent.user_level
                        })
                        contents.append(content)
                except Exception as e:
                    logger.warning(f"Failed to fetch {path} from {owner}/{repo}: {e}")
                    continue
            
            return contents
            
        except Exception as e:
            logger.error(f"Intelligent GitHub fetch failed: {e}")
            return []
    
    async def _discover_doc_structure(
        self, 
        owner: str, 
        repo: str, 
        intent: QueryIntent
    ) -> List[str]:
        """
        Use LLM to discover relevant documentation files in the repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            intent: Query intent
            
        Returns:
            List of file paths to fetch
        """
        try:
            # Get repository structure first
            structure = await self._get_repo_structure(owner, repo)
            
            topics_str = ', '.join(intent.topics) if intent.topics else "general topics"
            
            prompt = f"""
            Analyze this GitHub repository structure for {intent.technology} documentation.
            
            Repository: {owner}/{repo}
            Looking for: {intent.doc_type} documentation about {topics_str}
            User level: {intent.user_level}
            
            Repository structure:
            {json.dumps(structure, indent=2)[:2000]}  # Limit structure size
            
            Identify the most relevant documentation files based on:
            1. File paths and names
            2. Documentation type needed ({intent.doc_type})
            3. Topics of interest ({topics_str})
            4. User expertise level ({intent.user_level})
            
            Common documentation locations:
            - /README.md
            - /docs/ folder
            - /documentation/ folder
            - /examples/ folder (for tutorials)
            - /guides/ folder
            - /wiki/ folder
            - /tutorials/ folder
            
            Return a JSON array of file paths to fetch, prioritized by relevance.
            Include at most 10 files. Focus on markdown files when possible.
            
            Example response:
            [
                "/docs/tutorial/async.md",
                "/README.md",
                "/examples/async_example.py",
                "/docs/api-reference.md"
            ]
            
            Return ONLY the JSON array of paths.
            """
            
            response = await self.llm.generate(prompt)
            
            # Parse response
            try:
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                paths = json.loads(cleaned_response.strip())
                
                # Validate paths
                valid_paths = []
                for path in paths:
                    if isinstance(path, str) and path.startswith('/'):
                        valid_paths.append(path)
                
                return valid_paths[:10]  # Limit to 10 files
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response for doc paths: {e}")
                return self._get_fallback_paths(intent)
                
        except Exception as e:
            logger.error(f"Documentation discovery failed: {e}")
            return self._get_fallback_paths(intent)
    
    async def _get_repo_structure(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository file structure
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dictionary representing the repository structure
        """
        try:
            # Get repository tree
            url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/main?recursive=1"
            response = await self._make_request('GET', url)
            
            if response and 'tree' in response:
                # Organize by directory
                structure = {"root": []}
                
                for item in response['tree']:
                    path = item['path']
                    item_type = item['type']
                    
                    # Focus on documentation-related files
                    if (item_type == 'blob' and 
                        (path.endswith('.md') or 
                         path.endswith('.rst') or
                         'doc' in path.lower() or
                         'example' in path.lower() or
                         'tutorial' in path.lower() or
                         'guide' in path.lower())):
                        
                        parts = path.split('/')
                        current = structure
                        
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        
                        if "files" not in current:
                            current["files"] = []
                        current["files"].append(parts[-1])
                
                return structure
            
            return {"error": "Unable to fetch repository structure"}
            
        except Exception as e:
            logger.error(f"Failed to get repo structure: {e}")
            return {"error": str(e)}
    
    def _get_fallback_paths(self, intent: QueryIntent) -> List[str]:
        """
        Get common documentation paths as fallback
        """
        paths = ["/README.md"]
        
        # Add common documentation paths based on doc type
        if intent.doc_type == "tutorial":
            paths.extend([
                "/docs/tutorial.md",
                "/docs/getting-started.md",
                "/tutorials/README.md",
                "/examples/README.md"
            ])
        elif intent.doc_type == "reference":
            paths.extend([
                "/docs/api.md",
                "/docs/reference.md",
                "/API.md",
                "/docs/api-reference.md"
            ])
        else:  # guide
            paths.extend([
                "/docs/guide.md",
                "/docs/README.md",
                "/guides/README.md",
                "/documentation/README.md"
            ])
        
        return paths
    
    async def evaluate_content_relevance(
        self, 
        content: DocumentContent, 
        intent: QueryIntent
    ) -> float:
        """
        Evaluate how relevant a piece of content is to the query intent
        
        Args:
            content: Document content to evaluate
            intent: Query intent
            
        Returns:
            Relevance score from 0.0 to 1.0
        """
        try:
            # Truncate content for evaluation
            content_preview = content.text[:2000] if len(content.text) > 2000 else content.text
            
            prompt = f"""
            Evaluate the relevance of this documentation content to the search intent.
            
            Search Intent:
            - Technology: {intent.technology}
            - Topics: {', '.join(intent.topics)}
            - Doc Type: {intent.doc_type}
            - User Level: {intent.user_level}
            
            Content Preview:
            {content_preview}
            
            Rate relevance from 0.0 to 1.0 based on:
            1. Topic coverage
            2. Appropriate difficulty level
            3. Documentation type match
            4. Content quality
            
            Return ONLY a number between 0.0 and 1.0
            """
            
            response = await self.llm.generate(prompt)
            
            try:
                score = float(response.strip())
                return max(0.0, min(1.0, score))
            except ValueError:
                return 0.5  # Default medium relevance
                
        except Exception as e:
            logger.error(f"Content relevance evaluation failed: {e}")
            return 0.5