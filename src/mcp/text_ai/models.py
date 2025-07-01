"""
Data Models for Text AI Service
================================

Response models for each of the 10 AI decision types.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class QueryIntent(str, Enum):
    """Types of query intents."""
    INFORMATION_SEEKING = "information_seeking"
    PROBLEM_SOLVING = "problem_solving"
    HOW_TO = "how_to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    DEBUGGING = "debugging"
    COMPARISON = "comparison"
    BEST_PRACTICES = "best_practices"
    OTHER = "other"


class AnswerType(str, Enum):
    """Expected answer types."""
    EXPLANATION = "explanation"
    CODE_EXAMPLE = "code_example"
    REFERENCE = "reference"
    TUTORIAL = "tutorial"
    DEFINITION = "definition"
    TROUBLESHOOTING = "troubleshooting"
    MIXED = "mixed"


class KnowledgePriority(str, Enum):
    """Priority levels for knowledge ingestion."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QueryAnalysis(BaseModel):
    """
    Response model for Query Understanding (Decision 1).
    
    Analyzes query intent, domain, entities, and suggests workspaces.
    """
    
    primary_intent: QueryIntent = Field(
        description="Identified primary intent of the query"
    )
    
    technical_domain: Optional[str] = Field(
        default=None,
        description="Technical domain if applicable (e.g., 'python', 'react', 'aws')"
    )
    
    expected_answer_type: AnswerType = Field(
        description="Type of answer expected by the user"
    )
    
    key_entities: List[str] = Field(
        default_factory=list,
        description="Key entities or concepts extracted from query"
    )
    
    search_scope: str = Field(
        description="Scope of search (specific technology, general knowledge, etc.)"
    )
    
    suggested_workspaces: List[str] = Field(
        default_factory=list,
        description="Suggested AnythingLLM workspaces to search"
    )
    
    confidence: float = Field(
        description="Confidence in analysis (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional analysis metadata"
    )


class RelevanceEvaluation(BaseModel):
    """
    Response model for Result Relevance Evaluation (Decision 2).
    
    Evaluates search result quality and completeness.
    """
    
    overall_relevance_score: float = Field(
        description="Overall relevance score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    directly_answers_query: bool = Field(
        description="Whether results directly answer the query"
    )
    
    contains_all_information: bool = Field(
        description="Whether results contain all necessary information"
    )
    
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of missing information elements"
    )
    
    refined_search_needed: bool = Field(
        description="Whether a refined search is recommended"
    )
    
    suggested_refinement: Optional[str] = Field(
        default=None,
        description="Suggested query refinement if needed"
    )
    
    result_quality_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Quality scores by aspect (relevance, completeness, clarity)"
    )
    
    confidence: float = Field(
        description="Confidence in evaluation (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class RefinedQuery(BaseModel):
    """
    Response model for Query Refinement (Decision 3).
    
    Contains refined query for better search results.
    """
    
    refined_query: str = Field(
        description="The refined search query"
    )
    
    refinement_strategy: str = Field(
        description="Strategy used for refinement (specificity, technical terms, etc.)"
    )
    
    added_terms: List[str] = Field(
        default_factory=list,
        description="Terms added to the query"
    )
    
    removed_terms: List[str] = Field(
        default_factory=list,
        description="Terms removed from the query"
    )
    
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Areas of focus for the refined query"
    )


class ExternalSearchDecision(BaseModel):
    """
    Response model for External Search Decision (Decision 4).
    
    Determines whether external search is needed.
    """
    
    use_external_search: bool = Field(
        description="Whether to use external search"
    )
    
    reasoning: str = Field(
        description="Reasoning for the decision"
    )
    
    technical_topic_likelihood: bool = Field(
        description="Whether this is likely a technical documentation topic"
    )
    
    recent_technology: bool = Field(
        description="Whether query is about recent technologies"
    )
    
    public_repository_likelihood: bool = Field(
        description="Whether information likely exists in public repos"
    )
    
    web_search_effectiveness: bool = Field(
        description="Whether web search would be effective"
    )
    
    expected_improvement: float = Field(
        description="Expected improvement from external search (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    recommended_providers: List[str] = Field(
        default_factory=list,
        description="Recommended external search providers"
    )


class ExternalSearchQuery(BaseModel):
    """
    Response model for External Search Query Generation (Decision 5).
    
    Optimized query for external search providers.
    """
    
    search_query: str = Field(
        description="Optimized query for external search"
    )
    
    provider_specific_queries: Dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific query variations"
    )
    
    exact_phrases: List[str] = Field(
        default_factory=list,
        description="Phrases that should be searched exactly (with quotes)"
    )
    
    required_terms: List[str] = Field(
        default_factory=list,
        description="Terms that must be in results"
    )
    
    excluded_terms: List[str] = Field(
        default_factory=list,
        description="Terms to exclude from results"
    )
    
    site_restrictions: List[str] = Field(
        default_factory=list,
        description="Specific sites to search (e.g., 'site:github.com')"
    )


class ExtractedContent(BaseModel):
    """
    Response model for Content Extraction (Decision 6).
    
    Relevant content extracted from documentation.
    """
    
    extracted_content: str = Field(
        description="Extracted relevant content in Markdown format"
    )
    
    content_sections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured sections of extracted content"
    )
    
    code_examples: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Code examples found with language tags"
    )
    
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisites or required knowledge"
    )
    
    reference_links: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Reference links to preserve"
    )
    
    relevance_score: float = Field(
        description="Relevance of extracted content (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class FormattedResponse(BaseModel):
    """
    Response model for Response Format Selection (Decision 7).
    
    Formatted response based on user preference.
    """
    
    formatted_response: str = Field(
        description="Formatted response in Markdown"
    )
    
    response_type: str = Field(
        description="Type of response generated (raw/answer)"
    )
    
    citations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Source citations included"
    )
    
    structure_type: str = Field(
        description="Structure used (sections, bullet points, narrative, etc.)"
    )
    
    includes_code: bool = Field(
        default=False,
        description="Whether response includes code examples"
    )
    
    completeness_score: float = Field(
        description="Completeness of the response (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class LearningOpportunities(BaseModel):
    """
    Response model for Learning Opportunity Identification (Decision 8).
    
    Identifies knowledge gaps for ingestion.
    """
    
    knowledge_gaps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Identified knowledge gaps with details"
    )
    
    topics_to_add: List[str] = Field(
        default_factory=list,
        description="Topics that should be added to knowledge base"
    )
    
    ingestion_priority: KnowledgePriority = Field(
        description="Overall priority for knowledge ingestion"
    )
    
    suggested_sources: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Suggested source documentation with URLs"
    )
    
    workspace_categorization: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Topics mapped to appropriate workspaces"
    )
    
    gap_severity: float = Field(
        description="Severity of knowledge gap (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    improvement_impact: float = Field(
        description="Expected improvement from filling gaps (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class ProviderSelection(BaseModel):
    """
    Response model for Search Provider Selection (Decision 9).
    
    Selects optimal search provider.
    """
    
    selected_provider: str = Field(
        description="Selected provider ID"
    )
    
    reasoning: str = Field(
        description="Reasoning for selection"
    )
    
    provider_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores for each available provider"
    )
    
    query_complexity: str = Field(
        description="Assessed query complexity (simple/moderate/complex)"
    )
    
    domain_match_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Domain match scores by provider"
    )
    
    rate_limit_considerations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rate limit status by provider"
    )
    
    fallback_providers: List[str] = Field(
        default_factory=list,
        description="Ordered list of fallback providers"
    )


class FailureAnalysis(BaseModel):
    """
    Response model for Search Failure Analysis (Decision 10).
    
    Analyzes failed searches for improvement.
    """
    
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="Identified reasons for search failure"
    )
    
    query_issues: List[str] = Field(
        default_factory=list,
        description="Issues with the query (malformed, ambiguous, etc.)"
    )
    
    missing_domains: List[str] = Field(
        default_factory=list,
        description="Knowledge domains missing from system"
    )
    
    technical_limitations: List[str] = Field(
        default_factory=list,
        description="Technical limitations encountered"
    )
    
    system_improvements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recommended system improvements"
    )
    
    alternative_approaches: List[str] = Field(
        default_factory=list,
        description="Alternative approaches for similar queries"
    )
    
    failure_severity: str = Field(
        description="Severity of failure (minor/moderate/severe)"
    )
    
    recovery_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for user to get results"
    )