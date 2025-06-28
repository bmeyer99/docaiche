"""
LLM Source Finder - Dynamic Documentation Discovery
Uses LLMs to find the best documentation sources for a given technology
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.llm.client import LLMProviderClient
from src.search.llm_query_analyzer import QueryIntent

logger = logging.getLogger(__name__)


class DocumentationSource(BaseModel):
    """Represents a documentation source"""
    name: str = Field(..., description="Source name (e.g., 'FastAPI Official Docs')")
    url: str = Field(..., description="Direct URL to documentation")
    source_type: str = Field(..., description="Type: github, official, or community")
    format: str = Field(..., description="Format: markdown, html, or pdf")
    quality_score: float = Field(0.8, description="Quality score from 0.0 to 1.0")
    specific_path: Optional[str] = Field(None, description="Specific path within the source")
    version_specific: bool = Field(False, description="Whether this is version-specific")


class LLMSourceFinder:
    """Finds documentation sources using LLM intelligence"""
    
    def __init__(self, llm_client: LLMProviderClient):
        self.llm = llm_client
        
    async def find_sources(self, intent: QueryIntent) -> List[DocumentationSource]:
        """
        Find documentation sources based on query intent
        
        Args:
            intent: Analyzed query intent
            
        Returns:
            List of documentation sources ranked by relevance
        """
        try:
            version_str = f"version {intent.version}" if intent.version else "latest version"
            topics_str = ', '.join(intent.topics) if intent.topics else "general"
            
            prompt = f"""
            Find the best documentation sources for {intent.technology} {version_str}
            focusing on {intent.doc_type} documentation about {topics_str}.
            User level: {intent.user_level}
            
            Return a JSON array of documentation sources with:
            - name: descriptive source name
            - url: direct URL to documentation (must be a real, valid URL)
            - source_type: one of "github", "official", or "community"
            - format: one of "markdown", "html", or "pdf"
            - quality_score: 0.0 to 1.0 based on relevance and quality
            - specific_path: optional path within the source for specific topics
            - version_specific: boolean indicating if this is for a specific version
            
            Prioritize:
            1. Official documentation sites
            2. GitHub repositories with good documentation
            3. High-quality community resources
            
            For GitHub sources, prefer direct links to docs folders or specific markdown files.
            
            Example response:
            [
                {{
                    "name": "FastAPI Official Documentation",
                    "url": "https://fastapi.tiangolo.com",
                    "source_type": "official",
                    "format": "html",
                    "quality_score": 0.95,
                    "specific_path": "/tutorial/async",
                    "version_specific": false
                }},
                {{
                    "name": "FastAPI GitHub Repository",
                    "url": "https://github.com/tiangolo/fastapi",
                    "source_type": "github",
                    "format": "markdown",
                    "quality_score": 0.90,
                    "specific_path": "/docs/en/docs/tutorial",
                    "version_specific": false
                }}
            ]
            
            Find at least 3 sources. Return ONLY the JSON array.
            """
            
            response = await self.llm.generate(prompt)
            
            # Parse response
            try:
                # Clean response
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                sources_data = json.loads(cleaned_response.strip())
                
                # Validate and create DocumentationSource objects
                sources = []
                for source_data in sources_data:
                    # Validate required fields
                    if not source_data.get("url"):
                        continue
                        
                    # Normalize source_type
                    source_type = source_data.get("source_type", "community").lower()
                    if source_type not in ["github", "official", "community"]:
                        source_type = "community"
                    source_data["source_type"] = source_type
                    
                    # Normalize format
                    format_type = source_data.get("format", "html").lower()
                    if format_type not in ["markdown", "html", "pdf"]:
                        format_type = "html"
                    source_data["format"] = format_type
                    
                    # Ensure quality score is valid
                    quality_score = float(source_data.get("quality_score", 0.8))
                    source_data["quality_score"] = max(0.0, min(1.0, quality_score))
                    
                    sources.append(DocumentationSource(**source_data))
                
                # Sort by quality score
                sources.sort(key=lambda x: x.quality_score, reverse=True)
                
                return sources[:5]  # Return top 5 sources
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse source finder response: {e}")
                logger.debug(f"LLM response: {response}")
                return self._get_fallback_sources(intent)
                
        except Exception as e:
            logger.error(f"Source discovery failed: {e}")
            return self._get_fallback_sources(intent)
    
    def _get_fallback_sources(self, intent: QueryIntent) -> List[DocumentationSource]:
        """
        Fallback method to return common documentation sources
        """
        tech = intent.technology.lower()
        
        # Common documentation patterns
        sources = []
        
        # Try official docs
        if tech in ["python", "javascript", "typescript", "rust", "go"]:
            sources.append(DocumentationSource(
                name=f"{intent.technology.title()} Official Documentation",
                url=f"https://docs.{tech}.org" if tech == "python" else f"https://{tech}lang.org/docs",
                source_type="official",
                format="html",
                quality_score=0.9
            ))
        
        # Try GitHub
        github_repos = {
            "fastapi": "tiangolo/fastapi",
            "django": "django/django",
            "react": "facebook/react",
            "vue": "vuejs/vue",
            "angular": "angular/angular",
            "flask": "pallets/flask",
            "express": "expressjs/express"
        }
        
        if tech in github_repos:
            sources.append(DocumentationSource(
                name=f"{intent.technology.title()} GitHub Repository",
                url=f"https://github.com/{github_repos[tech]}",
                source_type="github",
                format="markdown",
                quality_score=0.85,
                specific_path="/docs"
            ))
        
        # Add generic community source
        sources.append(DocumentationSource(
            name=f"{intent.technology.title()} Community Resources",
            url=f"https://github.com/search?q={tech}+documentation",
            source_type="community",
            format="html",
            quality_score=0.6
        ))
        
        return sources
    
    async def evaluate_source_quality(self, source: DocumentationSource, intent: QueryIntent) -> float:
        """
        Evaluate the quality of a documentation source for a specific intent
        
        Args:
            source: Documentation source to evaluate
            intent: Query intent to match against
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        try:
            prompt = f"""
            Evaluate this documentation source for the given search intent.
            
            Source:
            - Name: {source.name}
            - URL: {source.url}
            - Type: {source.source_type}
            - Format: {source.format}
            
            Search Intent:
            - Technology: {intent.technology}
            - Topics: {', '.join(intent.topics)}
            - Doc Type: {intent.doc_type}
            - User Level: {intent.user_level}
            
            Rate the source quality from 0.0 to 1.0 based on:
            1. Relevance to the search topics
            2. Appropriateness for the user level
            3. Documentation completeness
            4. Update frequency and maintenance
            5. Community trust and usage
            
            Return ONLY a number between 0.0 and 1.0
            """
            
            response = await self.llm.generate(prompt)
            
            try:
                score = float(response.strip())
                return max(0.0, min(1.0, score))
            except ValueError:
                return source.quality_score  # Use existing score if parsing fails
                
        except Exception as e:
            logger.error(f"Source evaluation failed: {e}")
            return source.quality_score