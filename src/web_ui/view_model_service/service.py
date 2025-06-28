"""View Model Service for Web UI."""

from src.web_ui.data_service.service import DataService
import logging

logger = logging.getLogger(__name__)


class ViewModelService:
    def __init__(self, data_service: DataService):
        self.data_service = data_service

    async def get_content_view_model(self) -> dict:
        """Get the view model for the content page."""
        logger.info("Getting content view model")
        # Placeholder implementation
        content_data = await self.data_service.fetch_collections()
        return {"title": "Content Dashboard", "collections": content_data}
