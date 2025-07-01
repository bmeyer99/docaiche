"""
Text AI Service Abstract Interface
==================================

Abstract base class for AI-powered decision-making throughout
the MCP search workflow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import logging

from ..core.models import NormalizedQuery, VectorSearchResults, EvaluationResult
from .models import (
    QueryAnalysis,
    RelevanceEvaluation,
    RefinedQuery,
    ExternalSearchDecision,
    ExternalSearchQuery,
    ExtractedContent,
    FormattedResponse,
    LearningOpportunities,
    ProviderSelection,
    FailureAnalysis
)
from .prompts import PromptType, PromptTemplate

logger = logging.getLogger(__name__)


class TextAIService(ABC):
    """
    Abstract interface for Text AI decision-making service.
    
    Provides intelligent analysis and decision-making at 10 key points
    in the search workflow using configurable AI models and prompts.
    """
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Text AI service.
        
        Args:
            model_config: Configuration for AI model (provider, settings, etc.)
        """
        self.model_config = model_config or {}
        logger.info("TextAIService initialized with model config")
    
    @abstractmethod
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query to determine intent, domain, and search strategy.
        
        Decision Point 1: Query Understanding
        - Identifies primary intent and technical domain
        - Extracts key entities and concepts
        - Suggests relevant workspaces for search
        
        Args:
            query: Raw search query from user
            
        Returns:
            QueryAnalysis with intent, domain, entities, and suggestions
            
        Raises:
            TextAIError: If analysis fails
        """
        pass
    
    @abstractmethod
    async def evaluate_relevance(
        self,
        query: str,
        results: VectorSearchResults
    ) -> RelevanceEvaluation:
        """
        Evaluate relevance and completeness of search results.
        
        Decision Point 2: Result Relevance Evaluation
        - Scores overall relevance (0-1)
        - Determines if results answer the query
        - Identifies missing information
        - Recommends refinement if needed
        
        Args:
            query: Original search query
            results: Vector search results to evaluate
            
        Returns:
            RelevanceEvaluation with scores and recommendations
            
        Raises:
            TextAIError: If evaluation fails
        """
        pass
    
    @abstractmethod
    async def refine_query(
        self,
        original_query: str,
        results_summary: Dict[str, Any],
        missing_info: List[str]
    ) -> RefinedQuery:
        """
        Generate refined query when initial results are insufficient.
        
        Decision Point 3: Query Refinement
        - Creates more specific and targeted query
        - Adds key technical terms
        - Focuses on missing information
        - Optimizes for vector similarity
        
        Args:
            original_query: Initial query that yielded poor results
            results_summary: Summary of insufficient results
            missing_info: List of missing information elements
            
        Returns:
            RefinedQuery with improved query text
            
        Raises:
            TextAIError: If refinement fails
        """
        pass
    
    @abstractmethod
    async def decide_external_search(
        self,
        query: str,
        results_summary: Dict[str, Any],
        relevance_score: float,
        missing_info: List[str]
    ) -> ExternalSearchDecision:
        """
        Determine if external search providers should be used.
        
        Decision Point 4: External Search Decision
        - Analyzes if topic needs external documentation
        - Considers recency of technology
        - Estimates improvement from external search
        - Recommends specific providers
        
        Args:
            query: Original search query
            results_summary: Summary of AnythingLLM results
            relevance_score: Overall relevance score
            missing_info: Missing information list
            
        Returns:
            ExternalSearchDecision with boolean decision and reasoning
            
        Raises:
            TextAIError: If decision fails
        """
        pass
    
    @abstractmethod
    async def generate_search_query(
        self,
        original_query: str,
        results_summary: Dict[str, Any],
        missing_info: List[str],
        search_provider: str
    ) -> ExternalSearchQuery:
        """
        Generate optimized query for external search provider.
        
        Decision Point 5: External Search Query Generation
        - Formats query for web search engines
        - Adds quotes for exact phrases
        - Includes version numbers and technologies
        - Optimizes for specific provider
        
        Args:
            original_query: Original user query
            results_summary: Failed AnythingLLM results
            missing_info: What information is missing
            search_provider: Target search provider
            
        Returns:
            ExternalSearchQuery optimized for provider
            
        Raises:
            TextAIError: If generation fails
        """
        pass
    
    @abstractmethod
    async def extract_content(
        self,
        query: str,
        url: str,
        content_type: str,
        raw_content: str
    ) -> ExtractedContent:
        """
        Extract relevant content from external documentation.
        
        Decision Point 6: Content Extraction
        - Extracts only relevant sections
        - Preserves code examples
        - Maintains technical formatting
        - Includes necessary context
        - Removes irrelevant content
        
        Args:
            query: Original user query
            url: Source URL of content
            content_type: Type of content (docs, tutorial, etc.)
            raw_content: Raw document content
            
        Returns:
            ExtractedContent with relevant sections in Markdown
            
        Raises:
            TextAIError: If extraction fails
        """
        pass
    
    @abstractmethod
    async def select_response_format(
        self,
        query: str,
        response_type: str,
        results: VectorSearchResults
    ) -> FormattedResponse:
        """
        Format response based on user preference and query type.
        
        Decision Point 7: Response Format Selection
        - Handles "raw" vs "answer" response types
        - Synthesizes information for answers
        - Preserves formatting for raw responses
        - Includes proper citations
        
        Args:
            query: Original query
            response_type: Requested format (raw/answer)
            results: Search results to format
            
        Returns:
            FormattedResponse in appropriate format
            
        Raises:
            TextAIError: If formatting fails
        """
        pass
    
    @abstractmethod
    async def identify_learning_opportunities(
        self,
        query: str,
        initial_results: Dict[str, Any],
        external_results: Optional[Dict[str, Any]],
        final_response: str
    ) -> LearningOpportunities:
        """
        Identify knowledge gaps for future ingestion.
        
        Decision Point 8: Learning Opportunity Identification
        - Finds gaps in AnythingLLM knowledge base
        - Identifies topics to add
        - Sets ingestion priorities
        - Suggests source documentation
        - Maps to appropriate workspaces
        
        Args:
            query: Original search query
            initial_results: Initial AnythingLLM results
            external_results: External search results if used
            final_response: Final response sent to user
            
        Returns:
            LearningOpportunities with gaps and priorities
            
        Raises:
            TextAIError: If identification fails
        """
        pass
    
    @abstractmethod
    async def select_provider(
        self,
        query: str,
        providers: List[Dict[str, Any]],
        domain: Optional[str],
        performance_stats: Dict[str, Any]
    ) -> ProviderSelection:
        """
        Select optimal external search provider.
        
        Decision Point 9: Search Provider Selection
        - Analyzes query complexity
        - Matches provider strengths to domain
        - Considers rate limits
        - Uses performance history
        - Provides fallback order
        
        Args:
            query: Search query
            providers: Available provider configurations
            domain: Technical domain if identified
            performance_stats: Historical performance data
            
        Returns:
            ProviderSelection with chosen provider and reasoning
            
        Raises:
            TextAIError: If selection fails
        """
        pass
    
    @abstractmethod
    async def analyze_failure(
        self,
        query: str,
        vector_results: Optional[Dict[str, Any]],
        external_attempts: List[Dict[str, Any]],
        errors: List[str]
    ) -> FailureAnalysis:
        """
        Analyze failed search to improve future performance.
        
        Decision Point 10: Search Failure Analysis
        - Identifies failure reasons
        - Detects query issues
        - Finds missing knowledge domains
        - Suggests system improvements
        - Provides alternative approaches
        
        Args:
            query: Original failed query
            vector_results: AnythingLLM results if any
            external_attempts: List of external search attempts
            errors: Error messages encountered
            
        Returns:
            FailureAnalysis with insights and recommendations
            
        Raises:
            TextAIError: If analysis fails
        """
        pass
    
    # Helper methods that can be overridden or extended
    
    async def _prepare_results_summary(
        self,
        results: VectorSearchResults
    ) -> Dict[str, Any]:
        """
        Prepare results summary for AI analysis.
        
        Default implementation that can be overridden.
        
        Args:
            results: Search results to summarize
            
        Returns:
            Dictionary summary suitable for prompts
        """
        summary = {
            "total_results": results.total_count,
            "workspaces_searched": results.workspaces_searched,
            "top_results": []
        }
        
        # Include top 5 results
        for i, result in enumerate(results.results[:5]):
            summary["top_results"].append({
                "title": result.title,
                "snippet": result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet,
                "relevance_score": result.relevance_score,
                "workspace": result.workspace,
                "content_type": result.content_type.value
            })
        
        return summary
    
    async def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Simple estimation - can be overridden with model-specific counting.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    async def _truncate_content(
        self,
        content: str,
        max_tokens: int = 3000
    ) -> str:
        """
        Truncate content to fit within token limits.
        
        Args:
            content: Content to truncate
            max_tokens: Maximum token limit
            
        Returns:
            Truncated content
        """
        estimated_tokens = await self._estimate_token_count(content)
        if estimated_tokens <= max_tokens:
            return content
        
        # Truncate to approximately fit
        char_limit = max_tokens * 4
        return content[:char_limit] + "\n\n[Content truncated...]"
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from AI response text.
        
        Handles responses that include explanation text around JSON.
        
        Args:
            response: AI response text
            
        Returns:
            Extracted JSON as dictionary
            
        Raises:
            ValueError: If no valid JSON found
        """
        import json
        
        # Try direct parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
        
        # Look for JSON-like content between braces
        brace_pattern = r'\{[^{}]*\}'
        matches = re.findall(brace_pattern, response)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        raise ValueError("No valid JSON found in response")