"""TemplateEngine: Handles response formatting and template rendering (PRD-011)."""

import os
from typing import Any, Dict

from src.response.exceptions import TemplateNotFoundError, TemplateRenderError


class TemplateEngine:
    """Manages response templates and rendering logic."""

    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir

    def load_template(self, template_name: str) -> str:
        """Load a template by name."""
        template_file = f"{template_name}.prompt"
        template_path = os.path.join(self.template_dir, template_file)

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise TemplateNotFoundError(
                f"Template '{template_name}' not found at {template_path}"
            )

    async def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Load and render a template."""
        template_str = self.load_template(template_name)
        try:
            return template_str.format(**context)
        except KeyError as e:
            raise TemplateRenderError(f"Missing key in template '{template_name}': {e}")
