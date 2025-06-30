"""
Loki client wrapper for AI-optimized log queries.

This module provides a simplified interface for querying Loki with
AI-specific optimizations and enhanced error handling.
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode
import json

logger = logging.getLogger(__name__)


class LokiClient:
    """
    Async client for Loki log queries with AI-specific optimizations.
    """
    
    def __init__(self, 
                 base_url: str = "http://loki:3100",
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        Initialize Loki client.
        
        Args:
            base_url: Loki server URL
            timeout: Query timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def ensure_session(self):
        """Ensure session is initialized."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def query_range(self, 
                         logql: str,
                         start_time: datetime,
                         end_time: datetime,
                         limit: int = 1000,
                         direction: str = "backward") -> List[Dict[str, Any]]:
        """
        Execute a range query against Loki.
        
        Args:
            logql: LogQL query string
            start_time: Query start time
            end_time: Query end time
            limit: Maximum number of log lines
            direction: Query direction (forward/backward)
            
        Returns:
            List of log entries
        """
        await self.ensure_session()
        
        # Build query parameters
        params = {
            "query": logql,
            "start": int(start_time.timestamp() * 1e9),  # Nanoseconds
            "end": int(end_time.timestamp() * 1e9),
            "limit": limit,
            "direction": direction
        }
        
        url = f"{self.base_url}/loki/api/v1/query_range"
        
        # Execute query with retries
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = min(2 ** attempt, 10)
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Loki query failed: {response.status} - {error_text}")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"Loki query failed: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.error(f"Loki query timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Loki query error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                    
        return []
    
    async def query_instant(self,
                           logql: str,
                           time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Execute an instant query against Loki.
        
        Args:
            logql: LogQL query string
            time: Query time (default: now)
            
        Returns:
            List of log entries
        """
        await self.ensure_session()
        
        if time is None:
            time = datetime.utcnow()
            
        params = {
            "query": logql,
            "time": int(time.timestamp() * 1e9)
        }
        
        url = f"{self.base_url}/loki/api/v1/query"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_response(data)
                else:
                    error_text = await response.text()
                    raise Exception(f"Loki instant query failed: {error_text}")
        except Exception as e:
            logger.error(f"Loki instant query error: {e}")
            raise
    
    async def labels(self, 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[str]:
        """
        Get available labels from Loki.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of label names
        """
        await self.ensure_session()
        
        url = f"{self.base_url}/loki/api/v1/labels"
        params = {}
        
        if start_time:
            params["start"] = int(start_time.timestamp() * 1e9)
        if end_time:
            params["end"] = int(end_time.timestamp() * 1e9)
            
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to get labels: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return []
    
    async def label_values(self,
                          label: str,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[str]:
        """
        Get values for a specific label.
        
        Args:
            label: Label name
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of label values
        """
        await self.ensure_session()
        
        url = f"{self.base_url}/loki/api/v1/label/{label}/values"
        params = {}
        
        if start_time:
            params["start"] = int(start_time.timestamp() * 1e9)
        if end_time:
            params["end"] = int(end_time.timestamp() * 1e9)
            
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to get label values: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting label values: {e}")
            return []
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Loki query response into standardized format.
        
        Args:
            data: Raw Loki response
            
        Returns:
            List of parsed log entries
        """
        logs = []
        
        if data.get("status") != "success":
            logger.error(f"Loki query failed: {data}")
            return logs
            
        results = data.get("data", {}).get("result", [])
        
        for result in results:
            stream = result.get("stream", {})
            values = result.get("values", [])
            
            for timestamp_ns, line in values:
                # Convert nanosecond timestamp to datetime
                timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)
                
                # Try to parse JSON log line
                log_data = {}
                try:
                    log_data = json.loads(line)
                except json.JSONDecodeError:
                    log_data = {"message": line}
                
                # Merge stream labels and log data
                log_entry = {
                    "timestamp": timestamp,
                    "labels": stream,
                    **log_data
                }
                
                # Extract common fields
                log_entry["level"] = log_data.get("level", stream.get("level", "info"))
                log_entry["service"] = stream.get("service", stream.get("service_name", "unknown"))
                
                # AI-specific fields
                for field in ["correlation_id", "conversation_id", "workspace_id", 
                             "model", "tokens_used", "duration", "request_type"]:
                    if field in log_data:
                        log_entry[field] = log_data[field]
                    elif field in stream:
                        log_entry[field] = stream[field]
                
                logs.append(log_entry)
        
        return logs
    
    async def get_services(self,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[str]:
        """
        Get list of available services.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of service names
        """
        # Try multiple label names that might contain service info
        service_labels = ["service", "service_name", "container_name"]
        services = set()
        
        for label in service_labels:
            values = await self.label_values(label, start_time, end_time)
            services.update(values)
            
        # Filter out common non-service values
        exclude = {"", "unknown", "null", "undefined"}
        return sorted([s for s in services if s not in exclude])
    
    async def test_connection(self) -> bool:
        """
        Test connection to Loki.
        
        Returns:
            True if connection successful
        """
        await self.ensure_session()
        
        try:
            url = f"{self.base_url}/ready"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Loki connection test failed: {e}")
            return False
    
    def build_logql_query(self,
                         services: List[str] = None,
                         filters: Dict[str, Any] = None,
                         search_text: str = None) -> str:
        """
        Build a LogQL query from parameters.
        
        Args:
            services: List of services to query
            filters: Label filters
            search_text: Text to search for
            
        Returns:
            LogQL query string
        """
        # Start with base selector
        selectors = ['job="docaiche"']
        
        # Add service filter
        if services and "all" not in services:
            service_regex = "|".join(services)
            selectors.append(f'service=~"({service_regex})"')
            
        # Add other label filters
        if filters:
            for key, value in filters.items():
                if value is not None and value != "":
                    selectors.append(f'{key}="{value}"')
        
        # Build base query
        query = "{" + ", ".join(selectors) + "}"
        
        # Add text search
        if search_text:
            query += f' |~ "{search_text}"'
            
        return query
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None


class LokiAIQueryBuilder:
    """
    Specialized query builder for AI-related log queries.
    """
    
    @staticmethod
    def build_conversation_query(conversation_id: str,
                                include_context: bool = True) -> str:
        """Build query for conversation logs."""
        base = f'{{job="docaiche", conversation_id="{conversation_id}"}}'
        
        if include_context:
            # Also include correlated requests
            base = f'{{job="docaiche"}} |~ "conversation_id={conversation_id}"'
            
        return base
    
    @staticmethod
    def build_correlation_query(correlation_id: str) -> str:
        """Build query for correlated logs across services."""
        return f'{{job="docaiche"}} |~ "correlation_id={correlation_id}"'
    
    @staticmethod
    def build_workspace_query(workspace_id: str,
                             ai_only: bool = True) -> str:
        """Build query for workspace logs."""
        query = f'{{job="docaiche", workspace_id="{workspace_id}"}}'
        
        if ai_only:
            query += ' |~ "(ai_event|request_type=ai_completion|model=)"'
            
        return query
    
    @staticmethod
    def build_error_query(services: List[str] = None,
                         error_patterns: List[str] = None) -> str:
        """Build query for error logs."""
        # Base error query
        if services and "all" not in services:
            service_regex = "|".join(services)
            query = f'{{job="docaiche", service=~"({service_regex})"}} |~ "(error|ERROR|Error|fatal|FATAL|Fatal)"'
        else:
            query = '{job="docaiche"} |~ "(error|ERROR|Error|fatal|FATAL|Fatal)"'
        
        # Add specific error patterns
        if error_patterns:
            pattern_regex = "|".join(error_patterns)
            query += f' |~ "({pattern_regex})"'
            
        return query
    
    @staticmethod
    def build_performance_query(services: List[str] = None,
                               threshold_ms: int = 1000) -> str:
        """Build query for performance analysis."""
        if services and "all" not in services:
            service_regex = "|".join(services)
            base = f'{{job="docaiche", service=~"({service_regex})"}}'
        else:
            base = '{job="docaiche"}'
            
        # Look for duration fields
        query = base + ' | json | duration > ' + str(threshold_ms)
        
        return query