"""
Prompt Template Repository
==========================

Database repository for managing prompt templates with version control.
"""

import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database.manager import DatabaseManager
from src.mcp.text_ai.prompts import PromptType, DEFAULT_TEMPLATES

logger = logging.getLogger(__name__)


class PromptTemplateRepository:
    """
    Repository for managing prompt templates in the database.
    
    Handles CRUD operations for prompt templates with version control
    and initialization from default templates.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the repository with a database manager.
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
    
    async def initialize_default_templates(self) -> None:
        """
        Initialize database with default templates if not present.
        
        Creates entries for all 10 prompt types with their default values
        from the DEFAULT_TEMPLATES dictionary.
        """
        try:
            async with self.db_manager.transaction() as session:
                # Check if templates already exist
                result = await session.execute(
                    text("SELECT COUNT(*) as count FROM prompt_templates")
                )
                count = result.scalar()
                
                if count == 0:
                    logger.info("Initializing default prompt templates...")
                    
                    for prompt_type, template_content in DEFAULT_TEMPLATES.items():
                        template_id = str(uuid.uuid4())
                        
                        # Extract metadata from the template
                        metadata = {
                            "required_variables": self._extract_variables(template_content),
                            "output_format": "json" if "JSON" in template_content else "text",
                            "temperature_recommendation": 0.3 if prompt_type in [
                                PromptType.QUERY_UNDERSTANDING,
                                PromptType.RESULT_RELEVANCE,
                                PromptType.EXTERNAL_SEARCH_DECISION,
                                PromptType.PROVIDER_SELECTION,
                                PromptType.FAILURE_ANALYSIS
                            ] else 0.7,
                            "max_tokens_recommendation": 2000,
                            "active": True,
                            "notes": f"Default template for {prompt_type.value}"
                        }
                        
                        await session.execute(
                            text("""
                                INSERT INTO prompt_templates 
                                (id, prompt_type, content, metadata, version, created_at, updated_at)
                                VALUES (:id, :prompt_type, :content, :metadata, :version, :created_at, :updated_at)
                            """),
                            {
                                "id": template_id,
                                "prompt_type": prompt_type.value,
                                "content": template_content,
                                "metadata": json.dumps(metadata),
                                "version": "1.0.0",
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            }
                        )
                    
                    logger.info("Default prompt templates initialized successfully")
                else:
                    logger.info(f"Found {count} existing prompt templates, skipping initialization")
                    
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize default templates: {e}")
            raise
    
    async def get_all_prompts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all prompt templates from the database.
        
        Args:
            active_only: If True, only return active prompts
            
        Returns:
            List of prompt dictionaries with all fields
        """
        try:
            query = """
                SELECT id, prompt_type, content, metadata, version, created_at, updated_at
                FROM prompt_templates
                ORDER BY prompt_type, version DESC
            """
            
            if active_only:
                # For active only, get the latest version of each prompt type
                query = """
                    SELECT DISTINCT ON (prompt_type) 
                        id, prompt_type, content, metadata, version, created_at, updated_at
                    FROM prompt_templates
                    ORDER BY prompt_type, version DESC
                """
            
            rows = await self.db_manager.fetch_all(query)
            
            prompts = []
            for row in rows:
                metadata = json.loads(row.metadata) if row.metadata else {}
                
                # Only include active prompts if requested
                if active_only and not metadata.get("active", True):
                    continue
                
                prompts.append({
                    "id": row.id,
                    "prompt_type": row.prompt_type,
                    "content": row.content,
                    "metadata": metadata,
                    "version": row.version,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                })
            
            return prompts
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get all prompts: {e}")
            raise
    
    async def get_prompt_by_type(self, prompt_type: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific prompt template by type and optional version.
        
        Args:
            prompt_type: The prompt type (from PromptType enum)
            version: Optional specific version, defaults to latest
            
        Returns:
            Prompt dictionary or None if not found
        """
        try:
            if version:
                query = text("""
                    SELECT id, prompt_type, content, metadata, version, created_at, updated_at
                    FROM prompt_templates
                    WHERE prompt_type = :prompt_type AND version = :version
                """)
                params = {"prompt_type": prompt_type, "version": version}
            else:
                # Get the latest version
                query = text("""
                    SELECT id, prompt_type, content, metadata, version, created_at, updated_at
                    FROM prompt_templates
                    WHERE prompt_type = :prompt_type
                    ORDER BY version DESC
                    LIMIT 1
                """)
                params = {"prompt_type": prompt_type}
            
            result = await self.db_manager.fetch_one(query.text, tuple(params.values()))
            
            if result:
                metadata = json.loads(result.metadata) if result.metadata else {}
                return {
                    "id": result.id,
                    "prompt_type": result.prompt_type,
                    "content": result.content,
                    "metadata": metadata,
                    "version": result.version,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None
                }
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get prompt by type {prompt_type}: {e}")
            raise
    
    async def update_prompt(self, prompt_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update a prompt template, creating a new version.
        
        Args:
            prompt_type: The prompt type to update
            content: New prompt content
            metadata: Optional metadata updates
            
        Returns:
            Updated prompt dictionary with new version
        """
        try:
            async with self.db_manager.transaction() as session:
                # Get current latest version
                result = await session.execute(
                    text("""
                        SELECT version, metadata
                        FROM prompt_templates
                        WHERE prompt_type = :prompt_type
                        ORDER BY version DESC
                        LIMIT 1
                    """),
                    {"prompt_type": prompt_type}
                )
                current = result.first()
                
                if not current:
                    # No existing prompt, create as 1.0.0
                    new_version = "1.0.0"
                    current_metadata = {}
                else:
                    # Increment version
                    new_version = self._increment_version(current.version)
                    current_metadata = json.loads(current.metadata) if current.metadata else {}
                
                # Merge metadata
                if metadata:
                    current_metadata.update(metadata)
                
                # Update required variables based on new content
                current_metadata["required_variables"] = self._extract_variables(content)
                current_metadata["updated_at"] = datetime.utcnow().isoformat()
                
                # Create new version
                new_id = str(uuid.uuid4())
                now = datetime.utcnow()
                
                await session.execute(
                    text("""
                        INSERT INTO prompt_templates 
                        (id, prompt_type, content, metadata, version, created_at, updated_at)
                        VALUES (:id, :prompt_type, :content, :metadata, :version, :created_at, :updated_at)
                    """),
                    {
                        "id": new_id,
                        "prompt_type": prompt_type,
                        "content": content,
                        "metadata": json.dumps(current_metadata),
                        "version": new_version,
                        "created_at": now,
                        "updated_at": now
                    }
                )
                
                return {
                    "id": new_id,
                    "prompt_type": prompt_type,
                    "content": content,
                    "metadata": current_metadata,
                    "version": new_version,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to update prompt {prompt_type}: {e}")
            raise
    
    async def get_prompt_versions(self, prompt_type: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a specific prompt type.
        
        Args:
            prompt_type: The prompt type to get versions for
            
        Returns:
            List of prompt versions ordered by version descending
        """
        try:
            query = text("""
                SELECT id, prompt_type, content, metadata, version, created_at, updated_at
                FROM prompt_templates
                WHERE prompt_type = :prompt_type
                ORDER BY version DESC
            """)
            
            rows = await self.db_manager.fetch_all(query.text, (prompt_type,))
            
            versions = []
            for row in rows:
                metadata = json.loads(row.metadata) if row.metadata else {}
                versions.append({
                    "id": row.id,
                    "prompt_type": row.prompt_type,
                    "content": row.content,
                    "metadata": metadata,
                    "version": row.version,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                })
            
            return versions
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get versions for prompt {prompt_type}: {e}")
            raise
    
    def _extract_variables(self, template_content: str) -> List[str]:
        """
        Extract variable names from template content.
        
        Args:
            template_content: Template string with {variable} placeholders
            
        Returns:
            List of variable names found in the template
        """
        import re
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, template_content)))
    
    def _increment_version(self, version: str) -> str:
        """
        Increment a semantic version string.
        
        Args:
            version: Current version (e.g., "1.0.0")
            
        Returns:
            Incremented version (e.g., "1.0.1")
        """
        parts = version.split(".")
        if len(parts) != 3:
            return "1.0.1"
        
        try:
            major, minor, patch = map(int, parts)
            patch += 1
            return f"{major}.{minor}.{patch}"
        except ValueError:
            return "1.0.1"