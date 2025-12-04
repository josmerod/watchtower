import logging
from datetime import datetime

from src.analytics.trends import TrendAnalyzer
from src.config.settings import get_settings
from src.utils.file_system import ensure_directory, read_json_file, write_json_file

logger = logging.getLogger(__name__)


class TrendScheduler:
    """Schedules and executes trend analysis jobs."""

    def __init__(self):
        self.settings = get_settings()
        self.analyzer = TrendAnalyzer()
        self.trends_dir = self.settings.data_dir / "analytics" / "trends"
        ensure_directory(self.trends_dir)

    def run_daily_analysis(self):
        """Runs the daily trend analysis."""
        logger.info("Starting daily trend analysis...")

        # 1. Load all available data (simplified for now, ideally would scan all source dirs)
        # For this MVP, we'll scan a few known directories or use a central registry if available
        # In a real scenario, we might query a database or index.
        all_items = self._load_all_content()

        if not all_items:
            logger.warning("No items found for trend analysis.")
            return

        # 2. Calculate trends
        trends = self.analyzer.analyze_trends(all_items)

        # 3. Save results
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_file = self.trends_dir / f"{date_str}_trends.json"

        # Convert Pydantic models to dicts with JSON-safe types
        trends_data = [trend.model_dump(mode="json") for trend in trends]

        write_json_file(output_file, trends_data)

        # Also update 'latest' pointer
        write_json_file(self.trends_dir / "latest_trends.json", trends_data)

        logger.info(f"Trend analysis complete. Found {len(trends)} trends. Saved to {output_file}")

    def _load_all_content(self) -> list[dict]:
        """Loads content from all data sources."""
        # This is a placeholder for the actual data loading logic
        # We need to scan data/{source}/*.json
        all_items = []
        data_root = self.settings.data_dir

        # Example sources to scan
        sources = ["hackernews", "arxiv", "github", "reddit"]

        for source in sources:
            source_dir = data_root / source
            if not source_dir.exists():
                continue

            # Find the most recent data file
            # Assuming files are named like {source}.json or {timestamp}.json
            # We'll just look for json files
            for file_path in source_dir.glob("*.json"):
                try:
                    data = read_json_file(file_path)
                    if isinstance(data, list):
                        # Add source info if missing
                        for item in data:
                            if isinstance(item, dict) and "source" not in item:
                                item["source"] = source
                        all_items.extend(data)
                    elif isinstance(data, dict):
                        if "source" not in data:
                            data["source"] = source
                        all_items.append(data)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")

        return all_items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = TrendScheduler()
    scheduler.run_daily_analysis()
