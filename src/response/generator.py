"""ResponseGenerator: Main entry point for intelligent response generation (PRD-011)."""

import logging
from typing import Any, Dict, Optional

from src.response.builder import ResponseBuilder
from src.response.content_synthesizer import ContentSynthesizer
from src.response.exceptions import ResponseGenerationError, TemplateNotFoundError
from src.response.formatter import ResponseFormatter
from src.response.template_engine import TemplateEngine
from src.response.validator import ResponseValidator

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Coordinates the full response generation workflow."""

    def __init__(
        self,
        builder: Optional[ResponseBuilder] = None,
        template_engine: Optional[TemplateEngine] = None,
        content_synthesizer: Optional[ContentSynthesizer] = None,
        formatter: Optional[ResponseFormatter] = None,
        validator: Optional[ResponseValidator] = None,
    ):
        self.builder = builder or ResponseBuilder()
        self.template_engine = template_engine or TemplateEngine()
        self.content_synthesizer = content_synthesizer or ContentSynthesizer()
        self.formatter = formatter or ResponseFormatter()
        self.validator = validator or ResponseValidator()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def generate_response(
        self,
        search_results: list,
        enrichment_results: Optional[list] = None,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        output_format: str = "json",
    ) -> Any:
        """Generate a structured response."""
        context = context or {}
        try:
            synthesized_content = self.content_synthesizer.synthesize(
                search_results, enrichment_results
            )

            response_obj = self.builder.build(
                synthesized_content, meta=context.get("meta", {})
            )

            template_name = context.get("template_name", "default")
            render_ctx = {
                "query": query,
                "content": synthesized_content,
                **context.get("meta", {}),
            }

            rendered = await self.template_engine.render(template_name, render_ctx)
            response_obj["rendered"] = rendered

            if not self.validator.validate(response_obj, schema=context.get("schema")):
                raise ResponseGenerationError("Response validation failed.")

            return self.formatter.format(response_obj, output_format)

        except TemplateNotFoundError as e:
            self.logger.error(f"Template not found: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error during response generation: {e}", exc_info=True)
            raise ResponseGenerationError(f"Failed to generate response: {e}")
