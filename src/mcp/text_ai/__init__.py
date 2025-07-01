"""
Text AI Service Module
======================

AI-powered decision-making service for the MCP search system.
Provides intelligent analysis and decision-making at various
points in the search workflow.
"""

from .service import TextAIService
from .prompts import PromptTemplateManager
from .models import (
    QueryAnalysis,
    ExternalSearchDecision,
    ExtractedContent,
    FormattedResponse,
    LearningOpportunities,
    FailureAnalysis
)

__all__ = [
    "TextAIService",
    "PromptTemplateManager",
    "QueryAnalysis",
    "ExternalSearchDecision",
    "ExtractedContent",
    "FormattedResponse",
    "LearningOpportunities",
    "FailureAnalysis"
]