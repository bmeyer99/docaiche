"""ContentSynthesizer: Combines search results with enriched content (PRD-011).

Responsible for merging, deduplicating, and prioritizing content for response generation.
"""

from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class ContentSynthesizer:
    """Synthesizes content from search results and enrichment.

    Args:
        None (dependencies injected via methods if needed)

    Methods:
        synthesize: Merge and prioritize content for response

    Raises:
        ValueError: On invalid input

    Integration Points:
        - Accepts input from SearchOrchestrator (PRD-009)
        - Accepts enrichment from KnowledgeEnricher (PRD-010)

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def synthesize(
        self,
        search_results: Any,
        enriched_content: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Combine and prioritize content for response generation.

        Args:
            search_results: Results from SearchOrchestrator
            enriched_content: Optional content from KnowledgeEnricher
            context: Optional additional context

        Returns:
            Synthesized content for downstream processing

        Raises:
            ValueError: On invalid input
        """
        try:
            # Normalize input to lists
            base = []
            if search_results:
                if isinstance(search_results, list):
                    base.extend(search_results)
                else:
                    base.append(search_results)
            if enriched_content:
                if isinstance(enriched_content, list):
                    base.extend(enriched_content)
                else:
                    base.append(enriched_content)
            # Deduplicate by unique 'id' or content hash if present
            seen = set()
            deduped = []
            for item in base:
                # Use 'id' if available, else hash of str(item)
                key = None
                if isinstance(item, dict) and 'id' in item:
                    key = item['id']
                else:
                    key = hash(str(item))
                if key not in seen:
                    seen.add(key)
                    deduped.append(item)
            # Prioritize: If context provides 'priority_keys', sort accordingly
            if context and 'priority_keys' in context:
                keys = context['priority_keys']
                def sort_key(x):
                    if isinstance(x, dict):
                        return [x.get(k, 0) for k in keys]
                    return [0] * len(keys)
                deduped.sort(key=sort_key, reverse=True)
            return deduped
        except Exception as e:
            self.logger.error(f"Content synthesis error: {e}")
            raise ValueError(f"Content synthesis failed: {e}")