"""
Security Validator Implementation
================================

Comprehensive input validation and sanitization for MCP operations.
Implements defense against injection attacks and data validation.
"""

import re
import html
import json
import logging
from typing import Any, Dict, Optional, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse, quote

from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Production mode - reject suspicious input
    MODERATE = "moderate"  # Development mode - warn but allow
    PERMISSIVE = "permissive"  # Testing mode - minimal validation


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    sanitized_value: Any
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        self.errors = self.errors or []
        self.warnings = self.warnings or []


class SecurityValidator:
    """
    Comprehensive security validator for MCP inputs and outputs.
    
    Provides multi-layer validation including:
    - Input type validation
    - Pattern-based threat detection
    - Length and size constraints
    - Character encoding validation
    - Output sanitization
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level
        
        # Dangerous patterns for injection attacks
        self.injection_patterns = {
            # SQL Injection
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b.*\b(from|where|table|database)\b)": "SQL injection attempt",
            r"(;|\||&&).*\b(shutdown|drop|delete|truncate)\b": "Destructive SQL command",
            
            # NoSQL Injection
            r"\$\b(where|regex|ne|gt|lt|gte|lte|in|nin|exists)\b": "NoSQL injection attempt",
            r"{\s*\$\w+\s*:": "MongoDB operator injection",
            
            # Command Injection
            r"(;|\||&&|`|\$\(|\${).*\b(rm|dd|mkfs|format|kill|shutdown|reboot)\b": "Command injection attempt",
            r"(\.\.\/|\.\.\\|%2e%2e%2f|%252e%252e%252f)": "Path traversal attempt",
            
            # Script Injection
            r"<\s*script[^>]*>.*<\s*/\s*script\s*>": "Script tag injection",
            r"javascript\s*:": "JavaScript protocol injection",
            r"on\w+\s*=": "Event handler injection",
            
            # XML/XXE Injection
            r"<!ENTITY": "XML entity injection",
            r"<\?xml.*\?>": "XML declaration injection",
            
            # LDAP Injection
            r"\(\w*=\*\)": "LDAP wildcard injection",
            r"[()&|!].*[()&|!]": "LDAP operator injection"
        }
        
        # Safe character sets
        self.safe_chars = {
            "alphanumeric": re.compile(r"^[a-zA-Z0-9]+$"),
            "identifier": re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$"),
            "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "url": re.compile(r"^https?://[a-zA-Z0-9.-]+(/[a-zA-Z0-9./_-]*)?(\?[a-zA-Z0-9=&_-]*)?$"),
            "path": re.compile(r"^[a-zA-Z0-9._/-]+$")
        }
        
        # Maximum lengths
        self.max_lengths = {
            "query": 1000,
            "feedback": 5000,
            "identifier": 255,
            "url": 2048,
            "content": 1048576,  # 1MB
            "json": 10485760     # 10MB
        }
    
    async def validate_input(
        self,
        data: Any,
        input_type: str = "generic",
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate input data for security threats.
        
        Args:
            data: Input data to validate
            input_type: Type of input (query, content, identifier, etc.)
            context: Additional context for validation
            
        Returns:
            ValidationResult with sanitized data
        """
        try:
            # Type-specific validation
            if input_type == "query":
                return await self._validate_query(data)
            elif input_type == "content":
                return await self._validate_content(data)
            elif input_type == "identifier":
                return await self._validate_identifier(data)
            elif input_type == "url":
                return await self._validate_url(data)
            elif input_type == "json":
                return await self._validate_json(data)
            elif input_type == "feedback":
                return await self._validate_feedback(data)
            else:
                return await self._validate_generic(data)
                
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"Validation failed: {str(e)}"]
            )
    
    async def _validate_query(self, query: str) -> ValidationResult:
        """Validate search query input."""
        if not isinstance(query, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Query must be a string"]
            )
        
        # Length check
        if len(query) > self.max_lengths["query"]:
            return ValidationResult(
                is_valid=False,
                sanitized_value=query[:self.max_lengths["query"]],
                errors=[f"Query exceeds maximum length of {self.max_lengths['query']}"]
            )
        
        # Check for injection patterns
        for pattern, threat_type in self.injection_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                if self.validation_level == ValidationLevel.STRICT:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        errors=[f"Detected {threat_type}"]
                    )
                else:
                    logger.warning(f"Detected {threat_type} in query: {query[:100]}")
        
        # Sanitize query
        sanitized = html.escape(query)
        sanitized = re.sub(r'[<>]', '', sanitized)  # Remove angle brackets
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized
        )
    
    async def _validate_content(self, content: str) -> ValidationResult:
        """Validate document content."""
        if not isinstance(content, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Content must be a string"]
            )
        
        # Size check
        if len(content) > self.max_lengths["content"]:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"Content exceeds maximum size of {self.max_lengths['content']} bytes"]
            )
        
        # Check for malicious patterns
        warnings = []
        for pattern, threat_type in self.injection_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential {threat_type} detected")
        
        # Basic sanitization (preserve formatting)
        sanitized = content
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized,
            warnings=warnings if warnings else None
        )
    
    async def _validate_identifier(self, identifier: str) -> ValidationResult:
        """Validate identifier (tool name, resource name, etc.)."""
        if not isinstance(identifier, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Identifier must be a string"]
            )
        
        # Length check
        if len(identifier) > self.max_lengths["identifier"]:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"Identifier exceeds maximum length of {self.max_lengths['identifier']}"]
            )
        
        # Character validation
        if not self.safe_chars["identifier"].match(identifier):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Identifier contains invalid characters"]
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=identifier
        )
    
    async def _validate_url(self, url: str) -> ValidationResult:
        """Validate URL input."""
        if not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["URL must be a string"]
            )
        
        # Length check
        if len(url) > self.max_lengths["url"]:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"URL exceeds maximum length of {self.max_lengths['url']}"]
            )
        
        # Parse URL
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    errors=["URL must use HTTP or HTTPS scheme"]
                )
            
            # Check for suspicious patterns
            if '..' in parsed.path or parsed.path.startswith('//'):
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    errors=["URL contains suspicious path elements"]
                )
            
            # Sanitize URL
            sanitized = f"{parsed.scheme}://{parsed.netloc}{quote(parsed.path)}"
            if parsed.query:
                sanitized += f"?{quote(parsed.query, safe='=&')}"
            
            return ValidationResult(
                is_valid=True,
                sanitized_value=sanitized
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"Invalid URL format: {str(e)}"]
            )
    
    async def _validate_json(self, data: Union[str, dict]) -> ValidationResult:
        """Validate JSON input."""
        try:
            # Parse if string
            if isinstance(data, str):
                if len(data) > self.max_lengths["json"]:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        errors=[f"JSON exceeds maximum size of {self.max_lengths['json']} bytes"]
                    )
                parsed = json.loads(data)
            else:
                parsed = data
            
            # Deep validation
            errors = []
            self._validate_json_recursive(parsed, errors, depth=0)
            
            if errors:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    errors=errors
                )
            
            return ValidationResult(
                is_valid=True,
                sanitized_value=parsed
            )
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _validate_json_recursive(
        self,
        obj: Any,
        errors: List[str],
        depth: int,
        max_depth: int = 10
    ) -> None:
        """Recursively validate JSON structure."""
        if depth > max_depth:
            errors.append("JSON nesting too deep")
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    errors.append(f"Non-string key found: {type(key)}")
                elif len(key) > 255:
                    errors.append(f"Key too long: {key[:50]}...")
                else:
                    # Check key for injection
                    for pattern in self.injection_patterns:
                        if re.search(pattern, key, re.IGNORECASE):
                            errors.append(f"Suspicious key: {key}")
                            break
                
                self._validate_json_recursive(value, errors, depth + 1)
                
        elif isinstance(obj, list):
            if len(obj) > 10000:
                errors.append("Array too large")
            else:
                for item in obj:
                    self._validate_json_recursive(item, errors, depth + 1)
                    
        elif isinstance(obj, str):
            if len(obj) > 1048576:  # 1MB
                errors.append("String value too large")
    
    async def _validate_feedback(self, feedback: str) -> ValidationResult:
        """Validate feedback input."""
        if not isinstance(feedback, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Feedback must be a string"]
            )
        
        # Length check
        if len(feedback) > self.max_lengths["feedback"]:
            return ValidationResult(
                is_valid=False,
                sanitized_value=feedback[:self.max_lengths["feedback"]],
                errors=[f"Feedback exceeds maximum length of {self.max_lengths['feedback']}"]
            )
        
        # Basic sanitization
        sanitized = html.escape(feedback)
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized
        )
    
    async def _validate_generic(self, data: Any) -> ValidationResult:
        """Generic validation for unknown input types."""
        # Convert to string for validation
        try:
            data_str = str(data)
        except:
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                errors=["Cannot convert input to string"]
            )
        
        # Check for obvious injection attempts
        for pattern, threat_type in self.injection_patterns.items():
            if re.search(pattern, data_str, re.IGNORECASE):
                if self.validation_level == ValidationLevel.STRICT:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        errors=[f"Detected {threat_type}"]
                    )
        
        return ValidationResult(
            is_valid=True,
            sanitized_value=data
        )
    
    async def sanitize_output(
        self,
        data: Any,
        output_type: str = "json",
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Sanitize output data before sending to client.
        
        Args:
            data: Output data to sanitize
            output_type: Type of output (json, text, html)
            context: Additional context
            
        Returns:
            Sanitized output data
        """
        if output_type == "json":
            return self._sanitize_json_output(data)
        elif output_type == "html":
            return self._sanitize_html_output(data)
        elif output_type == "text":
            return self._sanitize_text_output(data)
        else:
            return data
    
    def _sanitize_json_output(self, data: Any) -> Any:
        """Sanitize JSON output."""
        if isinstance(data, dict):
            return {
                self._sanitize_key(k): self._sanitize_json_output(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_json_output(item) for item in data]
        elif isinstance(data, str):
            # Remove control characters
            return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data)
        else:
            return data
    
    def _sanitize_key(self, key: str) -> str:
        """Sanitize dictionary key."""
        # Remove special characters from keys
        return re.sub(r'[^\w.-]', '_', str(key))
    
    def _sanitize_html_output(self, data: str) -> str:
        """Sanitize HTML output."""
        return html.escape(str(data))
    
    def _sanitize_text_output(self, data: str) -> str:
        """Sanitize plain text output."""
        # Remove control characters
        return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(data))