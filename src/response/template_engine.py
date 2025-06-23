"""TemplateEngine: Handles response formatting and template rendering (PRD-011).

Manages template loading, rendering, and configuration integration.
"""
from typing import Any, Dict, Optional
import logging
import os
from src.response.exceptions import TemplateNotFoundError, TemplateRenderError

logger = logging.getLogger(__name__)

class TemplateEngine:
    """Manages response templates and rendering logic.

    Args:
        template_dir: Directory to load templates from
        config: Optional configuration for template management

    Methods:
        render_template: Render a template with provided context
        load_template: Load a template by name
        render: Render a template by name and context, with output format

    Raises:
        TemplateNotFoundError: If template is missing
        TemplateRenderError: On rendering failure

    Integration Points:
        - Loads templates from configuration or file system
        - Used by ResponseBuilder and ResponseGenerator

    """

    def __init__(self, template_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.template_dir = template_dir or self.config.get('templates_dir', 'templates')
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def load_template(self, template_name: str) -> str:
        """Load a template by name.

        Args:
            template_name: Name of the template to load

        Returns:
            Template string

        Raises:
            TemplateNotFoundError: If template is missing
        """
        # Try config-based templates first
        if self.config and 'templates' in self.config and template_name in self.config['templates']:
            return self.config['templates'][template_name]
        # Fallback to file-based templates
        templates_dir = self.template_dir or 'templates'
        template_path = os.path.join(templates_dir, f"{template_name}.prompt")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Template not found: {template_path}")
            raise TemplateNotFoundError(f"Template '{template_name}' not found.")
        except Exception as e:
            self.logger.error(f"Error loading template '{template_name}': {e}")
            raise TemplateNotFoundError(f"Error loading template '{template_name}': {e}")

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template with the provided context.

        Args:
            template: Template string
            context: Context variables for rendering

        Returns:
            Rendered string

        Raises:
            TemplateRenderError: On rendering failure
        """
        try:
            # Simple Python format-based rendering (safe for MVP, replace with Jinja2 if needed)
            rendered = template.format(**{k: (v if v is not None else "") for k, v in context.items()})
            return rendered
        except KeyError as e:
            self.logger.error(f"Missing variable in template context: {e}")
            raise TemplateRenderError(f"Missing variable in template context: {e}")
        except Exception as e:
            self.logger.error(f"Template rendering error: {e}")
            raise TemplateRenderError(f"Template rendering error: {e}")

    def render(self, template_name: str, context: Dict[str, Any], output_format: str = "text") -> str:
        """
        Render a template by name with context and output format.

        Args:
            template_name: Name of the template to load and render
            context: Context variables for rendering
            output_format: Output format (currently ignored, for future extension)

        Returns:
            Rendered string

        Raises:
            TemplateNotFoundError: If template is missing
            TemplateRenderError: On rendering failure
        """
        template = self.load_template(template_name)
        return self.render_template(template, context)