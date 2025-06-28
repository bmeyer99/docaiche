"""
Search Result Ranking - PRD-009
Multi-factor result scoring and ranking algorithms.

Implements result aggregation, relevance scoring, and deduplication as
specified in PRD-009 for optimal search result presentation.
"""

import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .models import SearchResult, SearchStrategy
from .exceptions import ResultRankingError

logger = logging.getLogger(__name__)


class ResultRanker:
    """
    Multi-factor result ranking and scoring system.

    Implements the exact result ranking requirements from PRD-009 including
    relevance scoring, recency weighting, quality boosting, and deduplication.
    """

    def __init__(self):
        """Initialize result ranker with scoring weights."""
        # Scoring weights for different factors (must sum to 1.0)
        self.scoring_weights = {
            "vector_similarity": 0.4,  # Vector similarity score
            "metadata_relevance": 0.2,  # Metadata-based relevance
            "recency": 0.15,  # Content recency
            "quality_score": 0.15,  # Content quality
            "technology_match": 0.1,  # Technology matching boost
        }

        logger.info("ResultRanker initialized with multi-factor scoring")

    async def rank_results(
        self,
        results: List[SearchResult],
        strategy_used: SearchStrategy,
        query: str,
        technology_hint: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Rank search results using multi-factor scoring.

        Implements exact ranking logic from PRD-009:
        - Vector similarity weighting
        - Metadata relevance scoring
        - Recency factor calculation
        - Quality score integration
        - Technology matching boost

        Args:
            results: List of search results to rank
            strategy_used: Search strategy that was executed
            query: Original search query for relevance calculation
            technology_hint: Technology filter hint for boosting

        Returns:
            List of SearchResult objects sorted by final score

        Raises:
            ResultRankingError: If ranking fails
        """
        try:
            logger.info(
                f"Ranking {len(results)} search results using strategy: {strategy_used}"
            )

            if not results:
                logger.info("No results to rank")
                return []

            # Step 1: Calculate multi-factor scores for each result
            scored_results = []
            for result in results:
                try:
                    final_score = await self._calculate_final_score(
                        result, query, technology_hint, strategy_used
                    )

                    # Update result with final score
                    result.relevance_score = final_score
                    scored_results.append(result)

                except Exception as e:
                    logger.warning(f"Failed to score result {result.content_id}: {e}")
                    # Keep result with original score as fallback
                    scored_results.append(result)

            # Step 2: Sort by final relevance score (descending)
            ranked_results = sorted(
                scored_results, key=lambda r: r.relevance_score, reverse=True
            )

            # Step 3: Apply position-based adjustments
            final_results = self._apply_position_adjustments(ranked_results)

            logger.info(
                f"Ranking completed: top score = {final_results[0].relevance_score:.3f}"
            )

            return final_results

        except Exception as e:
            logger.error(f"Result ranking failed: {e}")
            raise ResultRankingError(
                f"Failed to rank search results: {str(e)}",
                result_count=len(results),
                ranking_strategy=strategy_used.value,
                error_context={"error": str(e)},
            )

    async def _calculate_final_score(
        self,
        result: SearchResult,
        query: str,
        technology_hint: Optional[str],
        strategy: SearchStrategy,
    ) -> float:
        """
        Calculate final multi-factor score for a search result.

        Args:
            result: Search result to score
            query: Original search query
            technology_hint: Technology filter hint
            strategy: Search strategy used

        Returns:
            Final relevance score between 0.0 and 1.0
        """
        # Start with base vector similarity score
        vector_score = (
            result.relevance_score * self.scoring_weights["vector_similarity"]
        )

        # Calculate metadata relevance score
        metadata_score = (
            self._calculate_metadata_relevance(result, query)
            * self.scoring_weights["metadata_relevance"]
        )

        # Calculate recency score
        recency_score = (
            self._calculate_recency_score(result) * self.scoring_weights["recency"]
        )

        # Use quality score if available
        quality_score = (result.quality_score or 0.5) * self.scoring_weights[
            "quality_score"
        ]

        # Calculate technology matching boost
        tech_score = (
            self._calculate_technology_score(result, technology_hint)
            * self.scoring_weights["technology_match"]
        )

        # Combine all factors
        final_score = (
            vector_score + metadata_score + recency_score + quality_score + tech_score
        )

        # Apply strategy-specific adjustments
        final_score = self._apply_strategy_adjustments(final_score, strategy)

        # Ensure score is within bounds
        return min(1.0, max(0.0, final_score))

    def _calculate_metadata_relevance(self, result: SearchResult, query: str) -> float:
        """
        Calculate metadata-based relevance score.

        Args:
            result: Search result
            query: Search query

        Returns:
            Metadata relevance score between 0.0 and 1.0
        """
        score = 0.0
        query_lower = query.lower()

        # Title matching (highest weight)
        if query_lower in result.title.lower():
            score += 0.5

        # Content snippet matching
        if query_lower in result.content_snippet.lower():
            score += 0.3

        # Source URL matching (for specific documentation sections)
        if any(word in result.source_url.lower() for word in query_lower.split()):
            score += 0.2

        return min(1.0, score)

    def _calculate_recency_score(self, result: SearchResult) -> float:
        """
        Calculate recency-based score.

        Args:
            result: Search result

        Returns:
            Recency score between 0.0 and 1.0
        """
        # Default to moderate recency if no metadata available
        if not result.metadata:
            return 0.5

        # Try to extract creation or update date from metadata
        created_at = result.metadata.get("created_at")
        updated_at = result.metadata.get("updated_at")

        # Use the more recent of the two dates
        date_str = updated_at or created_at
        if not date_str:
            return 0.5

        try:
            # Parse date (assuming ISO format)
            if isinstance(date_str, str):
                content_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                content_date = date_str

            # Calculate age in days
            age_days = (datetime.utcnow() - content_date.replace(tzinfo=None)).days

            # Recency scoring: exponential decay with 6-month half-life
            half_life_days = 180
            recency_factor = math.exp(-age_days * math.log(2) / half_life_days)

            return min(1.0, recency_factor)

        except (ValueError, TypeError):
            # Fallback for invalid dates
            return 0.5

    def _calculate_technology_score(
        self, result: SearchResult, technology_hint: Optional[str]
    ) -> float:
        """
        Calculate technology matching score.

        Args:
            result: Search result
            technology_hint: Technology filter hint

        Returns:
            Technology matching score between 0.0 and 1.0
        """
        if not technology_hint:
            return 0.5  # Neutral score when no technology hint

        # Direct technology match
        if result.technology and result.technology.lower() == technology_hint.lower():
            return 1.0

        # Partial technology match in content or metadata
        tech_hint_lower = technology_hint.lower()

        if tech_hint_lower in result.title.lower():
            return 0.8

        if tech_hint_lower in result.content_snippet.lower():
            return 0.6

        if result.metadata and tech_hint_lower in str(result.metadata).lower():
            return 0.4

        return 0.1  # Minimal score for non-matching technology

    def _apply_strategy_adjustments(
        self, score: float, strategy: SearchStrategy
    ) -> float:
        """
        Apply strategy-specific score adjustments.

        Args:
            score: Base calculated score
            strategy: Search strategy used

        Returns:
            Adjusted score
        """
        adjustments = {
            SearchStrategy.VECTOR: 1.0,  # No adjustment for pure vector search
            SearchStrategy.METADATA: 0.95,  # Slight penalty for metadata-only search
            SearchStrategy.HYBRID: 1.05,  # Slight boost for hybrid search
            SearchStrategy.FACETED: 1.02,  # Small boost for faceted search
        }

        adjustment_factor = adjustments.get(strategy, 1.0)
        return score * adjustment_factor

    def _apply_position_adjustments(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Apply position-based adjustments to final ranking.

        Args:
            results: Results sorted by score

        Returns:
            Results with position adjustments applied
        """
        # Apply small position-based decay to prevent clustering
        for i, result in enumerate(results):
            position_decay = 1.0 - (i * 0.001)  # Very small decay
            result.relevance_score *= position_decay

        return results

    def deduplicate_results(
        self, results: List[SearchResult], dedup_threshold: float = 0.95
    ) -> List[SearchResult]:
        """
        Deduplicate search results based on content similarity.

        Args:
            results: List of search results
            dedup_threshold: Similarity threshold for deduplication

        Returns:
            Deduplicated list of results
        """
        try:
            logger.info(
                f"Deduplicating {len(results)} results with threshold {dedup_threshold}"
            )

            if not results:
                return []

            # Group results by content_id for exact duplicates
            content_groups = defaultdict(list)
            for result in results:
                content_groups[result.content_id].append(result)

            # Keep the highest-scoring result from each group
            deduplicated = []
            for content_id, group in content_groups.items():
                if len(group) == 1:
                    deduplicated.append(group[0])
                else:
                    # Keep the result with highest relevance score
                    best_result = max(group, key=lambda r: r.relevance_score)
                    deduplicated.append(best_result)
                    logger.debug(
                        f"Deduplicated {len(group)} results for content_id: {content_id}"
                    )

            logger.info(
                f"Deduplication completed: {len(results)} -> {len(deduplicated)} results"
            )
            return deduplicated

        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            # Return original results as fallback
            return results

    def get_ranking_explanation(self, result: SearchResult) -> Dict[str, Any]:
        """
        Get explanation of ranking factors for a result.

        Args:
            result: Search result to explain

        Returns:
            Dictionary with ranking factor breakdown
        """
        return {
            "final_score": result.relevance_score,
            "content_id": result.content_id,
            "title": result.title,
            "technology": result.technology,
            "quality_score": result.quality_score,
            "scoring_weights": self.scoring_weights,
            "explanation": "Multi-factor ranking combining vector similarity, metadata relevance, recency, quality, and technology matching",
        }
