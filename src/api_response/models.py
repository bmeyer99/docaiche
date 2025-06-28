"""
Pydantic models for the API Response Pipeline.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class CachedResponse(BaseModel):
    """
    Represents a cached response.
    """

    key: str = Field(..., description="The cache key for the response.")
    value: Any = Field(..., description="The cached response data.")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="The timestamp when the cache entry was created.",
    )
    ttl: Optional[int] = Field(
        None, description="The time-to-live for the cache entry in seconds."
    )

    @model_validator(mode="before")
    @classmethod
    def ensure_created_at(cls, values):
        """
        Ensure that the created_at field is set.
        """
        if "created_at" not in values:
            values["created_at"] = datetime.utcnow()
        return values

    def is_expired(self) -> bool:
        """
        Check if the cache entry has expired.
        """
        if self.ttl is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl)
