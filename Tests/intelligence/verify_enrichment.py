import os
import shutil
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Force Mock Provider for safety, unless env vars are present (which they are from previous steps)
# But for this test, we want to ensure *enrichment* runs.
# We will use the custom provider if set, or Mock if not.

from pydantic import Field

from src.etl.base import BaseETL
from src.models.base import AIEnhancedModel, TimestampedModel


class EnrichedNewsItem(TimestampedModel, AIEnhancedModel):
    title: str
    content: str


class TestEnrichmentETL(BaseETL[dict, EnrichedNewsItem]):
    def __init__(self):
        super().__init__(name="test_enrichment", enable_enrichment=True, enable_deduplication=False)

    def extract(self) -> list[dict]:
        return [{"title": "Python 3.13 Released", "content": "Python 3.13 introduces a JIT compiler and removes the GIL in free-threaded builds. This is a massive milestone for performance."}]

    def transform(self, data: list[dict]) -> list[EnrichedNewsItem]:
        return [EnrichedNewsItem(**item) for item in data]

    def load(self, data: list[EnrichedNewsItem]) -> None:
        pass  # No-op for test


def test_enrichment_flow():
    print("Testing AI Enrichment Flow...")

    etl = TestEnrichmentETL()

    # Run the ETL
    # The BaseETL.run() method returns metrics, but doesn't return the data itself.
    # However, we can inspect the data inside the `load` method if we overrode it or just trust the logs.
    # A better way for testing is to intercept `enricher.enrich_batch`.

    # Let's run it and check if it throws errors.
    # If using real LLM, this might cost tokens!

    metrics = etl.run()

    print(f"ETL finished. Success: {metrics.is_successful}")
    print(f"Records loaded: {metrics.records_loaded}")

    # To verify data, let's manually call the enricher on sample data
    from src.intelligence.enrichment import ContentEnricher

    item = EnrichedNewsItem(title="AI Agents in 2024", content="Autonomous agents are becoming the dominant paradigm in AI development.")

    print("\nManually Running Enricher...")
    enricher = ContentEnricher()
    enriched_items = enricher.enrich_batch([item])

    result = enriched_items[0]
    print(f"Summary: {result.ai_summary}")
    print(f"Tags: {result.ai_tags}")
    print(f"Insight: {result.ai_insight}")

    if result.ai_summary:
        print("PASS: Item was enriched.")
    else:
        print("FAIL: Item was NOT enriched (or Mock returned None).")


if __name__ == "__main__":
    test_enrichment_flow()
