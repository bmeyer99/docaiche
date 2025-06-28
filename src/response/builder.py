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
        build: Assemble a response from content and meta

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
        synthesized_content: Any = None,
        template_name: str = None,
        meta: Optional[Dict[str, Any]] = None,
        *,
        data: Any = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build a structured response object.

        Args:
            synthesized_content: Content to include in the response
            template_name: Name of the template to use
            meta: Optional meta for the response
            data: Alternative to synthesized_content (preferred if provided)

        Returns:
            Dict representing the response structure

        Raises:
            ValueError: On invalid input
        """
        try:
            # Use 'data' if provided, else fallback to synthesized_content
            content = data if data is not None else synthesized_content
            # Accept meta as a keyword argument, default to {}
            meta = meta if meta is not None else kwargs.get("meta", {})
            # Accept template_name as a keyword argument, default to "default"
            template_name = (
                template_name
                if template_name is not None
                else kwargs.get("template_name", "default")
            )
            if content is None:
                raise ValueError("Synthesized content/data is required.")
            if meta is not None and not isinstance(meta, dict):
                raise ValueError("Meta must be a dictionary if provided.")
            response = {
                "template": template_name,
                "content": content,
                "metadata": meta or {},
            }
            # Extensible: allow meta to override/add top-level keys
            if meta:
                for k, v in meta.items():
                    if k not in response:
                        response[k] = v
                # --- FIX: Always include top-level "meta" key if meta is provided ---
                response["meta"] = meta
            return response
        except Exception as e:
            self.logger.error(f"Response assembly error: {e}")
            raise ValueError(f"Response assembly failed: {e}")
