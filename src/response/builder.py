"""ResponseBuilder: Constructs structured responses for output (PRD-011).

Responsible for assembling response objects from synthesized content and templates.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ResponseBuilder:
    """Builds structured response objects from content and templates.

    Args:
        None (dependencies injected via methods if needed)

    Methods:
        build: Assemble a response from content and metadata

    Raises:
        ValueError: On invalid input

    Integration Points:
        - Consumes synthesized content from ContentSynthesizer
        - Uses templates from TemplateEngine

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def build(
        self,
        synthesized_content: Any,
        template_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a structured response object.

        Args:
            synthesized_content: Content to include in the response
            template_name: Name of the template to use
            metadata: Optional metadata for the response

        Returns:
            Dict representing the response structure

        Raises:
            ValueError: On invalid input
        """
        try:
            if not synthesized_content or not template_name:
                raise ValueError("Synthesized content and template name are required.")
            response = {
                "template": template_name,
                "content": synthesized_content,
                "metadata": metadata or {},
            }
            # Extensible: allow metadata to override/add top-level keys
            if metadata:
                for k, v in metadata.items():
                    if k not in response:
                        response[k] = v
            return response
        except Exception as e:
            self.logger.error(f"Response assembly error: {e}")
            raise ValueError(f"Response assembly failed: {e}")