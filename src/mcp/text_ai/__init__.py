"""
Text AI Service Module
======================

AI-powered decision-making service for the MCP search system.
Provides intelligent analysis and decision-making at various
points in the search workflow.
"""

from .service import TextAIService
from .prompts import PromptTemplateManager, PromptTemplate, PromptType
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
from .ab_testing import (
    ABTestingFramework,
    ABTest,
    TestVariant,
    TestStatus,
    StatisticalResult,
    ABTestConfigForUI
)

__all__ = [
    # Service
    "TextAIService",
    
    # Prompt Management
    "PromptTemplateManager",
    "PromptTemplate",
    "PromptType",
    
    # Decision Models
    "QueryAnalysis",
    "RelevanceEvaluation", 
    "RefinedQuery",
    "ExternalSearchDecision",
    "ExternalSearchQuery",
    "ExtractedContent",
    "FormattedResponse",
    "LearningOpportunities",
    "ProviderSelection",
    "FailureAnalysis",
    
    # A/B Testing
    "ABTestingFramework",
    "ABTest",
    "TestVariant",
    "TestStatus",
    "StatisticalResult",
    "ABTestConfigForUI"
]