"""
Feedback service implementation.

Handles user feedback collection including search quality feedback,
usage signals, and analytics data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from src.database.manager import DatabaseManager
from src.api.schemas import (
    FeedbackRequest, FeedbackResponse,
    UsageSignalRequest, FeedbackStatsResponse
)


class FeedbackService:
    """Service for handling feedback and usage signal collection."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the feedback service.
        
        Args:
            db_manager: Optional DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
    
    async def submit_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        """
        Submit user feedback for a search result or content item.
        
        Args:
            request: Feedback request with rating and comments
            
        Returns:
            FeedbackResponse confirming submission
        """
        if not self.db_manager:
            return FeedbackResponse(
                feedback_id="",
                status="failed",
                message="Database manager not available"
            )
        
        try:
            # Generate unique feedback ID
            feedback_id = str(uuid.uuid4())
            
            # Insert feedback into database
            query = """
            INSERT INTO feedback_events (
                feedback_id, content_id, user_id, session_id,
                feedback_type, rating, comment, metadata,
                created_at
            ) VALUES (
                :feedback_id, :content_id, :user_id, :session_id,
                :feedback_type, :rating, :comment, :metadata,
                :created_at
            )
            """
            
            params = {
                "feedback_id": feedback_id,
                "content_id": request.content_id,
                "user_id": request.user_id or "anonymous",
                "session_id": request.session_id or str(uuid.uuid4()),
                "feedback_type": request.feedback_type,
                "rating": request.rating,
                "comment": request.comment,
                "metadata": request.metadata or {},
                "created_at": datetime.utcnow()
            }
            
            await self.db_manager.execute(query, params)
            
            return FeedbackResponse(
                feedback_id=feedback_id,
                status="accepted",
                message="Feedback recorded successfully"
            )
            
        except Exception as e:
            return FeedbackResponse(
                feedback_id="",
                status="failed",
                message=f"Failed to record feedback: {str(e)}"
            )
    
    async def record_usage_signal(self, request: UsageSignalRequest) -> FeedbackResponse:
        """
        Record a usage signal (view, click, etc.).
        
        Args:
            request: Usage signal request with event details
            
        Returns:
            FeedbackResponse confirming recording
        """
        if not self.db_manager:
            return FeedbackResponse(
                feedback_id="",
                status="failed",
                message="Database manager not available"
            )
        
        try:
            # Generate unique signal ID
            signal_id = str(uuid.uuid4())
            
            # Insert usage signal into database
            query = """
            INSERT INTO usage_signals (
                signal_id, content_id, user_id, session_id,
                signal_type, signal_strength, metadata,
                created_at
            ) VALUES (
                :signal_id, :content_id, :user_id, :session_id,
                :signal_type, :signal_strength, :metadata,
                :created_at
            )
            """
            
            params = {
                "signal_id": signal_id,
                "content_id": request.content_id,
                "user_id": request.user_id or "anonymous",
                "session_id": request.session_id or str(uuid.uuid4()),
                "signal_type": request.signal_type,
                "signal_strength": request.signal_strength or 1.0,
                "metadata": request.metadata or {},
                "created_at": datetime.utcnow()
            }
            
            await self.db_manager.execute(query, params)
            
            return FeedbackResponse(
                feedback_id=signal_id,
                status="accepted",
                message="Usage signal recorded"
            )
            
        except Exception as e:
            return FeedbackResponse(
                feedback_id="",
                status="failed",
                message=f"Failed to record usage signal: {str(e)}"
            )
    
    async def get_feedback_stats(self, days: int = 30) -> FeedbackStatsResponse:
        """
        Get feedback statistics for the specified time period.
        
        Args:
            days: Number of days to include in statistics (default: 30)
            
        Returns:
            FeedbackStatsResponse with feedback statistics
        """
        if not self.db_manager:
            return FeedbackStatsResponse(
                total_feedback=0,
                average_rating=0.0,
                by_type={},
                by_rating={},
                recent_feedback=[]
            )
        
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total feedback count
            total_query = """
            SELECT COUNT(*) as count
            FROM feedback_events
            WHERE created_at >= :start_date AND created_at <= :end_date
            """
            total_result = await self.db_manager.fetch_one(
                total_query, 
                {"start_date": start_date, "end_date": end_date}
            )
            total_feedback = total_result["count"] if total_result else 0
            
            # Get average rating
            avg_query = """
            SELECT AVG(rating) as avg_rating
            FROM feedback_events
            WHERE created_at >= :start_date AND created_at <= :end_date
                AND rating IS NOT NULL
            """
            avg_result = await self.db_manager.fetch_one(
                avg_query,
                {"start_date": start_date, "end_date": end_date}
            )
            average_rating = float(avg_result["avg_rating"]) if avg_result and avg_result["avg_rating"] else 0.0
            
            # Get feedback by type
            type_query = """
            SELECT feedback_type, COUNT(*) as count
            FROM feedback_events
            WHERE created_at >= :start_date AND created_at <= :end_date
            GROUP BY feedback_type
            """
            type_results = await self.db_manager.fetch_all(
                type_query,
                {"start_date": start_date, "end_date": end_date}
            )
            by_type = {row["feedback_type"]: row["count"] for row in type_results}
            
            # Get feedback by rating
            rating_query = """
            SELECT rating, COUNT(*) as count
            FROM feedback_events
            WHERE created_at >= :start_date AND created_at <= :end_date
                AND rating IS NOT NULL
            GROUP BY rating
            ORDER BY rating
            """
            rating_results = await self.db_manager.fetch_all(
                rating_query,
                {"start_date": start_date, "end_date": end_date}
            )
            by_rating = {str(row["rating"]): row["count"] for row in rating_results}
            
            # Get recent feedback
            recent_query = """
            SELECT feedback_id, content_id, feedback_type, rating, comment, created_at
            FROM feedback_events
            WHERE created_at >= :start_date AND created_at <= :end_date
            ORDER BY created_at DESC
            LIMIT 10
            """
            recent_results = await self.db_manager.fetch_all(
                recent_query,
                {"start_date": start_date, "end_date": end_date}
            )
            
            recent_feedback = []
            for row in recent_results:
                recent_feedback.append({
                    "feedback_id": row["feedback_id"],
                    "content_id": row["content_id"],
                    "feedback_type": row["feedback_type"],
                    "rating": row["rating"],
                    "comment": row["comment"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            
            return FeedbackStatsResponse(
                total_feedback=total_feedback,
                average_rating=average_rating,
                by_type=by_type,
                by_rating=by_rating,
                recent_feedback=recent_feedback
            )
            
        except Exception:
            return FeedbackStatsResponse(
                total_feedback=0,
                average_rating=0.0,
                by_type={},
                by_rating={},
                recent_feedback=[]
            )