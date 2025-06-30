"""
Mock Pydantic Implementation
===========================

Minimal pydantic mock for environments where pydantic is not available.
Provides basic functionality for MCP schemas.
"""

from typing import Any, Dict, Optional, Type, TypeVar, get_type_hints
from dataclasses import dataclass, field, asdict
import json

T = TypeVar('T')


class Field:
    """Mock pydantic Field."""
    
    def __init__(self, default=None, description="", alias=None, **kwargs):
        self.default = default
        self.description = description
        self.alias = alias
        self.kwargs = kwargs
    
    def __call__(self, *args, **kwargs):
        return self.default


def validator(*fields, **kwargs):
    """Mock validator decorator."""
    def decorator(func):
        return func
    return decorator


class BaseModel:
    """Mock pydantic BaseModel."""
    
    def __init__(self, **data):
        # Simple attribute assignment
        for key, value in data.items():
            setattr(self, key, value)
        
        # Set defaults for missing fields
        hints = get_type_hints(self.__class__)
        for field_name, field_type in hints.items():
            if not hasattr(self, field_name):
                # Check for Optional types
                if hasattr(field_type, '__origin__') and field_type.__origin__ is type(Optional):
                    setattr(self, field_name, None)
                else:
                    # Set basic defaults
                    if field_type == str:
                        setattr(self, field_name, "")
                    elif field_type == int:
                        setattr(self, field_name, 0)
                    elif field_type == bool:
                        setattr(self, field_name, False)
                    elif field_type == dict:
                        setattr(self, field_name, {})
                    elif field_type == list:
                        setattr(self, field_name, [])
    
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary."""
        exclude_none = kwargs.get('exclude_none', False)
        result = {}
        
        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                value = getattr(self, key)
                if exclude_none and value is None:
                    continue
                result[key] = value
        
        return result
    
    def json(self, **kwargs) -> str:
        """Convert to JSON string."""
        return json.dumps(self.dict(**kwargs))
    
    @classmethod
    def parse_obj(cls: Type[T], obj: Any) -> T:
        """Parse object."""
        if isinstance(obj, dict):
            return cls(**obj)
        return obj
    
    @classmethod
    def parse_raw(cls: Type[T], data: str) -> T:
        """Parse raw JSON."""
        return cls(**json.loads(data))


# Create mock pydantic module attributes
__all__ = ['BaseModel', 'Field', 'validator']