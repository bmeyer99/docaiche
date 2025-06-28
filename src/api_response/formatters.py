"""API Response formatters for output serialization."""

from abc import ABC, abstractmethod
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class BaseAPIFormatter(ABC):
    """
    Abstract base class for API response formatters.
    """

    @abstractmethod
    def format(self, data: Any, context: Dict[str, Any] = {}) -> Any:
        """
        Format the response data for API delivery.

        Args:
            data: The data to format.
            context: Optional context for formatting.

        Returns:
            Formatted response data.

        Raises:
            FormattingError: On formatting failure.

        # TODO: IMPLEMENTATION ENGINEER - Implement format logic in subclasses.
        # INPUT: Raw response data.
        # OUTPUT: Formatted response (e.g., JSON serializable).
        """
        pass

class JSONAPIFormatter(BaseAPIFormatter):
    """
    Formats API responses as JSON API-compliant objects.
    """

    def format(self, data: Any, context: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Format data as JSON API.
        """
        # IMPLEMENTATION ENGINEER: Implement JSON API formatting.
        # JSON:API requires a "data" key, and optionally "meta" and "errors".
        # If data is a list, wrap as "data": [...]; if dict, wrap as "data": {...}
        # If data contains "errors", move to "errors" key.
        try:
            response: Dict[str, Any] = {}
            if isinstance(data, dict) and "errors" in data:
                response["errors"] = data["errors"]
                if "meta" in data:
                    response["meta"] = data["meta"]
                if "data" in data:
                    response["data"] = data["data"]
            else:
                response["data"] = data
                # Optionally add meta if present in context
                meta = context.get("meta")
                if meta:
                    response["meta"] = meta
            return response
        except Exception as e:
            logger.error(f"JSONAPIFormatter failed: {e}", exc_info=True)
            raise

class SimpleJSONFormatter(BaseAPIFormatter):
    """
    Formats API responses as simple JSON objects.
    """

    def format(self, data: Any, context: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Format data as simple JSON.
        """
        # IMPLEMENTATION ENGINEER: Implement simple JSON formatting.
        # Just return the data as a dict with a "result" key if not already a dict.
        try:
            if isinstance(data, dict):
                return data
            return {"result": data}
        except Exception as e:
            logger.error(f"SimpleJSONFormatter failed: {e}", exc_info=True)
            raise