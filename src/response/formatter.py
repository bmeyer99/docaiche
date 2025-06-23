"""ResponseFormatter: Handles output format conversion (PRD-011).

Supports formatting responses as JSON, Markdown, or other formats.
"""

from typing import Any, Dict
import logging
import json

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """Formats structured responses into the desired output format.

    Args:
        None (dependencies injected via methods if needed)

    Methods:
        format: Convert response to specified format

    Raises:
        ValueError: On unsupported format

    Integration Points:
        - Used by ResponseGenerator for output formatting

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def format(
        self,
        response: Dict[str, Any],
        output_format: str = "json"
    ) -> str:
        """Format the response as JSON, Markdown, or other supported formats.

        Args:
            response: Structured response object
            output_format: Desired output format (e.g., 'json', 'markdown')

        Returns:
            Formatted response string

        Raises:
            ValueError: On unsupported format
        """
        try:
            if output_format.lower() == "json":
                return json.dumps(response, ensure_ascii=False, indent=2)
            elif output_format.lower() == "markdown":
                # Simple Markdown: content as bullet points, metadata as code block
                md = ""
                if "content" in response:
                    md += "### Content\n"
                    if isinstance(response["content"], list):
                        for item in response["content"]:
                            md += f"- {item}\n"
                    else:
                        md += f"{response['content']}\n"
                if "metadata" in response and response["metadata"]:
                    md += "\n#### Metadata\n"
                    md += "```json\n"
                    md += json.dumps(response["metadata"], ensure_ascii=False, indent=2)
                    md += "\n```\n"
                return md
            elif output_format.lower() == "html":
                # Simple HTML: content as list, metadata as pre
                html = "<div class='response'>"
                if "content" in response:
                    html += "<h3>Content</h3>"
                    if isinstance(response["content"], list):
                        html += "<ul>"
                        for item in response["content"]:
                            html += f"<li>{item}</li>"
                        html += "</ul>"
                    else:
                        html += f"<p>{response['content']}</p>"
                if "metadata" in response and response["metadata"]:
                    html += "<h4>Metadata</h4>"
                    html += "<pre>" + json.dumps(response["metadata"], ensure_ascii=False, indent=2) + "</pre>"
                html += "</div>"
                return html
            else:
                self.logger.error(f"Unsupported output format: {output_format}")
                raise ValueError(f"Unsupported output format: {output_format}")
        except Exception as e:
            self.logger.error(f"Response formatting error: {e}")
            raise ValueError(f"Response formatting failed: {e}")