"""ResponseValidator: Validates quality and completeness of responses (PRD-011).

Ensures generated responses meet quality, structure, and completeness requirements.
"""
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ResponseValidator:
    """Validates responses for quality, structure, and completeness.

    Args:
        None (dependencies injected via methods if needed)

    Methods:
        validate: Validate a response object

    Raises:
        ValueError: On validation failure

    Integration Points:
        - Used by ResponseGenerator for final validation

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate(
        self,
        response: Any,
        schema: Optional[Dict[str, Any]] = None,
        quality_checks: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate the response for structure and quality.

        Args:
            response: Response object to validate
            schema: Optional schema definition for validation
            quality_checks: Optional quality check parameters

        Returns:
            True if valid, False if invalid (but not totally malformed)

        Raises:
            ValueError: On totally invalid input (e.g., None)
        """
        errors = []
        try:
            if response is None:
                self.logger.error("Response is None")
                raise ValueError("Response is None")
            # Basic structure validation
            if schema:
                for key, val_type in schema.items():
                    if key not in response:
                        errors.append(f"Missing required key: {key}")
                    elif not isinstance(response[key], val_type):
                        errors.append(f"Key '{key}' has wrong type: expected {val_type}, got {type(response[key])}")
            # Quality checks (e.g., content non-empty, metadata present)
            if quality_checks:
                for check, rule in quality_checks.items():
                    if check == "content_nonempty":
                        if not response.get("content"):
                            errors.append("Content is empty")
                    if check == "metadata_required":
                        if "metadata" not in response or not response["metadata"]:
                            errors.append("Metadata is missing or empty")
            # Additional: treat {"data": None} as invalid
            if isinstance(response, dict) and "data" in response and response["data"] is None:
                errors.append("Data is None")
            if errors:
                for err in errors:
                    self.logger.error(f"Response validation error: {err}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Response validation exception: {e}")
            raise ValueError(f"Response validation exception: {e}")