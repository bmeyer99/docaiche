"""ResponseGenerator: Main entry point for intelligent response generation (PRD-011).

Handles orchestration of response building, formatting, and validation.
Integrates with SearchOrchestrator (PRD-009), KnowledgeEnricher (PRD-010), and LLMProviderClient (PRD-005).
"""

from typing import Any, Dict, Optional
from src.response.builder import ResponseBuilder
from src.response.template_engine import TemplateEngine
from src.response.content_synthesizer import ContentSynthesizer
from src.response.formatter import ResponseFormatter
from src.response.validator import ResponseValidator
from src.response.exceptions import ResponseGenerationError, TemplateNotFoundError, TemplateRenderError
import logging

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Coordinates the full response generation workflow.

    Dependencies are injected for modularity and testability.

    Args:
        builder: ResponseBuilder instance for constructing responses
        template_engine: TemplateEngine for formatting and rendering
        synthesizer: ContentSynthesizer for combining search and enrichment
        formatter: ResponseFormatter for output format handling
        validator: ResponseValidator for quality checks

    Integration Points:
        - PRD-009: Accepts search results from SearchOrchestrator
        - PRD-010: Integrates enriched content from KnowledgeEnricher
        - PRD-005: Optionally enhances responses with LLMProviderClient

    Methods:
        generate_response: Main async method to generate a response

    Raises:
        ResponseGenerationError: On unrecoverable response generation failure
    """

    def __init__(
        self,
        builder: ResponseBuilder,
        template_engine: TemplateEngine,
        synthesizer: ContentSynthesizer,
        formatter: ResponseFormatter,
        validator: ResponseValidator,
    ):
        self.builder = builder
        self.template_engine = template_engine
        self.synthesizer = synthesizer
        self.formatter = formatter
        self.validator = validator
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def generate_response(
        self,
        query: str,
        search_results: Any,
        enriched_content: Optional[Any] = None,
        output_format: str = "json",
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Generate a structured response for a given query.

        Args:
            query: User query string
            search_results: Results from SearchOrchestrator
            enriched_content: Optional content from KnowledgeEnricher
            output_format: Desired output format (e.g., 'json', 'markdown')
            context: Optional additional context

        Returns:
            Structured response in the requested format

        Raises:
            ResponseGenerationError: On unrecoverable error
        """
        try:
            # 1. Synthesize content from search_results and enriched_content
            synthesized_content = self.synthesizer.synthesize(
                search_results, enriched_content, context
            )

            # 2. Build response structure using ResponseBuilder
            template_name = context.get("template_name") if context and "template_name" in context else "default"
            metadata = context.get("metadata") if context and "metadata" in context else {}
            response_obj = self.builder.build(
                synthesized_content, template_name, metadata
            )

            # 3. Render response using TemplateEngine
            try:
                template_str = self.template_engine.load_template(template_name)
            except (TemplateNotFoundError, Exception) as e:
                self.logger.error(f"Template loading failed: {e}")
                raise ResponseGenerationError(f"Template loading failed: {e}")

            render_ctx = dict(query=query, **(metadata or {}))
            render_ctx["content"] = synthesized_content
            try:
                rendered = self.template_engine.render_template(template_str, render_ctx)
            except (TemplateRenderError, Exception) as e:
                self.logger.error(f"Template rendering failed: {e}")
                raise ResponseGenerationError(f"Template rendering failed: {e}")

            response_obj["rendered"] = rendered

            # 4. Format output using ResponseFormatter
            try:
                formatted = self.formatter.format(
                    response_obj, output_format
                )
            except Exception as e:
                self.logger.error(f"Response formatting failed: {e}")
                raise ResponseGenerationError(f"Response formatting failed: {e}")

            # 5. Validate final response with ResponseValidator
            schema = context.get("schema") if context and "schema" in context else None
            quality_checks = context.get("quality_checks") if context and "quality_checks" in context else None
            try:
                self.validator.validate(
                    response_obj, schema, quality_checks
                )
            except Exception as e:
                self.logger.error(f"Response validation failed: {e}")
                raise ResponseGenerationError(f"Response validation failed: {e}")

            # 6. Return formatted response
            return formatted

        except ResponseGenerationError as e:
            self.logger.error(f"Response generation error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in response generation: {e}")
            raise ResponseGenerationError(f"Unexpected error in response generation: {e}")