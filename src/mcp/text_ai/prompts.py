"""
Prompt Template Management for Text AI Service
==============================================

Manages all 10 decision prompt templates with version control
and variable validation.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import re
import json
from pydantic import BaseModel, Field, validator


class PromptType(str, Enum):
    """Types of prompts in the system."""
    QUERY_UNDERSTANDING = "query_understanding"
    RESULT_RELEVANCE = "result_relevance"
    QUERY_REFINEMENT = "query_refinement"
    EXTERNAL_SEARCH_DECISION = "external_search_decision"
    EXTERNAL_SEARCH_QUERY = "external_search_query"
    CONTENT_EXTRACTION = "content_extraction"
    RESPONSE_FORMAT = "response_format"
    LEARNING_OPPORTUNITIES = "learning_opportunities"
    PROVIDER_SELECTION = "provider_selection"
    FAILURE_ANALYSIS = "failure_analysis"


class PromptTemplate(BaseModel):
    """
    Individual prompt template with metadata.
    
    Contains the template text, required variables, and
    validation information.
    """
    
    id: str = Field(
        description="Unique template identifier"
    )
    
    type: PromptType = Field(
        description="Type of prompt template"
    )
    
    version: str = Field(
        description="Template version (e.g., '1.0.0')"
    )
    
    template_text: str = Field(
        description="The prompt template with {variable} placeholders"
    )
    
    required_variables: Set[str] = Field(
        default_factory=set,
        description="Required variable names for this template"
    )
    
    optional_variables: Set[str] = Field(
        default_factory=set,
        description="Optional variable names"
    )
    
    output_format: str = Field(
        default="json",
        description="Expected output format (json/text/markdown)"
    )
    
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for structured outputs"
    )
    
    temperature_recommendation: float = Field(
        default=0.3,
        description="Recommended temperature setting",
        ge=0.0,
        le=1.0
    )
    
    max_tokens_recommendation: int = Field(
        default=2000,
        description="Recommended max tokens for response"
    )
    
    active: bool = Field(
        default=True,
        description="Whether this template is active"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Template creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics for this template"
    )
    
    notes: str = Field(
        default="",
        description="Implementation notes or guidelines"
    )
    
    @validator('required_variables', 'optional_variables', pre=True)
    def extract_variables(cls, v, values):
        """Extract variables from template if not provided."""
        if v is None and 'template_text' in values:
            # Extract {variable} patterns from template
            pattern = r'\{(\w+)\}'
            return set(re.findall(pattern, values['template_text']))
        return v
    
    def validate_variables(self, provided_vars: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that all required variables are provided.
        
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        missing = self.required_variables - set(provided_vars.keys())
        return len(missing) == 0, list(missing)
    
    def render(self, variables: Dict[str, Any]) -> str:
        """
        Render the template with provided variables.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            Rendered prompt text
            
        Raises:
            ValueError: If required variables are missing
        """
        is_valid, missing = self.validate_variables(variables)
        if not is_valid:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Handle complex variable formatting
        formatted_vars = {}
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                formatted_vars[key] = json.dumps(value, indent=2)
            else:
                formatted_vars[key] = str(value)
        
        return self.template_text.format(**formatted_vars)


class TemplateVersion(BaseModel):
    """Version information for prompt templates."""
    
    version: str = Field(
        description="Version string (semantic versioning)"
    )
    
    template_id: str = Field(
        description="ID of the template"
    )
    
    changes: str = Field(
        description="Description of changes in this version"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    created_by: str = Field(
        default="system",
        description="User who created this version"
    )
    
    performance_baseline: Dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics for this version"
    )


class ValidationResult(BaseModel):
    """Result of template validation."""
    
    is_valid: bool = Field(
        description="Whether validation passed"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    
    variable_count: int = Field(
        default=0,
        description="Number of variables found"
    )
    
    estimated_tokens: int = Field(
        default=0,
        description="Estimated token count"
    )


# Default prompt templates from mcp_search_decision_prompts.md
DEFAULT_TEMPLATES = {
    PromptType.QUERY_UNDERSTANDING: '''Analyze the following query to determine search parameters:

Query: "{query}"

Please identify:
1. Primary intent (information seeking, problem solving, how-to, etc.)
2. Technical domain (if applicable)
3. Expected answer type (explanation, code example, reference, etc.)
4. Key entities or concepts
5. Scope of search (specific technology, general knowledge, etc.)
6. Suggested workspaces to search in AnythingLLM

Return your analysis in JSON format.''',

    PromptType.RESULT_RELEVANCE: '''Evaluate the relevance of these search results for the query:

Query: "{query}"

Search Results:
{results_json}

Please assess:
1. Overall relevance score (0-1)
2. Whether results directly answer the query (yes/no)
3. Whether results contain all necessary information (yes/no)
4. Missing information (if any)
5. Whether a refined search is needed (yes/no)
6. Suggested query refinement (if needed)

Return your evaluation in JSON format.''',

    PromptType.QUERY_REFINEMENT: '''The following query did not yield sufficiently relevant results:

Original Query: "{original_query}"
Search Results: {results_summary}
Missing Information: {missing_info}

Please generate a refined search query that:
1. Is more specific and targeted
2. Includes key technical terms
3. Focuses on the missing information
4. Is optimized for vector similarity search

Return only the refined query text.''',

    PromptType.EXTERNAL_SEARCH_DECISION: '''Determine if external search is needed based on:

Original Query: "{original_query}"
AnythingLLM Results: {results_summary}
Relevance Score: {relevance_score}
Missing Information: {missing_info}

Consider:
1. Is this a technical topic likely found in documentation? (yes/no)
2. Is the query about recent technologies or updates? (yes/no)
3. Could the information exist in public repositories? (yes/no)
4. Is the answer likely to be found through web search? (yes/no)
5. Would external search provide significantly better results? (yes/no)

Return your decision (true/false) and reasoning in JSON format.''',

    PromptType.EXTERNAL_SEARCH_QUERY: '''Generate an optimal external search query based on:

Original Query: "{original_query}"
Failed AnythingLLM Results: {results_summary}
Missing Information: {missing_info}

Please create a search query that:
1. Is formatted for web search engines
2. Contains specific technical terms
3. Uses quotes for exact phrases if appropriate
4. Includes version numbers or specific technologies
5. Is focused on documentation sources
6. Prioritizes GitHub or official documentation

Return only the search query text optimized for {search_provider}.''',

    PromptType.CONTENT_EXTRACTION: '''Extract the most relevant content from this documentation:

User Query: "{original_query}"
Source URL: {url}
Content Type: {content_type}

Document Content:
{raw_content}

Please:
1. Extract only sections directly relevant to the query
2. Preserve code examples if present
3. Maintain formatting for technical instructions
4. Include necessary context (e.g., prerequisites)
5. Remove irrelevant sections, navigation, etc.
6. Keep reference links intact

Return the extracted content in Markdown format.''',

    PromptType.RESPONSE_FORMAT: '''Format the search results based on user preferences:

Query: "{query}"
Response Type: "{response_type}" (raw/answer)
Search Results: {results_json}

If response_type is "raw":
- Provide the most relevant documentation sections
- Preserve formatting, especially for code
- Include source attribution

If response_type is "answer":
- Synthesize information into a direct answer
- Include code examples if applicable
- Cite sources
- Ensure completeness

Return the formatted response in Markdown.''',

    PromptType.LEARNING_OPPORTUNITIES: '''Analyze this search interaction to identify knowledge gaps:

Query: "{query}"
Initial AnythingLLM Results: {initial_results}
External Search Results: {external_results}
Final Response: {final_response}

Please identify:
1. Knowledge gaps in our AnythingLLM database
2. Topics that should be added to our knowledge base
3. Priority level for ingestion (high/medium/low)
4. Suggested source documentation
5. Workspace categorization

Return your analysis in JSON format for knowledge base improvement.''',

    PromptType.PROVIDER_SELECTION: '''Select the optimal search provider for this query:

Query: "{query}"
Available Providers: {providers_json}
Query Domain: {domain}
Previous Provider Performance: {performance_stats}

Please analyze:
1. Query type and complexity
2. Technical domain specificity
3. Provider strengths for this domain
4. Recent provider performance
5. Rate limit considerations

Return the selected provider ID and reasoning in JSON format.''',

    PromptType.FAILURE_ANALYSIS: '''Analyze this failed search to improve future performance:

Original Query: "{query}"
AnythingLLM Results: {vector_results}
External Search Attempts: {external_attempts}
Error Messages: {errors}

Please identify:
1. Likely reasons for search failure
2. Whether query was malformed or ambiguous
3. Missing knowledge domains in our system
4. Technical limitations encountered
5. Recommended system improvements
6. Alternative approaches for similar queries

Return your analysis in JSON format.'''
}


class PromptTemplateManager(ABC):
    """
    Abstract manager for prompt templates with version control.
    
    Handles template storage, retrieval, validation, and A/B testing.
    """
    
    @abstractmethod
    async def get_template(
        self, 
        prompt_type: PromptType,
        version: Optional[str] = None
    ) -> PromptTemplate:
        """
        Get a prompt template by type and version.
        
        Args:
            prompt_type: Type of prompt to retrieve
            version: Specific version (None = active version)
            
        Returns:
            PromptTemplate instance
        """
        pass
    
    @abstractmethod
    async def save_template(self, template: PromptTemplate) -> str:
        """
        Save a new template or update existing.
        
        Args:
            template: Template to save
            
        Returns:
            Template ID
        """
        pass
    
    @abstractmethod
    async def list_templates(
        self,
        prompt_type: Optional[PromptType] = None,
        active_only: bool = True
    ) -> List[PromptTemplate]:
        """
        List available templates.
        
        Args:
            prompt_type: Filter by type (None = all)
            active_only: Only return active templates
            
        Returns:
            List of templates
        """
        pass
    
    @abstractmethod
    async def get_versions(self, template_id: str) -> List[TemplateVersion]:
        """
        Get version history for a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            List of versions
        """
        pass
    
    @abstractmethod
    async def activate_version(self, template_id: str, version: str) -> None:
        """
        Activate a specific template version.
        
        Args:
            template_id: Template ID
            version: Version to activate
        """
        pass
    
    @abstractmethod
    async def validate_template(self, template: PromptTemplate) -> ValidationResult:
        """
        Validate a template for correctness.
        
        Args:
            template: Template to validate
            
        Returns:
            Validation result
        """
        pass
    
    @abstractmethod
    async def import_template(self, template_data: Dict[str, Any]) -> str:
        """
        Import a template from external format.
        
        Args:
            template_data: Template data dictionary
            
        Returns:
            Imported template ID
        """
        pass
    
    @abstractmethod
    async def export_template(self, template_id: str) -> Dict[str, Any]:
        """
        Export a template to external format.
        
        Args:
            template_id: Template to export
            
        Returns:
            Template data dictionary
        """
        pass
    
    @abstractmethod
    async def update_metrics(
        self,
        template_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Update performance metrics for a template.
        
        Args:
            template_id: Template ID
            metrics: Performance metrics to update
        """
        pass
    
    @abstractmethod
    async def get_ab_test_template(
        self,
        prompt_type: PromptType,
        user_id: str
    ) -> PromptTemplate:
        """
        Get template for A/B testing based on user assignment.
        
        Args:
            prompt_type: Type of prompt
            user_id: User ID for consistent assignment
            
        Returns:
            Assigned template for testing
        """
        pass
    
    def create_default_templates(self) -> Dict[PromptType, PromptTemplate]:
        """
        Create default templates from documentation.
        
        Returns:
            Dictionary of default templates by type
        """
        templates = {}
        
        for prompt_type, template_text in DEFAULT_TEMPLATES.items():
            # Extract variables from template
            variables = set(re.findall(r'\{(\w+)\}', template_text))
            
            template = PromptTemplate(
                id=f"default_{prompt_type.value}",
                type=prompt_type,
                version="1.0.0",
                template_text=template_text,
                required_variables=variables,
                output_format="json" if "JSON" in template_text else "text",
                temperature_recommendation=0.3 if prompt_type in [
                    PromptType.QUERY_UNDERSTANDING,
                    PromptType.RESULT_RELEVANCE,
                    PromptType.EXTERNAL_SEARCH_DECISION,
                    PromptType.PROVIDER_SELECTION,
                    PromptType.FAILURE_ANALYSIS
                ] else 0.7,
                notes=f"Default template from mcp_search_decision_prompts.md"
            )
            
            templates[prompt_type] = template
        
        return templates