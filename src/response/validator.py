"""ResponseValidator: Validates quality and completeness of responses (PRD-011)."""

from typing import Any, Dict, Optional


class ResponseValidator:
    """Validates responses for quality, structure, and completeness."""

    def validate(
        self,
        response: Any,
        schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate the response for structure and quality."""
        if not isinstance(response, dict):
            return False

        if schema:
            for key, expected_type in schema.items():
                if key not in response or not isinstance(
                    response.get(key), expected_type
                ):
                    return False

        return True
