"""ETL for AI Research Intelligence."""

import json
import time
from datetime import datetime, timezone
from typing import Any

from src.alerts.engine import AlertEngine
from src.etl.intelligence.base_intelligence_etl import BaseIntelligenceETL
from src.intelligence.ai_engines import (
    AITrendDetector,
    ImplementationComplexityScorer,
    ResearchOpportunityAnalyzer,
)
from src.models.ai_research_model import (
    AIResearchPaper,
    ImplementationComplexity,
    ResearchDomain,
)


class AIResearchIntelligenceETL(BaseIntelligenceETL[dict, AIResearchPaper]):
    """ETL for AI/ML Research papers."""

    def __init__(self, fetch_interval: int = 3600, max_results: int = 200, days_back: int = 7):
        """Initialize the AI Research Intelligence ETL.

        Args:
            fetch_interval: Interval in seconds between fetches
            max_results: Maximum number of papers to fetch
            days_back: Number of days back to search for papers
        """
        self.fetch_interval = fetch_interval
        self.max_results = max_results
        self.days_back = days_back

        super().__init__(
            name="ai_research_intelligence",
            description="ETL for AI/ML research intelligence and trend analysis",
            # fetch_interval is not passed to BaseETL.__init__ as it's not a standard arg there
        )

        # Initialize watcher for real data
        from src.watchers.arxiv_watcher import ArxivWatcher

        self.watcher = ArxivWatcher(
            name="ai_research_watcher",
            check_interval=fetch_interval,
            max_results=max_results,
            days_back=days_back,
        )

        # Initialize intelligence engines
        self.trend_detector = AITrendDetector()
        self.complexity_scorer = ImplementationComplexityScorer()
        self.opportunity_analyzer = ResearchOpportunityAnalyzer()

        # Initialize Alert Engine
        self.alert_engine = AlertEngine()

    def extract(self) -> list[dict[str, Any]]:
        """Extract research papers from ArXiv using ArxivWatcher.

        Returns:
            List of raw paper dictionaries
        """
        self.logger.info(f"Extracting up to {self.max_results} AI research papers from ArXiv...")

        try:
            # Use the new pagination method
            papers = self.watcher.fetch_and_extract_all(self.max_results)

            self.logger.info(f"Extracted {len(papers)} papers from ArXiv")
            return papers

        except Exception as e:
            self.logger.error(f"Error extracting papers from ArXiv: {e}")
            return []

    def transform(self, raw_data: list[dict[str, Any]]) -> list[AIResearchPaper]:
        """Transform raw paper data into AIResearchPaper models.

        Args:
            raw_data: List of raw paper dictionaries from ArXiv

        Returns:
            List of enriched AIResearchPaper objects
        """
        self.logger.info(f"Transforming {len(raw_data)} papers...")

        transformed_papers = []

        for item in raw_data:
            try:
                # Map ArXiv fields to our model
                # ArXiv watcher returns: id, title, authors, categories, summary, published, updated, link, pdf_url

                # Determine domain from categories
                categories = item.get("categories", [])
                domain = self._map_categories_to_domain(categories)

                # Create base paper object
                paper = AIResearchPaper(
                    id=item.get("id"),
                    title=item.get("title", "Unknown Title"),
                    authors=item.get("authors", []),
                    published_at=self._parse_date(item.get("published")),
                    abstract=item.get("summary", ""),
                    url=item.get("link", ""),
                    pdf_url=item.get("pdf_url"),
                    source="arxiv",
                    primary_domain=domain,
                    tags=categories,
                    # Initialize intelligence fields (will be enriched below)
                    trend_score=0.0,
                    complexity=ImplementationComplexity.MEDIUM,
                    industry_impact="Pending Analysis",
                    implementation_probability=0.0,
                )

                # Enrich with intelligence
                self._enrich_paper(paper)

                transformed_papers.append(paper)

            except Exception as e:
                self.logger.warning(f"Error transforming paper {item.get('id', 'unknown')}: {e}")
                continue

        self.logger.info(f"Successfully transformed {len(transformed_papers)} papers")
        return transformed_papers

    def _map_categories_to_domain(self, categories: list[str]) -> ResearchDomain:
        """Map ArXiv categories to ResearchDomain."""
        # Simple mapping logic - can be expanded
        cat_str = " ".join(categories).lower()

        if "cs.cv" in cat_str:
            return ResearchDomain.CV
        elif "cs.cl" in cat_str:
            return ResearchDomain.NLP
        elif "cs.lg" in cat_str or "stat.ml" in cat_str:
            return ResearchDomain.ML_THEORY
        elif "cs.ai" in cat_str:
            return ResearchDomain.RL  # Approximation or use OTHER if not specific
        elif "cs.ro" in cat_str:
            return ResearchDomain.ROBOTICS
        elif "cs.cr" in cat_str:
            return ResearchDomain.OTHER  # Security not in enum yet
        else:
            return ResearchDomain.OTHER

    def _parse_date(self, date_str: Any) -> datetime:
        """Parse date string to datetime."""
        if isinstance(date_str, datetime):
            return date_str
        try:
            # ArXiv often uses ISO format or similar
            # If it's a struct_time (from feedparser), convert it
            if hasattr(date_str, "tm_year"):  # struct_time
                return datetime.fromtimestamp(time.mktime(date_str), tz=timezone.utc)
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except:
            return datetime.now(timezone.utc)

    def _enrich_paper(self, paper: AIResearchPaper) -> None:
        """Apply intelligence engines to enrich the paper."""
        # 1. Trend Analysis
        paper.trend_score = self.trend_detector.analyze_trend(paper)

        # 2. Complexity Analysis
        paper.complexity = self.complexity_scorer.score_complexity(paper)

        # 3. Opportunity Analysis
        opportunities = self.opportunity_analyzer.identify_opportunities(paper)
        paper.implementation_opportunities = opportunities

        # Set derived fields based on analysis
        if paper.trend_score > 0.8:
            paper.industry_impact = "High Potential"
        elif paper.trend_score > 0.5:
            paper.industry_impact = "Moderate Interest"
        else:
            paper.industry_impact = "Research Only"

        # Simple probability based on complexity and trend
        base_prob = paper.trend_score * 100
        if paper.complexity == ImplementationComplexity.LOW:
            base_prob *= 1.2
        elif paper.complexity == ImplementationComplexity.HIGH:
            base_prob *= 0.8
        paper.implementation_probability = min(95.0, max(5.0, base_prob))

    def load(self, data: list[AIResearchPaper]) -> None:
        """Load data to JSON storage."""
        # Use the default JSON loader from BaseETL (via SimpleETL-like behavior or custom)
        # BaseETL doesn't implement load, so we must.
        # We'll use the DataFrameETL-style loading or just simple JSON dump

        # Ensure output directory is data/ai_research
        from pathlib import Path

        self.output_dir = Path(self.settings.project_root) / "data" / "ai_research"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"ai_research_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = self.output_dir / filename

        output_path.write_text(
            json.dumps([p.model_dump(mode="json") for p in data], indent=2),
            encoding="utf-8",
        )
        self.logger.info(f"Saved {len(data)} papers to {output_path}")

        # Also save latest
        latest_path = self.output_dir / "ai_research_latest.json"
        latest_path.write_text(
            json.dumps([p.model_dump(mode="json") for p in data], indent=2),
            encoding="utf-8",
        )

        # Trigger Alerts
        self.logger.info("Evaluating papers for alerts...")
        alert_count = 0
        for paper in data:
            try:
                # Convert paper to dict for evaluation
                content = paper.model_dump(mode="json")
                # Add specific fields that rules might check
                content["source"] = "ai_research"
                # Make industry_impact searchable by including in description
                content["description"] = f"{paper.abstract} [Impact: {paper.industry_impact}]"

                # Evaluate against admin user rules
                events = self.alert_engine.evaluate_content(content, user_id="admin")
                if events:
                    alert_count += len(events)
                    self.logger.info(f"Generated {len(events)} alert(s) for paper: {paper.title}")
            except Exception as e:
                self.logger.error(f"Error evaluating alerts for paper {paper.id}: {e}")

        self.logger.info(f"Total alerts generated: {alert_count}")


if __name__ == "__main__":
    # Allow running directly
    etl = AIResearchIntelligenceETL()
    etl.run()
