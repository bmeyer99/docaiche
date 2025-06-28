"""
JSON Parsing Utility for LLM Responses - PRD-005 LLM-006
Robust JSON extraction and validation from LLM responses

Handles partial JSON, markdown code blocks, malformed responses, and validates
against expected Pydantic model schemas as specified in PRD-005.
"""

import logging
import json
import re
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class JSONParsingError(Exception):
    """Raised when JSON cannot be extracted or parsed from LLM response"""

    pass


class JSONValidationError(Exception):
    """Raised when JSON doesn't match expected Pydantic model schema"""

    pass


class JSONParser:
    """
    Robust JSON parser for LLM responses with multiple extraction strategies.

    Implements LLM-006 requirements for handling various JSON formats that
    LLMs might produce, including markdown wrapped JSON and partial responses.
    """

    @staticmethod
    def extract_and_parse(response_text: str, model_class: Type[T]) -> Optional[T]:
        """
        Extract and parse JSON from LLM response text, validate against model.

        Args:
            response_text: Raw LLM response text
            model_class: Pydantic model class for validation

        Returns:
            Validated Pydantic model instance or None if parsing/validation fails

        Raises:
            JSONParsingError: When JSON cannot be extracted or parsed
            JSONValidationError: When JSON doesn't match model schema
        """
        try:
            logger.debug(f"Attempting JSON extraction for {model_class.__name__}")

            json_text = JSONParser._extract_json_text(response_text)
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed: {e}")
                return None

            try:
                validated_model = model_class(**json_data)
                logger.debug(f"Successfully validated {model_class.__name__}")
                return validated_model
            except ValidationError as e:
                logger.error(f"Model validation failed for {model_class.__name__}: {e}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error in JSON extraction: {e}")
            return None

    @staticmethod
    def _extract_json_text(response_text: str) -> str:
        """
        Extract JSON text from various LLM response formats.

        Handles:
        - Plain JSON
        - Markdown code blocks with ```json
        - Partial JSON responses
        - JSON wrapped in explanatory text

        Args:
            response_text: Raw LLM response

        Returns:
            Extracted JSON text

        Raises:
            JSONParsingError: When no valid JSON can be found
        """
        if not response_text or not response_text.strip():
            raise JSONParsingError("Empty or whitespace-only response")

        # Strategy 1: Look for markdown code blocks
        json_text = JSONParser._extract_from_markdown(response_text)
        if json_text:
            return json_text

        # Strategy 2: Find JSON object boundaries
        json_text = JSONParser._extract_by_braces(response_text)
        if json_text:
            return json_text

        # Strategy 3: Try the entire response as JSON
        json_text = response_text.strip()
        if JSONParser._is_valid_json_structure(json_text):
            return json_text

        # Strategy 4: Look for JSON-like patterns and attempt repair
        json_text = JSONParser._attempt_json_repair(response_text)
        if json_text:
            return json_text

        raise JSONParsingError("No valid JSON structure found in response")

    @staticmethod
    def _extract_from_markdown(text: str) -> Optional[str]:
        """Extract JSON from markdown code blocks."""
        json_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        matches = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            candidate = match.strip()
            if JSONParser._is_valid_json_structure(candidate):
                return candidate

        return None

    @staticmethod
    def _extract_by_braces(text: str) -> Optional[str]:
        """Extract JSON by finding balanced brace boundaries."""
        start_pos = text.find("{")
        if start_pos == -1:
            return None

        brace_count = 0
        end_pos = start_pos

        for i, char in enumerate(text[start_pos:], start_pos):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break

        if brace_count == 0:
            candidate = text[start_pos : end_pos + 1]
            if JSONParser._is_valid_json_structure(candidate):
                return candidate

        return None

    @staticmethod
    def _is_valid_json_structure(text: str) -> bool:
        """Check if text has basic JSON structure without full parsing."""
        text = text.strip()
        if not text:
            return False

        # Must start and end with braces
        if not (text.startswith("{") and text.endswith("}")):
            return False

        # Basic brace balance check
        brace_count = 0
        for char in text:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count < 0:
                    return False

        return brace_count == 0

    @staticmethod
    def _attempt_json_repair(text: str) -> Optional[str]:
        """
        Attempt to repair common JSON issues in LLM responses.

        Handles:
        - Missing closing braces
        - Trailing commas
        - Unquoted keys
        """
        # Remove explanatory text before and after JSON-like content
        lines = text.split("\n")
        json_lines = []
        in_json = False

        for line in lines:
            line_stripped = line.strip()
            if "{" in line_stripped:
                in_json = True

            if in_json:
                json_lines.append(line)

            if "}" in line_stripped and in_json:
                break

        if not json_lines:
            return None

        candidate = "\n".join(json_lines).strip()

        # Try to fix common issues
        candidate = JSONParser._fix_trailing_commas(candidate)
        candidate = JSONParser._fix_missing_quotes(candidate)
        candidate = JSONParser._fix_missing_braces(candidate)

        if JSONParser._is_valid_json_structure(candidate):
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _fix_trailing_commas(text: str) -> str:
        """Remove trailing commas before closing braces/brackets."""
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        return text

    @staticmethod
    def _fix_missing_quotes(text: str) -> str:
        """Add quotes around unquoted keys (basic attempt)."""
        text = re.sub(r"(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', text)
        return text

    @staticmethod
    def _fix_missing_braces(text: str) -> str:
        """Add missing closing braces if needed."""
        brace_count = 0
        for char in text:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1

        # Add missing closing braces
        if brace_count > 0:
            text += "}" * brace_count

        return text


def parse_llm_response(response_text: str, model_class: Type[T]) -> Optional[T]:
    """
    Convenience function for parsing LLM responses.

    Args:
        response_text: Raw LLM response text
        model_class: Pydantic model class for validation

    Returns:
        Validated Pydantic model instance or None if parsing/validation fails
    """
    try:
        return JSONParser.extract_and_parse(response_text, model_class)
    except Exception:
        return None
