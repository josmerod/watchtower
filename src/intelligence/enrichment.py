"""Content Enrichment Service for Watchtower."""

import logging
from datetime import datetime
from typing import List, TypeVar

from pydantic import BaseModel, Field

from src.intelligence.llm_client import get_llm_client
from src.models.base import AIEnhancedModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class EnrichmentResult(BaseModel):
    """Structured result from LLM enrichment."""
    summary: str = Field(description="Concise summary of the content")
    tags: List[str] = Field(description="Relevant tags/categories")
    insight: str | None = Field(default=None, description="Key insight or 'why it matters'")


class ContentEnricher:
    """Service to enrich content with AI summaries and insights."""

    def __init__(self):
        self.llm_client = get_llm_client()

    def enrich_batch(self, items: List[T]) -> List[T]:
        """Enrich a batch of items with AI metadata.

        Args:
            items: List of items (must inherit from AIEnhancedModel to be enriched).

        Returns:
            List of items (potentially modified in-place or new instances).
        """
        if not items:
            return []

        # Filter for enrichable items
        enrichable_items = [
            item for item in items 
            if isinstance(item, AIEnhancedModel) and not item.ai_summary
        ]

        if not enrichable_items:
            return items

        logger.info(f"Enriching {len(enrichable_items)} items with AI...")

        for item in enrichable_items:
            try:
                self._enrich_item(item)
            except Exception as e:
                logger.error(f"Failed to enrich item {getattr(item, 'id', 'unknown')}: {e}")

        return items

    def _enrich_item(self, item: AIEnhancedModel) -> None:
        """Enrich a single item."""
        # Construct a context string from available fields
        text_content = ""
        if hasattr(item, "title"):
            text_content += f"Title: {item.title}\n"
        if hasattr(item, "description") and item.description:
            text_content += f"Description: {item.description}\n"
        if hasattr(item, "content") and item.content:
            text_content += f"Content: {item.content[:2000]}\n"  # Truncate content
        if hasattr(item, "abstract"):
            text_content += f"Abstract: {item.abstract}\n"

        if not text_content:
            return

        prompt = (
            "Analyze the following content and provide:\n"
            "1. A concise summary (max 2 sentences).\n"
            "2. A list of 3-5 relevant tags.\n"
            "3. A 'key insight' or 'why it matters' statement (1 sentence) for a developer audience."
        )

        result = self.llm_client.extract_structured_data(
            text=text_content,
            schema=EnrichmentResult,
            prompt=prompt
        )

        if result:
            item.ai_summary = result.summary
            item.ai_tags = result.tags
            item.ai_insight = result.insight
            item.ai_enriched_at = datetime.utcnow()
            logger.debug(f"Enriched item: {getattr(item, 'title', 'unknown')}")
