"""API Gateway router for Web UI Service."""

from fastapi import APIRouter, Depends, HTTPException, status
from src.web_ui.api_gateway.schemas import HealthResponse, StatsResponse, ConfigResponse, ContentResponse
from src.web_ui.data_service.service import DataService
from src.web_ui.view_model_service.service import ViewModelService
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Database session dependency (simple example, production should use a pool)
DATABASE_URL = os.getenv("WEB_UI_DATABASE_URL", "sqlite+aiosqlite:///./web_ui.db")
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_data_service(db: AsyncSession = Depends(get_db)):
    return DataService(db_session=db)

def get_view_model_service(data_service: DataService = Depends(get_data_service)):
    return ViewModelService(data_service=data_service)

@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for service monitoring."""
    # TODO: IMPLEMENTATION ENGINEER - Implement health check logic
    try:
        # Example: check DB connection
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return HealthResponse(status="ok")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@api_router.get("/stats", response_model=StatsResponse)
async def get_stats(data_service: DataService = Depends(get_data_service)):
    """Get system statistics for the UI."""
    # TODO: IMPLEMENTATION ENGINEER - Fetch and return stats from DataService
    try:
        stats = await data_service.fetch_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")

@api_router.get("/config", response_model=ConfigResponse)
async def get_config(data_service: DataService = Depends(get_data_service)):
    """Get current configuration for the UI."""
    # TODO: IMPLEMENTATION ENGINEER - Fetch and return config from DataService
    try:
        config = await data_service.fetch_config()
        return ConfigResponse(config=config)
    except Exception as e:
        logger.error(f"Failed to fetch config: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch config")

@api_router.get("/content", response_model=ContentResponse)
async def get_content(view_model_service: ViewModelService = Depends(get_view_model_service)):
    """Get content for the UI."""
    # TODO: IMPLEMENTATION ENGINEER - Fetch and return content from ViewModelService
    try:
        content = await view_model_service.get_content_view_model()
        return ContentResponse(content=content)
    except Exception as e:
        logger.error(f"Failed to fetch content: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch content")

@api_router.get("/collections")
async def get_collections(data_service: DataService = Depends(get_data_service)):
    """Get collections for the UI."""
    try:
        collections = await data_service.fetch_collections()
        return collections
    except Exception as e:
        logger.error(f"Failed to fetch collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch collections")

@api_router.post("/config")
async def update_config(config: dict, data_service: DataService = Depends(get_data_service)):
    """Update configuration."""
    try:
        updated_config = await data_service.update_config(config)
        return updated_config
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update config")

@api_router.get("/admin/search-content")
async def admin_search_content(data_service: DataService = Depends(get_data_service)):
    """Admin endpoint for searching content."""
    try:
        results = await data_service.admin_search_content()
        return results
    except Exception as e:
        logger.error(f"Failed to search content: {e}")
        raise HTTPException(status_code=500, detail="Failed to search content")

@api_router.delete("/content/{content_id}")
async def delete_content(content_id: str, data_service: DataService = Depends(get_data_service)):
    """Delete/flag content for removal."""
    try:
        result = await data_service.delete_content(content_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete content: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete content")</search>
</search_and_replace>