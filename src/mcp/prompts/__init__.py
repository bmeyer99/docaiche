"""
MCP Prompt Templates
===================

Pre-defined prompt templates for guided MCP interactions and
user assistance with documentation search and discovery.

Key Prompts:
- SearchPrompts: Guided search query construction
- TroubleshootingPrompts: Help and problem resolution
- ExamplePrompts: Usage examples and best practices
- OnboardingPrompts: New user guidance and tutorials

Prompts provide contextual assistance to help users effectively
utilize MCP tools and achieve better documentation discovery results.
"""

from .base_prompt import BasePrompt, PromptTemplate
from .search_prompts import SearchPrompts
from .troubleshooting_prompts import TroubleshootingPrompts
from .example_prompts import ExamplePrompts

__all__ = [
    'BasePrompt',
    'PromptTemplate',
    'SearchPrompts',
    'TroubleshootingPrompts',
    'ExamplePrompts'
]