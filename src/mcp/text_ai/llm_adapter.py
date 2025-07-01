"""
LLM Adapter for Text AI Service
================================

Adapter that connects the MCP TextAIService interface with the existing
LLM infrastructure, avoiding duplication while adding new capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
import json

from .service import TextAIService
from .models import (
    QueryAnalysis, RelevanceEvaluation, ExternalSearchDecision, 
    ExternalSearchQuery, FormattedResponse
)
from ..core.models import NormalizedQuery, VectorSearchResults, EvaluationResult
from src.llm.client import LLMProviderClient
from src.llm.models import (
    EvaluationResult as LLMEvaluationResult,
    EnrichmentStrategy,
    QualityAssessment
)
from src.search.llm_query_analyzer import LLMQueryAnalyzer

logger = logging.getLogger(__name__)


class TextAILLMAdapter(TextAIService):
    """
    Adapter that implements TextAIService interface using existing LLM infrastructure.
    
    This avoids duplication by reusing the existing LLM client and query analyzer
    while providing the MCP interface for new features.
    """
    
    def __init__(
        self,
        llm_client: LLMProviderClient,
        query_analyzer: Optional[LLMQueryAnalyzer] = None,
        model_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize adapter with existing LLM components.
        
        Args:
            llm_client: Existing LLM provider client
            query_analyzer: Existing query analyzer (optional)
            model_config: Additional configuration
        """
        super().__init__(model_config)
        self.llm_client = llm_client
        self.query_analyzer = query_analyzer
        logger.info("TextAILLMAdapter initialized with existing LLM infrastructure")
    
    async def analyze_normalized_query(self, query: NormalizedQuery) -> QueryAnalysis:
        """
        Analyze query using existing query analyzer if available.
        """
        if self.query_analyzer:
            try:
                # Use existing analyzer
                result = await self.query_analyzer.analyze(query.normalized_text)
                
                from .models import QueryIntent, AnswerType
                return QueryAnalysis(
                    primary_intent=QueryIntent.INFORMATION_SEEKING,
                    technical_domain=result.get('domain', 'general'),
                    expected_answer_type=AnswerType.EXPLANATION,
                    key_entities=result.get('entities', []),
                    search_scope=result.get('domain', 'general'),
                    suggested_workspaces=[],
                    confidence=result.get('confidence', 0.7)
                )
            except Exception as e:
                logger.error(f"Query analysis failed: {e}")
        
        # Fallback to simple analysis
        from .models import QueryIntent, AnswerType
        return QueryAnalysis(
            primary_intent=QueryIntent.INFORMATION_SEEKING,
            technical_domain=query.technology_hint,
            expected_answer_type=AnswerType.EXPLANATION,
            key_entities=self._extract_simple_entities(query.normalized_text),
            search_scope=query.technology_hint or 'general',
            suggested_workspaces=[],
            confidence=0.5
        )
    
    async def select_workspaces(
        self,
        query: NormalizedQuery,
        available_workspaces: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Select workspaces using simple logic for now.
        
        In the future, this can be enhanced with LLM-based selection.
        """
        selected = []
        
        # Technology-based selection
        if query.technology_hint:
            for ws in available_workspaces:
                if query.technology_hint in ws.get('technologies', []):
                    selected.append(ws['id'])
        
        # Add general workspaces
        for ws in available_workspaces:
            if ws['id'] not in selected and 'general' in ws.get('tags', []):
                selected.append(ws['id'])
                break
        
        # If none selected, use top priority workspaces
        if not selected:
            sorted_ws = sorted(
                available_workspaces,
                key=lambda w: w.get('priority', 0),
                reverse=True
            )
            selected = [ws['id'] for ws in sorted_ws[:3]]
        
        return selected[:5]  # Limit to 5 workspaces
    
    async def evaluate_results(
        self,
        query: NormalizedQuery,
        results: VectorSearchResults
    ) -> EvaluationResult:
        """
        Evaluate results using existing LLM evaluation if available.
        """
        try:
            # Convert to format expected by existing LLM client
            search_results = [
                {
                    'title': r.title,
                    'content': r.content,
                    'url': r.url,
                    'score': r.relevance_score
                }
                for r in results.results[:10]
            ]
            
            # Use existing evaluation
            llm_eval = self.llm_client.evaluate_search_results(
                query=query.normalized_text,
                results=search_results
            )
            
            # Convert to MCP format
            return EvaluationResult(
                relevance_score=llm_eval.avg_relevance_score,
                completeness_score=llm_eval.completeness_score,
                needs_refinement=llm_eval.avg_relevance_score < 0.6,
                needs_external_search=llm_eval.avg_relevance_score < 0.4,
                missing_information=llm_eval.missing_info or [],
                confidence=llm_eval.confidence_score
            )
            
        except Exception as e:
            logger.error(f"Result evaluation failed: {e}")
            # Fallback evaluation
            return self._simple_evaluation(results)
    
    async def refine_query(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> str:
        """
        Refine query based on evaluation.
        
        For now, uses simple expansion. Can be enhanced with LLM.
        """
        refined = query.normalized_text
        
        # Add common refinements
        if "how" in refined.lower() or "tutorial" not in refined.lower():
            refined += " tutorial"
        
        if "example" not in refined.lower():
            refined += " examples"
        
        # Add technology if specified
        if query.technology_hint and query.technology_hint not in refined:
            refined = f"{query.technology_hint} {refined}"
        
        return refined
    
    async def generate_external_query(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> str:
        """
        Generate query optimized for external search.
        """
        # For external search, be more specific
        external = query.normalized_text
        
        # Add technology context
        if query.technology_hint:
            external = f"{query.technology_hint} {external}"
        
        # Add search operators for better results
        if '"' not in external:
            # Quote important phrases
            words = external.split()
            if len(words) > 3:
                external = f'"{" ".join(words[:3])}" {" ".join(words[3:])}'
        
        return external
    
    async def extract_content(
        self,
        query: NormalizedQuery,
        results: VectorSearchResults
    ) -> Dict[str, Any]:
        """
        Extract relevant content from results.
        """
        content = {
            'summary': '',
            'code_snippets': [],
            'key_points': [],
            'citations': []
        }
        
        # Extract from top results
        for result in results.results[:5]:
            # Extract code snippets (simple pattern matching)
            code_blocks = self._extract_code_blocks(result.content)
            content['code_snippets'].extend(code_blocks[:2])  # Limit per result
            
            # Add citations
            content['citations'].append({
                'title': result.title,
                'url': result.url,
                'relevance': result.relevance_score
            })
        
        # Create summary from top result
        if results.results:
            content['summary'] = results.results[0].content[:500] + "..."
        
        return content
    
    async def generate_answer(
        self,
        query: NormalizedQuery,
        content: Dict[str, Any]
    ) -> str:
        """
        Generate answer from extracted content.
        """
        # For now, format the content nicely
        # In the future, use LLM for generation
        
        answer_parts = []
        
        # Add summary
        if content.get('summary'):
            answer_parts.append(content['summary'])
        
        # Add code examples if present
        if content.get('code_snippets'):
            answer_parts.append("\n**Code Examples:**")
            for i, snippet in enumerate(content['code_snippets'][:3]):
                answer_parts.append(f"\n```\n{snippet}\n```")
        
        # Add citations
        if content.get('citations'):
            answer_parts.append("\n**Sources:**")
            for citation in content['citations'][:5]:
                answer_parts.append(
                    f"- [{citation['title']}]({citation['url']}) "
                    f"(relevance: {citation['relevance']:.2f})"
                )
        
        return '\n'.join(answer_parts)
    
    async def identify_learning_opportunities(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps.
        """
        opportunities = []
        
        if evaluation.relevance_score < 0.5:
            opportunities.append({
                'topic': query.normalized_text,
                'reason': 'Low relevance results',
                'priority': 'high',
                'suggested_sources': ['official documentation', 'tutorials']
            })
        
        for missing in evaluation.missing_information:
            opportunities.append({
                'topic': missing,
                'reason': 'Missing information',
                'priority': 'medium',
                'suggested_sources': ['documentation', 'examples']
            })
        
        return opportunities
    
    async def select_provider(
        self,
        query: NormalizedQuery,
        available_providers: List[Dict[str, Any]]
    ) -> str:
        """
        Select best provider for query.
        """
        # Simple selection based on query type
        if query.technology_hint in ['python', 'javascript', 'java']:
            # Prefer technical search engines
            for provider in available_providers:
                if provider['type'] in ['brave', 'duckduckgo']:
                    return provider['id']
        
        # Default to first available
        return available_providers[0]['id'] if available_providers else 'brave_search'
    
    async def analyze_failure(
        self,
        query: NormalizedQuery,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze search failure.
        """
        error_type = type(error).__name__
        
        if "timeout" in str(error).lower():
            return {
                'cause': 'timeout',
                'suggestions': [
                    'Try a simpler query',
                    'Search fewer workspaces',
                    'Check system performance'
                ],
                'user_message': 'Search took too long. Try a simpler query.'
            }
        elif "connection" in str(error).lower():
            return {
                'cause': 'connection_error',
                'suggestions': [
                    'Check network connection',
                    'Verify service availability'
                ],
                'user_message': 'Connection issue. Please try again.'
            }
        else:
            return {
                'cause': 'unknown',
                'suggestions': ['Retry the search'],
                'user_message': 'An error occurred. Please try again.'
            }
    
    # Helper methods
    
    def _extract_simple_entities(self, text: str) -> List[str]:
        """Extract potential entities from text."""
        words = text.split()
        entities = []
        
        for word in words:
            # Technical terms with special characters
            if any(char in word for char in ['_', '-', '.', '/']):
                entities.append(word.lower())
            # Capitalized words (potential proper nouns)
            elif len(word) > 2 and word[0].isupper():
                entities.append(word.lower())
        
        return list(set(entities))
    
    def _simple_evaluation(self, results: VectorSearchResults) -> EvaluationResult:
        """Simple evaluation without LLM."""
        if not results.results:
            return EvaluationResult(
                relevance_score=0.0,
                completeness_score=0.0,
                needs_refinement=True,
                needs_external_search=True,
                missing_information=["No results found"],
                confidence=0.9
            )
        
        # Calculate average relevance
        avg_relevance = sum(r.relevance_score for r in results.results) / len(results.results)
        
        # Estimate completeness
        completeness = min(len(results.results) / 10, 1.0)
        
        return EvaluationResult(
            relevance_score=avg_relevance,
            completeness_score=completeness,
            needs_refinement=avg_relevance < 0.6,
            needs_external_search=completeness < 0.5,
            missing_information=[],
            confidence=0.7
        )
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract code blocks from content."""
        code_blocks = []
        
        # Look for markdown code blocks
        import re
        pattern = r'```[\w]*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        code_blocks.extend(matches)
        
        # Look for indented code blocks
        lines = content.split('\n')
        current_block = []
        for line in lines:
            if line.startswith('    '):  # 4 spaces = code block
                current_block.append(line[4:])
            elif current_block:
                if len(current_block) > 1:
                    code_blocks.append('\n'.join(current_block))
                current_block = []
        
        return code_blocks[:5]  # Limit number of blocks
    
    # Abstract method implementations for TextAIService
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query - delegates to the existing analyze_query method."""
        from ..core.models import NormalizedQuery
        norm_query = NormalizedQuery(
            original_query=query,
            normalized_text=query.lower().strip(),
            technology_hint=None,
            query_hash=str(hash(query)),
            tokens=query.split()
        )
        return await self.analyze_normalized_query(norm_query)
    
    async def evaluate_relevance(self, query: str, results: List[Dict[str, Any]]) -> RelevanceEvaluation:
        """Evaluate relevance of results."""
        
        # Simple relevance evaluation
        avg_score = sum(r.get('score', 0.5) for r in results) / max(len(results), 1)
        
        return RelevanceEvaluation(
            overall_relevance_score=avg_score,
            directly_answers_query=avg_score > 0.7,
            contains_all_information=avg_score > 0.8,
            missing_information=[] if avg_score > 0.8 else ["additional_examples"],
            refined_search_needed=avg_score < 0.6,
            confidence=0.8
        )
    
    async def decide_external_search(self, query: str, current_results: List[Dict[str, Any]]) -> ExternalSearchDecision:
        """Decide if external search is needed."""
        
        should_search = len(current_results) < 3 or all(r.get('score', 0) < 0.6 for r in current_results)
        
        return ExternalSearchDecision(
            should_search=should_search,
            reasoning="Insufficient internal results" if should_search else "Adequate internal results",
            confidence=0.8,
            suggested_providers=['brave_search', 'google_search'] if should_search else []
        )
    
    async def generate_search_query(self, original_query: str, context: Dict[str, Any]) -> ExternalSearchQuery:
        """Generate optimized search query."""
        
        # Enhance query with context
        enhanced = original_query
        if context.get('technology'):
            enhanced = f"{context['technology']} {enhanced}"
        
        return ExternalSearchQuery(
            query=enhanced,
            search_operators=['site:docs.python.org'] if 'python' in enhanced.lower() else [],
            filters={'language': 'en'},
            expected_result_types=['documentation', 'tutorial', 'example']
        )
    
    async def select_response_format(self, query: str, available_content: Dict[str, Any]) -> FormattedResponse:
        """Select appropriate response format."""
        
        # Simple format selection
        has_code = bool(available_content.get('code_snippets'))
        has_examples = 'example' in query.lower()
        
        format_type = 'code_example' if has_code and has_examples else 'explanation'
        
        return FormattedResponse(
            format_type=format_type,
            sections=['summary', 'details', 'examples'] if has_examples else ['summary', 'details'],
            include_citations=True,
            tone='technical' if has_code else 'informative'
        )