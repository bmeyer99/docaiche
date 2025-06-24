"""ContentSynthesizer: Combines search results with enriched content (PRD-011).

Responsible for merging, deduplicating, and prioritizing content for response generation.
"""
from typing import Any, Dict, Optional, List
import logging
import re

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    # Remove <img> tags and other potentially unsafe HTML
    if not isinstance(text, str):
        return text
    text = re.sub(r'<img[^>]*>', '', text, flags=re.IGNORECASE)
    # Optionally strip other tags or sanitize further as needed
    return text

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
            # Input validation
            def is_empty(val):
                if val is None:
                    return True
                if isinstance(val, (list, dict, str)) and len(val) == 0:
                    return True
                return False

            if is_empty(search_results) and is_empty(enriched_content):
                raise ValueError("At least one of search_results or enriched_content must be provided and non-empty.")
            if search_results is not None and not isinstance(search_results, (list, dict, str)):
                raise ValueError("search_results must be a list, dict, or str.")
            if enriched_content is not None and not isinstance(enriched_content, (list, dict, str)):
                raise ValueError("enriched_content must be a list, dict, or str.")

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
            # If all items are dicts, require all to have "text" key, else raise
            if all(isinstance(item, dict) for item in deduped):
                if not all("text" in item for item in deduped):
                    for item in deduped:
                        if "text" not in item:
                            self.logger.error("Input dict missing required 'text' key.")
                            raise ValueError("All dictionary items must contain 'text' key")
                merged_text = " ".join(sanitize_text(item["text"]) for item in deduped)
                return {"text": merged_text}
            # If all items are strings, merge and sanitize
            if all(isinstance(item, str) for item in deduped):
                merged_text = " ".join(sanitize_text(item) for item in deduped)
                return {"text": merged_text}
            # Otherwise, return as results list, but sanitize any text fields
            for item in deduped:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = sanitize_text(item["text"])
                elif isinstance(item, str):
                    item = sanitize_text(item)
            return {"results": deduped}
        except Exception as e:
            self.logger.error(f"Content synthesis error: {e}")
            raise ValueError(f"Content synthesis failed: {e}")