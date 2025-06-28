"""
LLM Query Analyzer - Intelligent Query Understanding
Uses LLMs to extract intent, technology, and context from search queries
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.llm.client import LLMProviderClient
from src.core.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class QueryIntent(BaseModel):
    """Structured representation of user query intent"""
    technology: str = Field(..., description="Main technology/framework being searched")
    version: Optional[str] = Field(None, description="Specific version if mentioned")
    doc_type: str = Field(..., description="Type of documentation: tutorial, reference, or guide")
    topics: List[str] = Field(default_factory=list, description="Specific topics mentioned")
    user_level: str = Field("intermediate", description="User expertise: beginner, intermediate, or advanced")
    related_technologies: List[str] = Field(default_factory=list, description="Related technologies that might be relevant")


class LLMQueryAnalyzer:
    """Analyzes search queries using LLM to extract structured intent"""
    
    def __init__(self, llm_client: LLMProviderClient):
        self.llm = llm_client
        
    async def analyze_query(self, query: str) -> QueryIntent:
        """
        Analyze a search query to extract intent and context
        
        Args:
            query: The user's search query
            
        Returns:
            QueryIntent object with extracted information
        """
        try:
            prompt = f"""
            Analyze this documentation search query: "{query}"
            
            Extract and return as JSON:
            - technology: main technology/framework (e.g., "fastapi", "react", "django")
            - version: version if specified (null if not mentioned)
            - doc_type: one of "tutorial", "reference", or "guide"
            - topics: list of specific topics mentioned (e.g., ["async", "authentication", "routing"])
            - user_level: "beginner", "intermediate", or "advanced" (infer from query)
            - related_technologies: other technologies that might have relevant docs
            
            Examples:
            Query: "fastapi async tutorial for beginners"
            {{
                "technology": "fastapi",
                "version": null,
                "doc_type": "tutorial",
                "topics": ["async", "asynchronous programming"],
                "user_level": "beginner",
                "related_technologies": ["python", "asyncio", "starlette"]
            }}
            
            Query: "React 18 hooks comprehensive guide"
            {{
                "technology": "react",
                "version": "18",
                "doc_type": "guide",
                "topics": ["hooks", "state management"],
                "user_level": "intermediate",
                "related_technologies": ["javascript", "typescript", "redux"]
            }}
            
            Query: "Django REST framework authentication API reference"
            {{
                "technology": "django",
                "version": null,
                "doc_type": "reference",
                "topics": ["rest framework", "authentication", "api"],
                "user_level": "advanced",
                "related_technologies": ["python", "django-rest-framework", "oauth"]
            }}
            
            Analyze the query and return ONLY valid JSON matching the structure above.
            """
            
            # Generate response from LLM
            response = await self.llm.generate(prompt)
            
            # Parse JSON response
            try:
                # Clean response - remove any markdown formatting
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                intent_data = json.loads(cleaned_response.strip())
                
                # Validate and normalize data
                intent_data["doc_type"] = intent_data.get("doc_type", "guide").lower()
                if intent_data["doc_type"] not in ["tutorial", "reference", "guide"]:
                    intent_data["doc_type"] = "guide"
                    
                intent_data["user_level"] = intent_data.get("user_level", "intermediate").lower()
                if intent_data["user_level"] not in ["beginner", "intermediate", "advanced"]:
                    intent_data["user_level"] = "intermediate"
                
                # Ensure lists are lists
                if not isinstance(intent_data.get("topics"), list):
                    intent_data["topics"] = []
                if not isinstance(intent_data.get("related_technologies"), list):
                    intent_data["related_technologies"] = []
                
                return QueryIntent(**intent_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"LLM response: {response}")
                # Fallback to basic extraction
                return self._fallback_extraction(query)
                
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Return a basic intent based on simple parsing
            return self._fallback_extraction(query)
    
    def _fallback_extraction(self, query: str) -> QueryIntent:
        """
        Fallback method for basic query intent extraction
        """
        query_lower = query.lower()
        
        # Try to identify technology
        technologies = ["python", "javascript", "react", "vue", "angular", "django", 
                       "fastapi", "flask", "nodejs", "typescript", "java", "spring",
                       "rust", "go", "kubernetes", "docker", "aws", "azure"]
        
        detected_tech = "general"
        for tech in technologies:
            if tech in query_lower:
                detected_tech = tech
                break
        
        # Detect doc type
        doc_type = "guide"
        if "tutorial" in query_lower:
            doc_type = "tutorial"
        elif "reference" in query_lower or "api" in query_lower:
            doc_type = "reference"
        
        # Detect user level
        user_level = "intermediate"
        if "beginner" in query_lower or "basic" in query_lower or "getting started" in query_lower:
            user_level = "beginner"
        elif "advanced" in query_lower or "expert" in query_lower:
            user_level = "advanced"
        
        # Extract topics (simple word extraction)
        words = query_lower.split()
        topics = [word for word in words if len(word) > 4 and word not in 
                 ["tutorial", "guide", "reference", "documentation", "docs", "beginner", "advanced"]]
        
        return QueryIntent(
            technology=detected_tech,
            version=None,
            doc_type=doc_type,
            topics=topics[:5],  # Limit topics
            user_level=user_level,
            related_technologies=[]
        )
    
    async def enhance_query(self, query: str, intent: QueryIntent) -> str:
        """
        Enhance the original query based on extracted intent
        
        Args:
            query: Original search query
            intent: Extracted query intent
            
        Returns:
            Enhanced query string
        """
        try:
            prompt = f"""
            Enhance this documentation search query for better results.
            
            Original query: "{query}"
            
            Extracted intent:
            - Technology: {intent.technology}
            - Topics: {', '.join(intent.topics)}
            - User level: {intent.user_level}
            - Doc type: {intent.doc_type}
            
            Create an enhanced search query that:
            1. Includes relevant synonyms and related terms
            2. Adds technical context
            3. Maintains the original intent
            4. Is optimized for vector search
            
            Return ONLY the enhanced query string, nothing else.
            """
            
            enhanced = await self.llm.generate(prompt)
            return enhanced.strip()
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {e}")
            # Return original query if enhancement fails
            return query