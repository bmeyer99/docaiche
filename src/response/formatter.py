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

    def format(self, response: Dict[str, Any], output_format: str = "json") -> str:
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
            if not response or not isinstance(response, dict):
                self.logger.warning(
                    "Non-dict response input to format(); returning minimal output."
                )
                if output_format.lower() == "json":
                    return json.dumps(
                        {"content": str(response)}, ensure_ascii=False, indent=2
                    )
                elif output_format.lower() == "markdown":
                    return f"### Content\n{str(response)}\n"
                elif output_format.lower() == "html":
                    return f"&lt;div class='response'&gt;&lt;h3&gt;Content&lt;/h3&gt;&lt;p&gt;{str(response)}&lt;/p&gt;&lt;/div&gt;"
                else:
                    return str(response)
            if output_format.lower() == "json":
                result = json.dumps(response, ensure_ascii=False, indent=2)
                if not result.strip():
                    raise ValueError("Formatted JSON output is empty for valid input.")
                return result
            elif output_format.lower() == "markdown":
                md = ""
                if "content" in response:
                    md += "### Content\n"
                    if isinstance(response["content"], list) and response["content"]:
                        for item in response["content"]:
                            md += f"- {item}\n"
                    elif response["content"]:
                        md += f"{response['content']}\n"
                    else:
                        md += "- (No content)\n"
                else:
                    md += "### Content\n- (No content)\n"
                if "metadata" in response and response["metadata"]:
                    md += "\n#### Metadata\n"
                    md += "```json\n"
                    md += json.dumps(response["metadata"], ensure_ascii=False, indent=2)
                    md += "\n```\n"
                if not md.strip():
                    raise ValueError(
                        "Formatted Markdown output is empty for valid input."
                    )
                return md
            elif output_format.lower() == "html":
                html = "<div class='response'>"
                if "content" in response:
                    html += "<h3>Content</h3>"
                    if isinstance(response["content"], list) and response["content"]:
                        html += "<ul>"
                        for item in response["content"]:
                            html += f"<li>{item}</li>"
                        html += "</ul>"
                    elif response["content"]:
                        html += f"<p>{response['content']}</p>"
                    else:
                        html += "<p>(No content)</p>"
                else:
                    html += "<h3>Content</h3><p>(No content)</p>"
                if "metadata" in response and response["metadata"]:
                    html += "<h4>Metadata</h4>"
                    html += (
                        "<pre>"
                        + json.dumps(response["metadata"], ensure_ascii=False, indent=2)
                        + "</pre>"
                    )
                html += "</div>"
                if not html.strip():
                    raise ValueError("Formatted HTML output is empty for valid input.")
                return html
            else:
                self.logger.error(f"Unsupported output format: {output_format}")
                raise ValueError(f"Unsupported output format: {output_format}")
        except Exception as e:
            self.logger.error(f"Response formatting error: {e}")
            raise ValueError(f"Response formatting failed: {e}")
