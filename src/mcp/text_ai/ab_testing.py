"""
A/B Testing Framework for Prompt Optimization
=============================================

Provides infrastructure for testing different prompt versions
with statistical analysis and admin UI integration.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import random
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator
import math

from .prompts import PromptType, PromptTemplate


class TestStatus(str, Enum):
    """A/B test status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"


class TrafficSplitStrategy(str, Enum):
    """Traffic splitting strategies."""
    RANDOM = "random"  # Pure random assignment
    DETERMINISTIC = "deterministic"  # Hash-based consistent assignment
    WEIGHTED = "weighted"  # Custom weight distribution


class TestVariant(BaseModel):
    """
    Individual variant in an A/B test.
    
    Represents one version of a prompt being tested.
    """
    
    id: str = Field(
        description="Unique variant identifier"
    )
    
    name: str = Field(
        description="Human-readable variant name (e.g., 'Control', 'Variant A')"
    )
    
    template_id: str = Field(
        description="ID of the prompt template for this variant"
    )
    
    template_version: str = Field(
        description="Version of the template"
    )
    
    traffic_percentage: float = Field(
        default=50.0,
        description="Percentage of traffic for this variant",
        ge=0.0,
        le=100.0
    )
    
    is_control: bool = Field(
        default=False,
        description="Whether this is the control variant"
    )
    
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated metrics for this variant"
    )
    
    sample_size: int = Field(
        default=0,
        description="Number of times this variant was used"
    )


class TestMetrics(BaseModel):
    """Metrics tracked for each test variant."""
    
    response_quality_scores: List[float] = Field(
        default_factory=list,
        description="AI quality scores for responses"
    )
    
    response_times_ms: List[int] = Field(
        default_factory=list,
        description="Response generation times"
    )
    
    token_counts: List[int] = Field(
        default_factory=list,
        description="Token usage per request"
    )
    
    success_rate: float = Field(
        default=0.0,
        description="Percentage of successful responses"
    )
    
    error_count: int = Field(
        default=0,
        description="Number of errors encountered"
    )
    
    user_satisfaction_scores: List[float] = Field(
        default_factory=list,
        description="User feedback scores if available"
    )
    
    def calculate_averages(self) -> Dict[str, float]:
        """Calculate average metrics."""
        return {
            "avg_quality_score": sum(self.response_quality_scores) / len(self.response_quality_scores) if self.response_quality_scores else 0.0,
            "avg_response_time_ms": sum(self.response_times_ms) / len(self.response_times_ms) if self.response_times_ms else 0.0,
            "avg_token_count": sum(self.token_counts) / len(self.token_counts) if self.token_counts else 0.0,
            "avg_satisfaction": sum(self.user_satisfaction_scores) / len(self.user_satisfaction_scores) if self.user_satisfaction_scores else 0.0
        }


class StatisticalResult(BaseModel):
    """Statistical analysis results for A/B test."""
    
    winner: Optional[str] = Field(
        default=None,
        description="Winning variant ID if statistically significant"
    )
    
    confidence_level: float = Field(
        description="Statistical confidence level (0.0-1.0)"
    )
    
    p_value: float = Field(
        description="P-value from statistical test"
    )
    
    effect_size: float = Field(
        description="Effect size (Cohen's d or similar)"
    )
    
    required_sample_size: int = Field(
        description="Required sample size for significance"
    )
    
    current_power: float = Field(
        description="Current statistical power"
    )
    
    recommendation: str = Field(
        description="Recommendation based on analysis"
    )


class ABTest(BaseModel):
    """
    Complete A/B test configuration and state.
    
    Manages the lifecycle of a prompt optimization test.
    """
    
    id: str = Field(
        description="Unique test identifier"
    )
    
    name: str = Field(
        description="Human-readable test name"
    )
    
    description: str = Field(
        description="Test description and hypothesis"
    )
    
    prompt_type: PromptType = Field(
        description="Type of prompt being tested"
    )
    
    variants: List[TestVariant] = Field(
        description="Test variants including control"
    )
    
    status: TestStatus = Field(
        default=TestStatus.DRAFT,
        description="Current test status"
    )
    
    split_strategy: TrafficSplitStrategy = Field(
        default=TrafficSplitStrategy.DETERMINISTIC,
        description="How to split traffic between variants"
    )
    
    minimum_sample_size: int = Field(
        default=100,
        description="Minimum sample size per variant"
    )
    
    maximum_duration_days: int = Field(
        default=30,
        description="Maximum test duration"
    )
    
    success_metric: str = Field(
        default="response_quality",
        description="Primary metric for determining winner"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="When test started running"
    )
    
    ended_at: Optional[datetime] = Field(
        default=None,
        description="When test ended"
    )
    
    created_by: str = Field(
        description="User who created the test"
    )
    
    statistical_results: Optional[StatisticalResult] = Field(
        default=None,
        description="Statistical analysis results"
    )
    
    @validator('variants')
    def validate_traffic_split(cls, v):
        """Ensure traffic percentages sum to 100."""
        total = sum(variant.traffic_percentage for variant in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Traffic percentages must sum to 100, got {total}")
        return v
    
    @validator('variants')
    def validate_control_variant(cls, v):
        """Ensure exactly one control variant."""
        controls = [var for var in v if var.is_control]
        if len(controls) != 1:
            raise ValueError(f"Must have exactly one control variant, got {len(controls)}")
        return v
    
    def is_active(self) -> bool:
        """Check if test is currently active."""
        return self.status == TestStatus.RUNNING
    
    def can_conclude(self) -> bool:
        """Check if test has enough data to conclude."""
        for variant in self.variants:
            if variant.sample_size < self.minimum_sample_size:
                return False
        return True
    
    def get_variant_for_user(self, user_id: str) -> TestVariant:
        """
        Get variant assignment for a user.
        
        Uses deterministic assignment for consistency.
        """
        if self.split_strategy == TrafficSplitStrategy.DETERMINISTIC:
            # Hash user_id for consistent assignment
            hash_value = int(hashlib.md5(f"{self.id}:{user_id}".encode()).hexdigest(), 16)
            percentage = (hash_value % 100) + 1
            
            # Find variant based on cumulative percentages
            cumulative = 0.0
            for variant in self.variants:
                cumulative += variant.traffic_percentage
                if percentage <= cumulative:
                    return variant
            
            # Fallback to last variant
            return self.variants[-1]
        
        elif self.split_strategy == TrafficSplitStrategy.RANDOM:
            # Pure random assignment
            rand = random.uniform(0, 100)
            cumulative = 0.0
            for variant in self.variants:
                cumulative += variant.traffic_percentage
                if rand <= cumulative:
                    return variant
            return self.variants[-1]
        
        else:  # WEIGHTED or custom
            # Implement weighted selection
            weights = [v.traffic_percentage for v in self.variants]
            return random.choices(self.variants, weights=weights)[0]


class ABTestingFramework(ABC):
    """
    Abstract framework for A/B testing prompt templates.
    
    Manages test lifecycle, user assignment, and statistical analysis.
    """
    
    @abstractmethod
    async def create_test(self, test: ABTest) -> str:
        """
        Create a new A/B test.
        
        Args:
            test: Test configuration
            
        Returns:
            Test ID
        """
        pass
    
    @abstractmethod
    async def get_test(self, test_id: str) -> Optional[ABTest]:
        """
        Get test by ID.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Test configuration or None
        """
        pass
    
    @abstractmethod
    async def list_tests(
        self,
        status: Optional[TestStatus] = None,
        prompt_type: Optional[PromptType] = None
    ) -> List[ABTest]:
        """
        List tests with optional filters.
        
        Args:
            status: Filter by status
            prompt_type: Filter by prompt type
            
        Returns:
            List of tests
        """
        pass
    
    @abstractmethod
    async def start_test(self, test_id: str) -> None:
        """
        Start running a test.
        
        Args:
            test_id: Test to start
        """
        pass
    
    @abstractmethod
    async def pause_test(self, test_id: str) -> None:
        """
        Pause a running test.
        
        Args:
            test_id: Test to pause
        """
        pass
    
    @abstractmethod
    async def conclude_test(self, test_id: str) -> StatisticalResult:
        """
        Conclude test and perform final analysis.
        
        Args:
            test_id: Test to conclude
            
        Returns:
            Statistical analysis results
        """
        pass
    
    @abstractmethod
    async def get_variant_for_request(
        self,
        prompt_type: PromptType,
        user_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get variant assignment for a request.
        
        Args:
            prompt_type: Type of prompt needed
            user_id: User identifier for consistent assignment
            
        Returns:
            Tuple of (test_id, variant_id) or (None, None) if no active test
        """
        pass
    
    @abstractmethod
    async def record_outcome(
        self,
        test_id: str,
        variant_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record outcome metrics for a variant usage.
        
        Args:
            test_id: Test identifier
            variant_id: Variant that was used
            metrics: Outcome metrics to record
        """
        pass
    
    @abstractmethod
    async def analyze_test(self, test_id: str) -> StatisticalResult:
        """
        Perform statistical analysis on current test data.
        
        Args:
            test_id: Test to analyze
            
        Returns:
            Current statistical results
        """
        pass
    
    @abstractmethod
    async def export_test_data(self, test_id: str) -> Dict[str, Any]:
        """
        Export test data for external analysis.
        
        Args:
            test_id: Test to export
            
        Returns:
            Complete test data including all metrics
        """
        pass
    
    # Statistical analysis helpers
    
    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_effect: float,
        power: float = 0.8,
        alpha: float = 0.05
    ) -> int:
        """
        Calculate required sample size for test.
        
        Uses power analysis for two-proportion z-test.
        
        Args:
            baseline_rate: Expected baseline conversion rate
            minimum_effect: Minimum detectable effect size
            power: Statistical power (default 0.8)
            alpha: Significance level (default 0.05)
            
        Returns:
            Required sample size per variant
        """
        from scipy import stats
        
        # Z-scores for power and alpha
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_power = stats.norm.ppf(power)
        
        # Pooled proportion
        p1 = baseline_rate
        p2 = baseline_rate + minimum_effect
        p_pooled = (p1 + p2) / 2
        
        # Sample size calculation
        n = ((z_alpha + z_power) ** 2 * 
             (p1 * (1 - p1) + p2 * (1 - p2))) / (p1 - p2) ** 2
        
        return int(math.ceil(n))
    
    def perform_significance_test(
        self,
        control_metrics: TestMetrics,
        variant_metrics: TestMetrics,
        metric_name: str = "response_quality"
    ) -> Tuple[float, float, str]:
        """
        Perform statistical significance test.
        
        Args:
            control_metrics: Control variant metrics
            variant_metrics: Test variant metrics
            metric_name: Which metric to test
            
        Returns:
            Tuple of (p_value, effect_size, winner_id)
        """
        from scipy import stats
        import numpy as np
        
        # Get metric data
        if metric_name == "response_quality":
            control_data = control_metrics.response_quality_scores
            variant_data = variant_metrics.response_quality_scores
        elif metric_name == "response_time":
            control_data = control_metrics.response_times_ms
            variant_data = variant_metrics.response_times_ms
        else:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        if not control_data or not variant_data:
            return 1.0, 0.0, "insufficient_data"
        
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(control_data, variant_data)
        
        # Calculate effect size (Cohen's d)
        control_mean = np.mean(control_data)
        variant_mean = np.mean(variant_data)
        pooled_std = np.sqrt(
            (np.std(control_data) ** 2 + np.std(variant_data) ** 2) / 2
        )
        effect_size = (variant_mean - control_mean) / pooled_std if pooled_std > 0 else 0
        
        # Determine winner
        winner = "control" if control_mean > variant_mean else "variant"
        if p_value > 0.05:  # Not significant
            winner = "no_winner"
        
        return p_value, effect_size, winner


class ABTestConfigForUI(BaseModel):
    """
    A/B test configuration exposed to admin UI.
    
    Simplified model for UI interaction.
    """
    
    id: Optional[str] = Field(
        default=None,
        description="Test ID (null for new tests)"
    )
    
    name: str = Field(
        description="Test name"
    )
    
    description: str = Field(
        description="Test description"
    )
    
    prompt_type: str = Field(
        description="Prompt type being tested"
    )
    
    variants: List[Dict[str, Any]] = Field(
        description="Variant configurations"
    )
    
    status: str = Field(
        default="draft",
        description="Test status"
    )
    
    duration_days: int = Field(
        default=14,
        description="Test duration"
    )
    
    minimum_sample_size: int = Field(
        default=100,
        description="Minimum samples per variant"
    )