"""
Prompt Template Manager - PRD-005 LLM-005
Utility for loading and formatting prompt templates from .prompt files

Supports variable substitution with {variable_name} syntax, template validation,
and caching for performance as specified in PRD-005.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

class PromptTemplateError(Exception):
    """Raised when prompt template operations fail"""
    pass

class PromptManager:
    """
    Manages prompt templates with loading, formatting, and validation.

    Implements LLM-005 requirements for template management with variable
    substitution, validation, and caching capabilities.
    """

    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize PromptManager with templates directory.

        Args:
            templates_dir: Directory containing .prompt template files
        """
        self.templates_dir = Path(templates_dir)
        self._template_cache: Dict[str, str] = {}
        self._variable_cache: Dict[str, set] = {}

        # Ensure templates directory exists
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory {templates_dir} does not exist")

    def load_template(self, template_name: str) -> str:
        """
        Load template content from .prompt file.

        Args:
            template_name: Name of template (without .prompt extension)

        Returns:
            Template content as string

        Raises:
            PromptTemplateError: When template cannot be loaded
        """
        # Check cache first for performance
        if template_name in self._template_cache:
            logger.debug(f"Template {template_name} loaded from cache")
            return self._template_cache[template_name]

        # Construct file path
        template_path = self.templates_dir / f"{template_name}.prompt"

        if not template_path.exists():
            raise PromptTemplateError(f"Template file not found: {template_path}")

        try:
            # Load template content
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                raise PromptTemplateError(f"Template {template_name} is empty")

            # Cache template content
            self._template_cache[template_name] = content

            # Extract and cache variables for validation
            variables = self._extract_variables(content)
            self._variable_cache[template_name] = variables

            logger.debug(f"Template {template_name} loaded successfully with variables: {variables}")
            return content

        except IOError as e:
            raise PromptTemplateError(f"Failed to read template {template_name}: {str(e)}")

    def format_template(self, template_name: str, **variables) -> str:
        """
        Format template with variable substitution and input sanitization.

        Args:
            template_name: Name of template to format
            **variables: Variables to substitute in template

        Returns:
            Formatted template string

        Raises:
            PromptTemplateError: When formatting fails or variables are missing
        """
        # Load template
        template_content = self.load_template(template_name)

        # Validate required variables
        self._validate_variables(template_name, variables)

        # Sanitize all variable values to prevent prompt injection
        sanitized_vars = {k: self._sanitize_input(str(v)) for k, v in variables.items()}
        self._validate_sanitized_vars(sanitized_vars)

        try:
            # Format template with variable substitution
            formatted = template_content.format(**sanitized_vars)

            logger.debug(f"Template {template_name} formatted successfully")
            return formatted

        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise PromptTemplateError(f"Missing required variable '{missing_var}' for template {template_name}")

        except ValueError as e:
            raise PromptTemplateError(f"Template formatting error for {template_name}: {str(e)}")

    def _sanitize_input(self, value: str) -> str:
        """
        Sanitize input to prevent prompt injection and unsafe content.
        Args:
            value: Input string
        Returns:
            Sanitized string
        """
        # Remove curly braces, control chars, and excessive whitespace
        sanitized = re.sub(r"[{}]", "", value)
        sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", sanitized)
        sanitized = sanitized.strip()
        # Limit length to 4096 chars to prevent prompt overflow
        if len(sanitized) > 4096:
            sanitized = sanitized[:4096]
        # Block common prompt injection patterns
        sanitized = re.sub(r"(ignore previous instructions|as an ai language model|you are a helpful assistant)", "", sanitized, flags=re.IGNORECASE)
        return sanitized

    def _validate_sanitized_vars(self, variables: Dict[str, str]) -> None:
        """
        Additional validation for sanitized variables to prevent prompt injection.
        Args:
            variables: Dict of sanitized variable values
        Raises:
            PromptTemplateError: If unsafe content is detected
        """
        for k, v in variables.items():
            # Block suspicious patterns
            if re.search(r"(}}|{{|<script|</script|system:|user:|assistant:)", v, re.IGNORECASE):
                raise PromptTemplateError(f"Unsafe content detected in variable '{k}'")
            # Block excessive length
            if len(v) > 4096:
                raise PromptTemplateError(f"Variable '{k}' exceeds maximum allowed length")

    def _extract_variables(self, template_content: str) -> set:
        """
        Extract variable names from template content.

        Args:
            template_content: Template string

        Returns:
            Set of variable names found in template
        """
        # Find all {variable_name} patterns
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template_content)

        # Filter out format specifiers (e.g., {var:format})
        variables = set()
        for match in matches:
            var_name = match.split(':')[0].strip()
            if var_name and var_name.isidentifier():
                variables.add(var_name)

        return variables

    def _validate_variables(self, template_name: str, provided_vars: Dict[str, Any]) -> None:
        """
        Validate that all required variables are provided.

        Args:
            template_name: Name of template
            provided_vars: Variables provided for substitution

        Raises:
            PromptTemplateError: When required variables are missing
        """
        if template_name not in self._variable_cache:
            # Extract variables if not cached
            template_content = self._template_cache.get(template_name)
            if template_content:
                self._variable_cache[template_name] = self._extract_variables(template_content)

        required_vars = self._variable_cache.get(template_name, set())
        provided_var_names = set(provided_vars.keys())

        missing_vars = required_vars - provided_var_names
        if missing_vars:
            raise PromptTemplateError(
                f"Missing required variables for template {template_name}: {', '.join(sorted(missing_vars))}"
            )

    def get_template(self, template_name: str) -> str:
        """
        Return the raw template string for the given template name.
        Args:
            template_name: Name of template (without .prompt extension)
        Returns:
            Template content as string
        Raises:
            PromptTemplateError: When template cannot be loaded
        """
        return self.load_template(template_name)

    def fill_template(self, template_name: str, variables: dict) -> str:
        """
        Fill the template with the provided variables, handling missing variables gracefully.
        Args:
            template_name: Name of template (without .prompt extension)
            variables: Dictionary of variables to substitute
        Returns:
            Formatted template string
        Raises:
            PromptTemplateError: When formatting fails
        """
        template_content = self.load_template(template_name)
        # Get all required variables for the template
        required_vars = self._variable_cache.get(template_name)
        if required_vars is None:
            required_vars = self._extract_variables(template_content)
            self._variable_cache[template_name] = required_vars
        # Fill missing variables with empty string
        safe_vars = {k: self._sanitize_input(str(variables.get(k, ""))) for k in required_vars}
        # Add any extra variables provided
        for k, v in variables.items():
            if k not in safe_vars:
                safe_vars[k] = self._sanitize_input(str(v))
        try:
            formatted = template_content.format(**safe_vars)
            logger.debug(f"Template {template_name} filled successfully")
            return formatted
        except Exception as e:
            logger.error(f"Template filling error for {template_name}: {e}")
            raise PromptTemplateError(f"Template filling error for {template_name}: {str(e)}")

    def get_template_variables(self, template_name: str) -> set:
        """
        Get list of variables required by template.

        Args:
            template_name: Name of template

        Returns:
            Set of variable names required by template
        """
        # Load template to populate cache
        self.load_template(template_name)
        return self._variable_cache.get(template_name, set()).copy()

    def list_templates(self) -> list:
        """
        List all available template names.

        Returns:
            List of template names (without .prompt extension)
        """
        if not self.templates_dir.exists():
            return []

        templates = []
        for file_path in self.templates_dir.glob("*.prompt"):
            templates.append(file_path.stem)

        return sorted(templates)

    def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate template syntax and structure.

        Args:
            template_name: Name of template to validate

        Returns:
            Validation result dictionary
        """
        try:
            # Load template
            content = self.load_template(template_name)

            # Extract variables
            variables = self.get_template_variables(template_name)

            # Check for common issues
            issues = []

            # Check for unmatched braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                issues.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

            # Check for empty template
            if not content.strip():
                issues.append("Template is empty")

            # Check for variables with invalid names
            all_braces = re.findall(r'\{([^}]*)\}', content)
            for var in all_braces:
                var_name = var.split(':')[0].strip()
                if var_name and not var_name.isidentifier():
                    issues.append(f"Invalid variable name: '{var_name}'")

            return {
                'valid': len(issues) == 0,
                'template': template_name,
                'variables': sorted(variables),
                'variable_count': len(variables),
                'issues': issues,
                'content_length': len(content)
            }

        except PromptTemplateError as e:
            return {
                'valid': False,
                'template': template_name,
                'variables': [],
                'variable_count': 0,
                'issues': [str(e)],
                'content_length': 0
            }

    def clear_cache(self) -> None:
        """Clear template and variable caches."""
        self._template_cache.clear()
        self._variable_cache.clear()
        logger.debug("Template cache cleared")

    def reload_template(self, template_name: str) -> str:
        """
        Force reload template from disk, bypassing cache.

        Args:
            template_name: Name of template to reload

        Returns:
            Template content
        """
        # Remove from cache
        self._template_cache.pop(template_name, None)
        self._variable_cache.pop(template_name, None)

        # Load fresh from disk
        return self.load_template(template_name)

# Global prompt manager instance for convenience
_global_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager(templates_dir: str = "templates") -> PromptManager:
    """
    Get global PromptManager instance.

    Args:
        templates_dir: Templates directory path

    Returns:
        PromptManager instance
    """
    global _global_prompt_manager

    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager(templates_dir)

    return _global_prompt_manager

def format_template(template_name: str, **variables) -> str:
    """
    Convenience function for formatting templates.

    Args:
        template_name: Name of template
        **variables: Variables for substitution

    Returns:
        Formatted template string
    """
    manager = get_prompt_manager()
    return manager.format_template(template_name, **variables)