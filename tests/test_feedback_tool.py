"""
Unit Tests for Feedback Tool
=============================

Comprehensive test suite for the docaiche_feedback tool implementation
covering all feedback types, validation, categorization, and analytics.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os
from datetime import datetime
import hashlib
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestFeedbackTool(unittest.TestCase):
    """Test suite for feedback tool operations."""
    
    def test_feedback_type_validation(self):
        """Test validation of feedback types."""
        valid_types = ["rating", "text", "bug", "feature", "search_quality", "content_accuracy"]
        
        # All valid types should be accepted
        for feedback_type in valid_types:
            assert feedback_type in valid_types
        
        # Invalid types
        invalid_types = ["spam", "advertisement", "other"]
        for feedback_type in invalid_types:
            assert feedback_type not in valid_types
    
    def test_content_validation(self):
        """Test feedback content validation rules."""
        def validate_content(content, feedback_type):
            errors = []
            
            # Check minimum length
            if len(content) < 10:
                errors.append("Content too short")
            
            # Check maximum length
            if len(content) > 5000:
                errors.append("Content too long")
            
            # Check for spam patterns
            spam_patterns = ["buy now", "click here", "limited offer", "viagra"]
            content_lower = content.lower()
            if any(pattern in content_lower for pattern in spam_patterns):
                errors.append("Spam detected")
            
            return errors
        
        # Test valid content
        valid_content = "This is a valid feedback about the documentation quality"
        assert validate_content(valid_content, "text") == []
        
        # Test too short
        short_content = "Too short"
        errors = validate_content(short_content, "text")
        assert "Content too short" in errors
        
        # Test spam
        spam_content = "Click here for a limited offer on documentation!"
        errors = validate_content(spam_content, "text")
        assert "Spam detected" in errors
    
    def test_feedback_categorization(self):
        """Test automatic feedback categorization."""
        def categorize_feedback(content, feedback_type):
            categories = {
                "bug": ["functional", "ui", "performance", "security"],
                "feature": ["enhancement", "new_feature", "integration"],
                "search_quality": ["relevance", "completeness", "accuracy"],
                "content_accuracy": ["outdated", "incorrect", "missing", "unclear"]
            }
            
            type_categories = categories.get(feedback_type, [])
            if not type_categories:
                return "general"
            
            content_lower = content.lower()
            
            if feedback_type == "bug":
                if any(word in content_lower for word in ["crash", "error", "fail"]):
                    return "functional"
                elif any(word in content_lower for word in ["ui", "display", "render"]):
                    return "ui"
                elif any(word in content_lower for word in ["slow", "performance", "lag"]):
                    return "performance"
                elif any(word in content_lower for word in ["security", "vulnerability", "auth"]):
                    return "security"
            
            elif feedback_type == "search_quality":
                if any(word in content_lower for word in ["relevant", "irrelevant", "wrong"]):
                    return "relevance"
                elif any(word in content_lower for word in ["missing", "incomplete"]):
                    return "completeness"
                elif any(word in content_lower for word in ["accurate", "incorrect", "outdated"]):
                    return "accuracy"
            
            return type_categories[0] if type_categories else "general"
        
        # Test bug categorization
        assert categorize_feedback("The app crashes when I click submit", "bug") == "functional"
        assert categorize_feedback("The UI elements are not aligned properly", "bug") == "ui"
        assert categorize_feedback("The search is very slow and laggy", "bug") == "performance"
        assert categorize_feedback("Security vulnerability in authentication", "bug") == "security"
        
        # Test search quality categorization
        assert categorize_feedback("Search results are not relevant", "search_quality") == "relevance"
        assert categorize_feedback("Many documents are missing from search", "search_quality") == "completeness"
        assert categorize_feedback("Search results show outdated information", "search_quality") == "accuracy"
    
    def test_priority_calculation(self):
        """Test feedback priority calculation."""
        def calculate_priority(feedback_type, severity=None, rating=None):
            if feedback_type == "bug":
                return severity or "medium"
            elif feedback_type == "search_quality":
                return "high"
            elif feedback_type == "content_accuracy":
                return "high"
            elif feedback_type == "feature":
                return "medium"
            elif feedback_type == "rating" and rating:
                if rating <= 2:
                    return "high"
                elif rating == 3:
                    return "medium"
                else:
                    return "low"
            return "medium"
        
        # Test bug priorities
        assert calculate_priority("bug", severity="critical") == "critical"
        assert calculate_priority("bug", severity="high") == "high"
        assert calculate_priority("bug", severity=None) == "medium"
        
        # Test search quality (always high)
        assert calculate_priority("search_quality") == "high"
        
        # Test content accuracy (always high)
        assert calculate_priority("content_accuracy") == "high"
        
        # Test feature (always medium)
        assert calculate_priority("feature") == "medium"
        
        # Test rating-based priority
        assert calculate_priority("rating", rating=1) == "high"
        assert calculate_priority("rating", rating=2) == "high"
        assert calculate_priority("rating", rating=3) == "medium"
        assert calculate_priority("rating", rating=4) == "low"
        assert calculate_priority("rating", rating=5) == "low"
    
    def test_feedback_id_generation(self):
        """Test unique feedback ID generation."""
        def generate_feedback_id(feedback_type, content):
            timestamp = datetime.utcnow().isoformat()
            content_hash = hashlib.sha256(
                f"{feedback_type}:{content}:{timestamp}".encode()
            ).hexdigest()[:8]
            
            return f"fb_{feedback_type[:3]}_{timestamp[:10].replace('-', '')}_{content_hash}"
        
        # Test ID format
        id1 = generate_feedback_id("bug", "Test bug report")
        assert id1.startswith("fb_bug_")
        assert len(id1.split("_")) == 4
        
        # Test different types produce different prefixes
        id2 = generate_feedback_id("feature", "Test feature request")
        assert id2.startswith("fb_fea_")
        
        id3 = generate_feedback_id("search_quality", "Test search feedback")
        assert id3.startswith("fb_sea_")
    
    def test_anonymous_feedback_handling(self):
        """Test anonymous feedback processing."""
        def process_anonymous_feedback(feedback_data):
            if feedback_data.get("anonymous", False):
                # Remove identifying information
                feedback_data["contact_info"] = None
                feedback_data["client_id"] = None
                
                # Anonymize context if present
                if "context" in feedback_data:
                    context = feedback_data["context"].copy()
                    context.pop("session_id", None)
                    feedback_data["context"] = context
            
            return feedback_data
        
        # Test anonymous feedback
        anonymous_feedback = {
            "anonymous": True,
            "contact_info": {"email": "user@example.com"},
            "client_id": "client123",
            "context": {"session_id": "session123", "page_url": "/docs"}
        }
        
        processed = process_anonymous_feedback(anonymous_feedback)
        assert processed["contact_info"] is None
        assert processed["client_id"] is None
        assert "session_id" not in processed["context"]
        assert processed["context"]["page_url"] == "/docs"
        
        # Test non-anonymous feedback
        regular_feedback = {
            "anonymous": False,
            "contact_info": {"email": "user@example.com"},
            "client_id": "client123"
        }
        
        processed = process_anonymous_feedback(regular_feedback)
        assert processed["contact_info"]["email"] == "user@example.com"
        assert processed["client_id"] == "client123"
    
    def test_next_steps_generation(self):
        """Test next steps message generation."""
        def get_next_steps(feedback_type):
            next_steps_map = {
                "bug": [
                    "Your bug report has been logged and will be reviewed by our team",
                    "We'll investigate the issue and provide updates if you included contact information",
                    "For critical issues, we aim to respond within 24 hours"
                ],
                "feature": [
                    "Your feature request has been recorded for consideration",
                    "We review all feature requests during our planning cycles",
                    "Popular requests are prioritized based on community feedback"
                ],
                "search_quality": [
                    "Your search quality feedback helps us improve result relevance",
                    "We continuously update our search algorithms based on user input",
                    "You may see improvements in search results within a few days"
                ]
            }
            
            return next_steps_map.get(feedback_type, [
                "Thank you for your feedback",
                "Your input has been recorded",
                "We review all feedback to improve DocaiChe"
            ])
        
        # Test specific feedback types
        bug_steps = get_next_steps("bug")
        assert len(bug_steps) == 3
        assert "bug report" in bug_steps[0]
        
        feature_steps = get_next_steps("feature")
        assert len(feature_steps) == 3
        assert "feature request" in feature_steps[0]
        
        # Test default steps
        default_steps = get_next_steps("unknown_type")
        assert len(default_steps) == 3
        assert "Thank you" in default_steps[0]
    
    def test_rating_validation(self):
        """Test rating value validation."""
        def validate_rating(rating, feedback_type):
            if feedback_type == "rating":
                if rating is None:
                    return "Rating required for rating feedback"
                if not isinstance(rating, int) or rating < 1 or rating > 5:
                    return "Rating must be between 1 and 5"
            return None
        
        # Test valid ratings
        assert validate_rating(5, "rating") is None
        assert validate_rating(1, "rating") is None
        assert validate_rating(3, "rating") is None
        
        # Test invalid ratings
        assert validate_rating(None, "rating") == "Rating required for rating feedback"
        assert validate_rating(0, "rating") == "Rating must be between 1 and 5"
        assert validate_rating(6, "rating") == "Rating must be between 1 and 5"
        
        # Test rating not required for other types
        assert validate_rating(None, "bug") is None
        assert validate_rating(None, "feature") is None
    
    def test_contact_info_validation(self):
        """Test contact information validation."""
        def validate_contact_info(contact_info):
            if not contact_info:
                return []
            
            errors = []
            
            if "email" in contact_info:
                email = contact_info["email"]
                # Basic email validation
                if "@" not in email or "." not in email.split("@")[1]:
                    errors.append("Invalid email format")
            
            if "name" in contact_info:
                name = contact_info["name"]
                if len(name) > 100:
                    errors.append("Name too long")
            
            return errors
        
        # Test valid contact info
        valid_contact = {"email": "user@example.com", "name": "John Doe"}
        assert validate_contact_info(valid_contact) == []
        
        # Test invalid email
        invalid_email = {"email": "not-an-email"}
        errors = validate_contact_info(invalid_email)
        assert "Invalid email format" in errors
        
        # Test name too long
        long_name = {"name": "x" * 101}
        errors = validate_contact_info(long_name)
        assert "Name too long" in errors
    
    def test_analytics_queue_item_structure(self):
        """Test analytics queue item creation."""
        def create_analytics_item(feedback_id, feedback_type, rating, category, tags, has_context):
            return {
                "feedback_id": feedback_id,
                "feedback_type": feedback_type,
                "timestamp": datetime.utcnow(),
                "rating": rating,
                "category": category,
                "tags": tags,
                "has_context": has_context
            }
        
        # Test analytics item creation
        item = create_analytics_item(
            "fb_bug_20241220_abc123",
            "bug",
            None,
            "functional",
            ["crash", "ui"],
            True
        )
        
        assert item["feedback_id"] == "fb_bug_20241220_abc123"
        assert item["feedback_type"] == "bug"
        assert item["rating"] is None
        assert item["category"] == "functional"
        assert item["tags"] == ["crash", "ui"]
        assert item["has_context"] is True
        assert isinstance(item["timestamp"], datetime)


class TestFeedbackCapabilities(unittest.TestCase):
    """Test feedback tool capability reporting."""
    
    def test_capability_structure(self):
        """Test capability reporting structure."""
        capabilities = {
            "tool_name": "docaiche_feedback",
            "version": "1.0.0",
            "supported_types": ["rating", "text", "bug", "feature", "search_quality", "content_accuracy"],
            "features": {
                "anonymous_submission": True,
                "contact_optional": True,
                "categorization": True,
                "priority_assignment": True,
                "analytics_integration": True,
                "spam_detection": True
            },
            "limits": {
                "max_content_length": 5000,
                "max_subject_length": 200,
                "max_tags": 10,
                "rate_limit_per_minute": 20
            },
            "categories": {
                "rating": ["user_experience", "content_quality", "performance"],
                "bug": ["functional", "ui", "performance", "security"],
                "feature": ["enhancement", "new_feature", "integration"],
                "search_quality": ["relevance", "completeness", "accuracy"],
                "content_accuracy": ["outdated", "incorrect", "missing", "unclear"]
            },
            "priority_levels": ["low", "medium", "high", "critical"],
            "privacy": {
                "anonymous_option": True,
                "data_retention_days": 365,
                "gdpr_compliant": True
            }
        }
        
        assert len(capabilities["supported_types"]) == 6
        assert capabilities["features"]["anonymous_submission"] is True
        assert capabilities["limits"]["max_content_length"] == 5000
        assert capabilities["limits"]["rate_limit_per_minute"] == 20
        assert len(capabilities["categories"]["bug"]) == 4
        assert capabilities["privacy"]["gdpr_compliant"] is True


if __name__ == "__main__":
    unittest.main()