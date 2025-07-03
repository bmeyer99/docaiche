"""
LLM Adapter for Text AI Service
================================

Adapter that connects the MCP TextAIService interface with the existing
LLM infrastructure, avoiding duplication while adding new capabilities.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import json

from .service import TextAIService
from .models import (
    QueryAnalysis, RelevanceEvaluation, ExternalSearchDecision, 
    ExternalSearchQuery, FormattedResponse
)
from .prompts import PromptType, PromptTemplate, DEFAULT_TEMPLATES
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
        
        # Initialize prompt templates
        self.prompt_templates = DEFAULT_TEMPLATES.copy()
        
        logger.info("TextAILLMAdapter initialized with existing LLM infrastructure and prompt templates")
    
    async def analyze_normalized_query(self, query: NormalizedQuery) -> QueryAnalysis:
        """
        Analyze query using LLM with QUERY_UNDERSTANDING prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.QUERY_UNDERSTANDING]
            
            # Prepare variables
            variables = {
                'query': query.original_query
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model for structured output
            from pydantic import BaseModel, Field
            from .models import QueryIntent, AnswerType
            
            class QueryAnalysisResponse(BaseModel):
                primary_intent: str = Field(description="Primary intent: information_seeking, problem_solving, how_to, etc.")
                technical_domain: Optional[str] = Field(description="Technical domain if applicable")
                expected_answer_type: str = Field(description="Expected answer type: explanation, code_example, reference, etc.")
                key_entities: List[str] = Field(default_factory=list, description="Key entities or concepts")
                search_scope: str = Field(description="Scope: specific technology or general knowledge")
                suggested_workspaces: List[str] = Field(default_factory=list, description="Suggested AnythingLLM workspaces")
            
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=QueryAnalysisResponse,
                temperature=0.3,
                max_tokens=500
            )
            
            logger.info(f"LLM query analysis completed in {int((time.time() - start_time) * 1000)}ms")
            
            # Map to QueryAnalysis model
            intent_map = {
                'information_seeking': QueryIntent.INFORMATION_SEEKING,
                'problem_solving': QueryIntent.PROBLEM_SOLVING,
                'how_to': QueryIntent.HOW_TO,
                'reference': QueryIntent.REFERENCE,
                'code_example': QueryIntent.CODE_EXAMPLE
            }
            
            answer_type_map = {
                'explanation': AnswerType.EXPLANATION,
                'code_example': AnswerType.CODE_EXAMPLE,
                'reference': AnswerType.REFERENCE,
                'tutorial': AnswerType.TUTORIAL,
                'definition': AnswerType.DEFINITION
            }
            
            return QueryAnalysis(
                primary_intent=intent_map.get(llm_response.primary_intent.lower(), QueryIntent.INFORMATION_SEEKING),
                technical_domain=llm_response.technical_domain or query.technology_hint,
                expected_answer_type=answer_type_map.get(llm_response.expected_answer_type.lower(), AnswerType.EXPLANATION),
                key_entities=llm_response.key_entities,
                search_scope=llm_response.search_scope,
                suggested_workspaces=llm_response.suggested_workspaces,
                confidence=0.8  # Higher confidence with LLM
            )
            
        except Exception as e:
            logger.error(f"LLM query analysis failed: {e}")
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
        Refine query using LLM with QUERY_REFINEMENT prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.QUERY_REFINEMENT]
            
            # Prepare results summary
            results_summary = f"Relevance: {evaluation.relevance_score:.2f}, Completeness: {evaluation.completeness_score:.2f}"
            
            # Prepare variables
            variables = {
                'original_query': query.original_query,
                'results_summary': results_summary,
                'missing_info': json.dumps(evaluation.missing_information) if evaluation.missing_information else "No specific gaps identified"
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Call LLM directly for text response
            start_time = time.time()
            refined_query = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=200
            )
            
            # Clean up the response (remove quotes if present)
            refined_query = refined_query.strip().strip('"\'')
            
            logger.info(f"LLM query refinement completed in {int((time.time() - start_time) * 1000)}ms: {refined_query}")
            
            return refined_query
            
        except Exception as e:
            logger.error(f"LLM query refinement failed: {e}")
            # Fallback to simple refinement
            refined = query.normalized_text
            
            # Add common refinements
            if "how" in refined.lower() and "tutorial" not in refined.lower():
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
        Generate query optimized for external search using LLM with EXTERNAL_SEARCH_QUERY prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.EXTERNAL_SEARCH_QUERY]
            
            # Prepare results summary
            results_summary = f"Found {evaluation.relevance_score:.0%} relevant results with {evaluation.completeness_score:.0%} completeness"
            
            # Prepare variables
            variables = {
                'original_query': query.original_query,
                'results_summary': results_summary,
                'missing_info': json.dumps(evaluation.missing_information) if evaluation.missing_information else "General information needed",
                'search_provider': 'web search'  # Generic, could be made specific later
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Call LLM directly for text response
            start_time = time.time()
            external_query = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=150
            )
            
            # Clean up the response
            external_query = external_query.strip().strip('"\'')
            
            logger.info(f"LLM external query generation completed in {int((time.time() - start_time) * 1000)}ms: {external_query}")
            
            return external_query
            
        except Exception as e:
            logger.error(f"LLM external query generation failed: {e}")
            # Fallback to simple enhancement
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
        Extract relevant content using LLM with CONTENT_EXTRACTION prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.CONTENT_EXTRACTION]
            
            # Combine top results for extraction
            combined_content = "\n\n---\n\n".join([
                f"Title: {r.title}\nURL: {r.url}\nContent:\n{r.content[:1000]}"
                for r in results.results[:3]  # Top 3 results
            ])
            
            # Prepare variables
            variables = {
                'original_query': query.original_query,
                'url': results.results[0].url if results.results else "N/A",
                'content_type': "documentation",
                'raw_content': combined_content
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model
            from pydantic import BaseModel, Field
            
            class ExtractedContent(BaseModel):
                summary: str = Field(description="Summary of relevant content")
                code_snippets: List[str] = Field(default_factory=list, description="Extracted code examples")
                key_points: List[str] = Field(default_factory=list, description="Key points or instructions")
                relevant_sections: str = Field(description="Most relevant content in Markdown format")
            
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=ExtractedContent,
                temperature=0.3,
                max_tokens=1500
            )
            
            logger.info(f"LLM content extraction completed in {int((time.time() - start_time) * 1000)}ms")
            
            # Build content dictionary
            content = {
                'summary': llm_response.summary,
                'code_snippets': llm_response.code_snippets,
                'key_points': llm_response.key_points,
                'citations': [
                    {
                        'title': r.title,
                        'url': r.url,
                        'relevance': r.relevance_score
                    }
                    for r in results.results[:5]
                ]
            }
            
            return content
            
        except Exception as e:
            logger.error(f"LLM content extraction failed: {e}")
            # Fallback to simple extraction
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
        content: Dict[str, Any],
        response_type: str = "answer"
    ) -> str:
        """
        Generate answer using LLM with RESPONSE_FORMAT prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.RESPONSE_FORMAT]
            
            # Prepare results JSON
            results_json = json.dumps({
                'summary': content.get('summary', ''),
                'code_snippets': content.get('code_snippets', [])[:3],
                'key_points': content.get('key_points', []),
                'citations': content.get('citations', [])[:3]
            }, indent=2)
            
            # Prepare variables
            variables = {
                'query': query.original_query,
                'response_type': response_type,
                'results_json': results_json
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Call LLM directly for markdown response
            start_time = time.time()
            formatted_answer = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000
            )
            
            logger.info(f"LLM answer generation completed in {int((time.time() - start_time) * 1000)}ms")
            
            return formatted_answer
            
        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            # Fallback to simple formatting
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
        evaluation: EvaluationResult,
        external_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps using LLM with LEARNING_OPPORTUNITIES prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.LEARNING_OPPORTUNITIES]
            
            # Prepare initial results summary
            initial_results = {
                'relevance_score': evaluation.relevance_score,
                'completeness_score': evaluation.completeness_score,
                'missing_information': evaluation.missing_information
            }
            
            # Prepare external results summary
            external_results_summary = []
            if external_results:
                for result in external_results[:5]:
                    external_results_summary.append({
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'snippet': result.get('snippet', '')[:200]
                    })
            
            # Prepare variables
            variables = {
                'query': query.original_query,
                'initial_results': json.dumps(initial_results, indent=2),
                'external_results': json.dumps(external_results_summary, indent=2) if external_results else "No external results",
                'final_response': "Not available for analysis"
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model
            from pydantic import BaseModel, Field
            
            class LearningOpportunity(BaseModel):
                topic: str = Field(description="Topic or knowledge area")
                reason: str = Field(description="Why this is a gap")
                priority: str = Field(description="Priority level: high/medium/low")
                suggested_sources: List[str] = Field(description="Suggested documentation sources")
                workspace_category: str = Field(description="Suggested workspace for this content")
            
            class LearningOpportunitiesResponse(BaseModel):
                knowledge_gaps: List[LearningOpportunity] = Field(description="Identified knowledge gaps")
                
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=LearningOpportunitiesResponse,
                temperature=0.5,
                max_tokens=800
            )
            
            logger.info(f"LLM learning opportunities analysis completed in {int((time.time() - start_time) * 1000)}ms")
            
            # Convert to expected format
            opportunities = []
            for gap in llm_response.knowledge_gaps:
                opportunities.append({
                    'topic': gap.topic,
                    'reason': gap.reason,
                    'priority': gap.priority,
                    'suggested_sources': gap.suggested_sources,
                    'workspace': gap.workspace_category
                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"LLM learning opportunities analysis failed: {e}")
            # Fallback to simple analysis
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
        available_providers: List[Dict[str, Any]],
        performance_stats: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Select best provider using LLM with PROVIDER_SELECTION prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.PROVIDER_SELECTION]
            
            # Prepare variables
            variables = {
                'query': query.original_query,
                'providers_json': json.dumps(available_providers, indent=2),
                'domain': query.technology_hint or 'general',
                'performance_stats': json.dumps(performance_stats, indent=2) if performance_stats else "{}"
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model
            from pydantic import BaseModel, Field
            
            class ProviderSelectionResponse(BaseModel):
                selected_provider: str = Field(description="ID of the selected provider")
                reasoning: str = Field(description="Explanation for the selection")
                query_complexity: str = Field(description="Query complexity: simple/moderate/complex")
                domain_match: str = Field(description="How well the provider matches the domain")
                
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=ProviderSelectionResponse,
                temperature=0.3,
                max_tokens=400
            )
            
            logger.info(f"LLM provider selection completed in {int((time.time() - start_time) * 1000)}ms: {llm_response.selected_provider}")
            
            # Validate the selected provider exists
            provider_ids = [p.get('id', p.get('type', '')) for p in available_providers]
            if llm_response.selected_provider in provider_ids:
                return llm_response.selected_provider
            else:
                logger.warning(f"LLM selected invalid provider {llm_response.selected_provider}, using first available")
                return provider_ids[0] if provider_ids else 'brave_search'
            
        except Exception as e:
            logger.error(f"LLM provider selection failed: {e}")
            # Fallback to simple selection
            if query.technology_hint in ['python', 'javascript', 'java']:
                # Prefer technical search engines
                for provider in available_providers:
                    if provider.get('type') in ['brave', 'google']:
                        return provider.get('id', provider.get('type'))
            
            # Default to first available
            return available_providers[0].get('id', available_providers[0].get('type')) if available_providers else 'brave_search'
    
    async def analyze_failure(
        self,
        query: NormalizedQuery,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze search failure using LLM with FAILURE_ANALYSIS prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.FAILURE_ANALYSIS]
            
            # Prepare vector results summary
            vector_results = context.get('vector_results', {})
            vector_summary = {
                'count': len(vector_results.get('results', [])),
                'avg_score': sum(r.get('relevance_score', 0) for r in vector_results.get('results', [])) / max(1, len(vector_results.get('results', [])))
            }
            
            # Prepare external attempts summary
            external_attempts = []
            if context.get('external_attempts'):
                for attempt in context.get('external_attempts', []):
                    external_attempts.append({
                        'provider': attempt.get('provider'),
                        'status': attempt.get('status'),
                        'error': str(attempt.get('error', ''))[:200]
                    })
            
            # Prepare variables
            variables = {
                'query': query.original_query,
                'vector_results': json.dumps(vector_summary, indent=2),
                'external_attempts': json.dumps(external_attempts, indent=2) if external_attempts else "No external search attempts",
                'errors': str(error)[:500]
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model
            from pydantic import BaseModel, Field
            
            class FailureAnalysisResponse(BaseModel):
                likely_reasons: List[str] = Field(description="Likely reasons for search failure")
                query_issues: str = Field(description="Whether query was malformed or ambiguous")
                missing_domains: List[str] = Field(description="Missing knowledge domains in our system")
                technical_limitations: List[str] = Field(description="Technical limitations encountered")
                system_improvements: List[str] = Field(description="Recommended system improvements")
                alternative_approaches: List[str] = Field(description="Alternative approaches for similar queries")
                
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=FailureAnalysisResponse,
                temperature=0.5,
                max_tokens=800
            )
            
            logger.info(f"LLM failure analysis completed in {int((time.time() - start_time) * 1000)}ms")
            
            # Generate user-friendly message
            user_message = "Search failed. "
            if llm_response.query_issues and 'ambiguous' in llm_response.query_issues:
                user_message += "Try making your query more specific. "
            elif llm_response.likely_reasons and 'timeout' in ' '.join(llm_response.likely_reasons).lower():
                user_message += "The search took too long. Try a simpler query. "
            else:
                user_message += "Please try again with a different query. "
            
            return {
                'cause': llm_response.likely_reasons[0] if llm_response.likely_reasons else 'unknown',
                'error_type': type(error).__name__,
                'likely_reasons': llm_response.likely_reasons,
                'query_issues': llm_response.query_issues,
                'missing_domains': llm_response.missing_domains,
                'technical_limitations': llm_response.technical_limitations,
                'suggestions': llm_response.system_improvements + llm_response.alternative_approaches,
                'user_message': user_message
            }
            
        except Exception as e:
            logger.error(f"LLM failure analysis failed: {e}")
            # Fallback to simple analysis
            error_type = type(error).__name__
            
            if "timeout" in str(error).lower():
                return {
                    'cause': 'timeout',
                    'error_type': error_type,
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
                    'error_type': error_type,
                    'suggestions': [
                        'Check network connection',
                        'Verify service availability'
                    ],
                    'user_message': 'Connection issue. Please try again.'
                }
            else:
                return {
                    'cause': 'unknown',
                    'error_type': error_type,
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
    
    async def decide_external_search(
        self, 
        query: NormalizedQuery, 
        evaluation: EvaluationResult
    ) -> ExternalSearchDecision:
        """
        Decide if external search is needed using LLM with EXTERNAL_SEARCH_DECISION prompt.
        """
        try:
            # Get prompt template
            template = self.prompt_templates[PromptType.EXTERNAL_SEARCH_DECISION]
            
            # Prepare results summary
            results_summary = {
                'relevance_score': evaluation.relevance_score,
                'completeness_score': evaluation.completeness_score,
                'confidence': evaluation.confidence,
                'has_results': evaluation.relevance_score > 0
            }
            
            # Prepare variables
            variables = {
                'original_query': query.original_query,
                'results_summary': json.dumps(results_summary, indent=2),
                'relevance_score': evaluation.relevance_score,
                'missing_info': json.dumps(evaluation.missing_information) if evaluation.missing_information else "[]"
            }
            
            # Render prompt
            prompt = template.format(**variables)
            
            # Define response model
            from pydantic import BaseModel, Field
            
            class ExternalSearchDecisionResponse(BaseModel):
                decision: bool = Field(description="True if external search is needed, False otherwise")
                reasoning: str = Field(description="Explanation for the decision")
                technical_topic: bool = Field(description="Is this a technical topic likely found in documentation?")
                recent_technology: bool = Field(description="Is the query about recent technologies or updates?")
                public_repos: bool = Field(description="Could the information exist in public repositories?")
                web_search_helpful: bool = Field(description="Is the answer likely to be found through web search?")
                significantly_better: bool = Field(description="Would external search provide significantly better results?")
            
            # Call LLM
            start_time = time.time()
            llm_response = await self.llm_client.generate_structured(
                prompt=prompt,
                response_model=ExternalSearchDecisionResponse,
                temperature=0.3,
                max_tokens=500
            )
            
            logger.info(f"LLM external search decision completed in {int((time.time() - start_time) * 1000)}ms: {llm_response.decision}")
            
            # Determine suggested providers based on analysis
            suggested_providers = []
            if llm_response.decision:
                if llm_response.technical_topic or llm_response.public_repos:
                    suggested_providers.extend(['brave_search', 'google_search'])
                if llm_response.recent_technology:
                    suggested_providers.append('brave_search')  # Good for recent tech
            
            return ExternalSearchDecision(
                should_search=llm_response.decision,
                reasoning=llm_response.reasoning,
                confidence=0.9 if llm_response.decision else 0.8,
                suggested_providers=suggested_providers
            )
            
        except Exception as e:
            logger.error(f"LLM external search decision failed: {e}")
            # Fallback to simple logic
            should_search = evaluation.relevance_score < 0.6 or evaluation.needs_external_search
            
            return ExternalSearchDecision(
                should_search=should_search,
                reasoning="Fallback decision based on relevance score" if should_search else "Adequate internal results",
                confidence=0.6,
                suggested_providers=['brave_search'] if should_search else []
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