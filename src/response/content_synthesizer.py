"""ContentSynthesizer: Combines search results with enriched content (PRD-011)."""

from typing import Any, Dict, List, Optional


class ContentSynthesizer:
    """Synthesizes content from search results and enrichment."""

    def synthesize(
        self,
        search_results: Optional[List[Dict]] = None,
        enrichment_results: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """Combine and prioritize content for response generation."""
        search_results = search_results or []
        enrichment_results = enrichment_results or []

        combined = search_results + enrichment_results

        seen_ids = set()
        deduped = []
        for item in combined:
            if "id" in item:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    deduped.append(item)
            else:
                # If no ID, just append. A more sophisticated strategy could be added later.
                deduped.append(item)

        return deduped
