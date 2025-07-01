"""
Configuration Audit Log Service

Provides functionality for logging and retrieving configuration changes
with proper audit trail capabilities.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.sql import func

from .models import ConfigurationAuditLog

logger = logging.getLogger(__name__)


class ConfigurationAuditService:
    """Service for managing configuration audit logs."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def log_configuration_change(
        self,
        user: str,
        section: str,
        changes: Dict[str, Any],
        previous_values: Dict[str, Any],
        comment: Optional[str] = None
    ) -> str:
        """
        Log a configuration change to the audit log.
        
        Args:
            user: User who made the change
            section: Configuration section that was changed
            changes: New values that were applied
            previous_values: Previous values before the change
            comment: Optional comment about the change
            
        Returns:
            The audit log entry ID
        """
        try:
            audit_id = str(uuid.uuid4())
            
            audit_entry = ConfigurationAuditLog(
                id=audit_id,
                timestamp=datetime.utcnow(),
                user=user,
                section=section,
                changes=changes,
                previous_values=previous_values,
                comment=comment
            )
            
            self.db_session.add(audit_entry)
            await self.db_session.commit()
            
            logger.info(
                f"Configuration change logged: {audit_id} by {user} in section {section}"
            )
            
            return audit_id
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to log configuration change: {e}")
            raise
    
    async def get_configuration_history(
        self,
        limit: int = 50,
        offset: int = 0,
        section: Optional[str] = None
    ) -> List[ConfigurationAuditLog]:
        """
        Retrieve configuration change history.
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            section: Optional filter by configuration section
            
        Returns:
            List of configuration audit log entries
        """
        try:
            query = select(ConfigurationAuditLog).order_by(
                desc(ConfigurationAuditLog.timestamp)
            )
            
            if section:
                query = query.where(ConfigurationAuditLog.section == section)
            
            query = query.limit(limit).offset(offset)
            
            result = await self.db_session.execute(query)
            entries = result.scalars().all()
            
            logger.debug(f"Retrieved {len(entries)} configuration history entries")
            
            return list(entries)
            
        except Exception as e:
            logger.error(f"Failed to retrieve configuration history: {e}")
            raise
    
    async def get_configuration_history_count(
        self,
        section: Optional[str] = None
    ) -> int:
        """
        Get total count of configuration history entries.
        
        Args:
            section: Optional filter by configuration section
            
        Returns:
            Total number of audit log entries
        """
        try:
            query = select(func.count(ConfigurationAuditLog.id))
            
            if section:
                query = query.where(ConfigurationAuditLog.section == section)
            
            result = await self.db_session.execute(query)
            count = result.scalar()
            
            return count or 0
            
        except Exception as e:
            logger.error(f"Failed to get configuration history count: {e}")
            raise
    
    async def get_user_configuration_changes(
        self,
        user: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConfigurationAuditLog]:
        """
        Get configuration changes made by a specific user.
        
        Args:
            user: User to filter by
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List of configuration audit log entries for the user
        """
        try:
            query = select(ConfigurationAuditLog).where(
                ConfigurationAuditLog.user == user
            ).order_by(desc(ConfigurationAuditLog.timestamp)).limit(limit).offset(offset)
            
            result = await self.db_session.execute(query)
            entries = result.scalars().all()
            
            logger.debug(f"Retrieved {len(entries)} configuration changes for user {user}")
            
            return list(entries)
            
        except Exception as e:
            logger.error(f"Failed to retrieve user configuration changes: {e}")
            raise