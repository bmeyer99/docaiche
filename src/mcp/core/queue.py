"""
Queue Management Interfaces
===========================

Abstract interfaces for priority-based queue management with
overflow protection and rate limiting.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

from .models import SearchRequest, UserContext, QueueStats


class QueuePriority(Enum):
    """Priority levels for queue ordering."""
    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BATCH = 4  # Lowest priority


class QueueStatus(Enum):
    """Queue operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    PAUSED = "paused"


class QueueManager(ABC):
    """
    Abstract interface for queue management with overflow protection.
    
    Manages search request queuing with priority ordering, rate limiting,
    and overflow handling as specified in PLAN.md.
    """
    
    @abstractmethod
    async def enqueue(
        self,
        request: SearchRequest,
        priority: QueuePriority = QueuePriority.NORMAL
    ) -> Tuple[bool, Optional[str]]:
        """
        Enqueue a search request with overflow protection.
        
        Must implement:
        - Queue depth checking against max_queue_depth
        - Priority-based insertion
        - Rate limit enforcement
        - Overflow response (503) when full
        
        Args:
            request: Search request to enqueue
            priority: Request priority level
            
        Returns:
            Tuple of (success, queue_id or error_message)
            
        Raises:
            QueueOverflowError: When queue is at capacity
            RateLimitExceededError: When rate limits exceeded
        """
        pass
    
    @abstractmethod
    async def dequeue(self, max_items: int = 1) -> List[SearchRequest]:
        """
        Dequeue requests by priority.
        
        Must implement:
        - Priority-based retrieval
        - Batch dequeuing support
        - Request age consideration
        - Fair queuing between users/workspaces
        
        Args:
            max_items: Maximum items to dequeue
            
        Returns:
            List of dequeued requests (may be empty)
        """
        pass
    
    @abstractmethod
    async def get_queue_depth(self) -> int:
        """
        Get current queue depth.
        
        Returns:
            Number of requests currently in queue
        """
        pass
    
    @abstractmethod
    async def get_queue_stats(self) -> QueueStats:
        """
        Get comprehensive queue statistics.
        
        Must include:
        - Current depth by priority
        - Average wait times
        - Overflow count
        - Rate limit hits
        - Request distribution
        
        Returns:
            QueueStats with monitoring metrics
        """
        pass
    
    @abstractmethod
    async def check_overload_status(self) -> QueueStatus:
        """
        Check current queue overload status.
        
        Must implement:
        - Depth threshold checking
        - Rate limit status
        - System resource checks
        - Degradation detection
        
        Returns:
            Current queue status
        """
        pass
    
    @abstractmethod
    async def check_rate_limits(
        self,
        user_context: UserContext
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if request would exceed rate limits.
        
        Must check:
        - Per-user rate limits
        - Per-workspace rate limits
        - Global rate limits
        - Burst allowances
        
        Args:
            user_context: User and workspace information
            
        Returns:
            Tuple of (allowed, limit_info or None)
        """
        pass
    
    @abstractmethod
    async def pause_processing(self, reason: str) -> None:
        """
        Pause queue processing.
        
        Args:
            reason: Reason for pausing
        """
        pass
    
    @abstractmethod
    async def resume_processing(self) -> None:
        """Resume queue processing after pause."""
        pass
    
    @abstractmethod
    async def clear_queue(self, priority: Optional[QueuePriority] = None) -> int:
        """
        Clear queued requests.
        
        Args:
            priority: Clear only specific priority (None = all)
            
        Returns:
            Number of requests cleared
        """
        pass
    
    @abstractmethod
    async def get_position(self, queue_id: str) -> Optional[int]:
        """
        Get position of request in queue.
        
        Args:
            queue_id: Queue ID from enqueue
            
        Returns:
            Position in queue (0-based) or None if not found
        """
        pass


class PriorityQueue(ABC):
    """
    Abstract interface for priority-based request ordering.
    
    Implements the queue storage and ordering logic with
    support for different prioritization strategies.
    """
    
    @abstractmethod
    async def add(
        self,
        request: SearchRequest,
        priority: QueuePriority,
        queue_id: str
    ) -> None:
        """
        Add request to priority queue.
        
        Must implement:
        - Priority-based insertion
        - Timestamp tracking
        - Queue ID assignment
        
        Args:
            request: Search request
            priority: Request priority
            queue_id: Unique queue identifier
        """
        pass
    
    @abstractmethod
    async def remove(self, queue_id: str) -> Optional[SearchRequest]:
        """
        Remove specific request from queue.
        
        Args:
            queue_id: Queue ID to remove
            
        Returns:
            Removed request or None if not found
        """
        pass
    
    @abstractmethod
    async def peek(self, count: int = 1) -> List[Tuple[SearchRequest, QueuePriority, str]]:
        """
        Peek at next requests without removing.
        
        Args:
            count: Number of requests to peek
            
        Returns:
            List of (request, priority, queue_id) tuples
        """
        pass
    
    @abstractmethod
    async def pop(self, count: int = 1) -> List[Tuple[SearchRequest, QueuePriority, str]]:
        """
        Remove and return next requests.
        
        Must implement:
        - Priority order retrieval
        - Age-based tie breaking
        - Atomic removal
        
        Args:
            count: Number of requests to pop
            
        Returns:
            List of (request, priority, queue_id) tuples
        """
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """
        Get total queue size.
        
        Returns:
            Total number of queued requests
        """
        pass
    
    @abstractmethod
    async def size_by_priority(self) -> Dict[QueuePriority, int]:
        """
        Get queue size breakdown by priority.
        
        Returns:
            Dictionary mapping priority to count
        """
        pass
    
    @abstractmethod
    async def get_wait_times(self) -> Dict[QueuePriority, float]:
        """
        Get average wait times by priority.
        
        Returns:
            Dictionary mapping priority to average wait seconds
        """
        pass
    
    @abstractmethod
    async def reorder(self, strategy: str = "priority_age") -> None:
        """
        Reorder queue based on strategy.
        
        Strategies:
        - "priority_age": Priority first, then age
        - "fair_share": Balance between users/workspaces
        - "deadline": Urgent requests first
        
        Args:
            strategy: Reordering strategy
        """
        pass
    
    @abstractmethod
    async def expire_old_requests(self, max_age_seconds: int) -> List[str]:
        """
        Remove requests older than threshold.
        
        Args:
            max_age_seconds: Maximum age before expiration
            
        Returns:
            List of expired queue IDs
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get detailed queue metrics.
        
        Must include:
        - Size by priority
        - Age distribution
        - User/workspace distribution
        - Wait time percentiles
        
        Returns:
            Dictionary of queue metrics
        """
        pass