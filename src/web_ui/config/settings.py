from pydantic_settings import BaseSettings
from pydantic import Field


class WebUISettings(BaseSettings):
    """
    Settings for the Web UI service.
    """

    allowed_origins: str = Field(default="*", description="CORS allowed origins")

    class Config:
        env_prefix = "WEB_UI_"

    # Add any Web UI specific settings here
