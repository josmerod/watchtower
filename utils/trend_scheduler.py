"""Trend scheduler for daily background trend calculation.

This module provides automated daily trend analysis and data storage
for the content deduplication and analytics system.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from src.utils.logging import get_logger
from src.web.dashboard.utils import get_data_path

logger = get_logger(__name__)


class TrendScheduler:
    """Background scheduler for daily trend calculation and storage.

    Runs trend analysis on all content categories and stores results
    for dashboard display and filtering.
    """

    def __init__(
        self,
        window_days: int = 7,
        threshold_percentage: float = 30.0,
        min_confidence: float = 0.5,
    ):
        """Initialize the TrendScheduler.

        Args:
            window_days: Analysis window in days
            threshold_percentage: Minimum percentage change for trend detection
            min_confidence: Minimum confidence score
        """
        self.window_days = window_days
        self.threshold_percentage = threshold_percentage
        self.min_confidence = min_confidence

        # Data paths
        self.trends_data_path = get_data_path("analytics", "trends")
        self.trends_data_path.mkdir(parents=True, exist_ok=True)

    def run_daily_trend_analysis(self) -> dict[str, Any]:
        """Execute daily trend analysis for all content categories.

        Returns:
            Analysis results with metadata
        """
        logger.info("Starting daily trend analysis")

        try:
            analysis_date = datetime.utcnow()

            # Load all available content data
            all_content = self._load_all_content_data()

            if not all_content:
                logger.warning("No content data available for trend analysis")
                return self._create_empty_result(analysis_date)

            # Import here to avoid circular imports
            from src.analytics.trends import TrendAnalyzer

            # Initialize analyzer
            analyzer = TrendAnalyzer(
                window_days=self.window_days,
                threshold_percentage=self.threshold_percentage,
                min_confidence=self.min_confidence,
            )

            # Calculate trends
            trend_analysis = analyzer.calculate_trends(all_content)

            # Store results
            self._store_trend_results(trend_analysis, analysis_date)

            # Store content snapshot for future comparison
            self._store_content_snapshot(all_content, analysis_date)

            # Clean old data
            self._cleanup_old_data()

            results = {
                "analysis_date": analysis_date.isoformat(),
                "total_items_analyzed": trend_analysis.total_items_analyzed,
                "trends_detected": len(trend_analysis.trending_items),
                "rising_trends": trend_analysis.rising_trends,
                "falling_trends": trend_analysis.falling_trends,
                "stable_trends": trend_analysis.stable_trends,
                "average_confidence": trend_analysis.average_confidence,
                "significant_trends": trend_analysis.significant_trends,
                "success": True,
                "message": "Daily trend analysis completed successfully",
            }

            logger.info(f"Daily trend analysis completed: {results['trends_detected']} trends detected " f"({results['rising_trends']} rising, {results['falling_trends']} falling)")

            return results

        except Exception as e:
            logger.error(f"Error in daily trend analysis: {e}", exc_info=True)
            return {
                "analysis_date": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(e),
                "message": "Daily trend analysis failed",
            }

    def get_latest_trends(self) -> dict[str, Any]:
        """Get the most recent trend analysis results.

        Returns:
            Latest trend analysis data
        """
        try:
            # Look for the latest trend file
            trend_files = list(self.trends_data_path.glob("*_trends.json"))
            if not trend_files:
                return {"trends": [], "message": "No trend data available"}

            # Sort by date (most recent first)
            latest_file = max(trend_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Error loading latest trends: {e}")
            return {"trends": [], "error": str(e)}

    def _load_all_content_data(self) -> list[dict[str, Any]]:
        """Load all available content data from various sources.

        Returns:
            Combined list of all content items
        """
        all_content = []

        # Define data sources to scan
        data_sources = [
            ("arxiv", "arxiv_papers.json"),
            ("news", "*_latest.json"),
            ("github", "github_trending.json"),
            ("games", "free_games.json"),
            ("deals", "latest_deals.json"),
            ("courses", "latest_courses.json"),
            ("entertainment", "latest_entertainment.json"),
        ]

        # Load from each data source
        for source_dir, pattern in data_sources:
            try:
                source_path = get_data_path(source_dir)
                if not source_path.exists():
                    continue

                # Handle patterns and single files
                if "*" in pattern:
                    files = list(source_path.glob(pattern))
                else:
                    file_path = source_path / pattern
                    files = [file_path] if file_path.exists() else []

                # Load content from files
                for file_path in files:
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                # Add source metadata
                                for item in data:
                                    item["data_source"] = source_dir
                                    item["file_source"] = file_path.name
                                all_content.extend(data)
                            elif isinstance(data, dict) and "items" in data:
                                # Handle nested data structures
                                for item in data["items"]:
                                    item["data_source"] = source_dir
                                    item["file_source"] = file_path.name
                                all_content.extend(data["items"])

                    except (OSError, json.JSONDecodeError) as e:
                        logger.warning(f"Error loading {file_path}: {e}")

            except Exception as e:
                logger.warning(f"Error scanning data source {source_dir}: {e}")

        logger.info(f"Loaded {len(all_content)} content items from {len(data_sources)} sources")
        return all_content

    def _store_trend_results(self, trend_analysis, analysis_date: datetime) -> None:
        """Store trend analysis results to JSON file.

        Args:
            trend_analysis: TrendAnalysis object to store
            analysis_date: Date of the analysis
        """
        try:
            filename = f"{analysis_date.strftime('%Y-%m-%d')}_trends.json"
            file_path = self.trends_data_path / filename

            # Convert to dict for JSON serialization
            trend_data = {
                "analysis_date": trend_analysis.analysis_date.isoformat(),
                "window_days": trend_analysis.window_days,
                "total_items_analyzed": trend_analysis.total_items_analyzed,
                "threshold_percentage": trend_analysis.threshold_percentage,
                "min_data_points": trend_analysis.min_data_points,
                "rising_trends": trend_analysis.rising_trends,
                "falling_trends": trend_analysis.falling_trends,
                "stable_trends": trend_analysis.stable_trends,
                "average_confidence": trend_analysis.average_confidence,
                "significant_trends": trend_analysis.significant_trends,
                "trending_items": [item.dict() for item in trend_analysis.trending_items],
                "metadata": {
                    "analyzer_version": "1.0",
                    "generated_at": datetime.utcnow().isoformat(),
                    "data_sources_count": len({item.get("data_source", "unknown") for item in self._load_all_content_data()}),
                },
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(trend_data, f, indent=2, ensure_ascii=False)

            # Also store as latest for quick access
            latest_path = self.trends_data_path / "latest_trends.json"
            with open(latest_path, "w", encoding="utf-8") as f:
                json.dump(trend_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Trend results stored to {filename}")

        except Exception as e:
            logger.error(f"Error storing trend results: {e}")

    def _store_content_snapshot(self, content: list[dict[str, Any]], analysis_date: datetime) -> None:
        """Store content snapshot for future trend comparison.

        Args:
            content: Content items to store
            analysis_date: Date of the snapshot
        """
        try:
            filename = f"{analysis_date.strftime('%Y-%m-%d')}_content_snapshot.json"
            file_path = self.trends_data_path / filename

            # Store a snapshot for historical comparison
            snapshot_data = {
                "snapshot_date": analysis_date.isoformat(),
                "total_items": len(content),
                "content_snapshot": content[:1000],  # Limit to 1000 items for storage efficiency
                "metadata": {
                    "stored_items": min(len(content), 1000),
                    "total_items_available": len(content),
                    "generated_at": datetime.utcnow().isoformat(),
                },
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Content snapshot stored to {filename}")

        except Exception as e:
            logger.error(f"Error storing content snapshot: {e}")

    def _cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old trend analysis files.

        Args:
            days_to_keep: Number of days to keep files
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Clean trend files
            for file_path in self.trends_data_path.glob("*.json"):
                try:
                    # Extract date from filename
                    if file_path.name.startswith("latest_"):
                        continue  # Keep latest file

                    date_str = file_path.name.split("_")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        file_path.unlink()
                        logger.debug(f"Removed old trend file: {file_path.name}")

                except (ValueError, IndexError):
                    # Skip files that don't match expected format
                    continue

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _create_empty_result(self, analysis_date: datetime) -> dict[str, Any]:
        """Create empty result for when no data is available.

        Args:
            analysis_date: Date of the analysis

        Returns:
            Empty analysis result
        """
        return {
            "analysis_date": analysis_date.isoformat(),
            "total_items_analyzed": 0,
            "trends_detected": 0,
            "rising_trends": 0,
            "falling_trends": 0,
            "stable_trends": 0,
            "average_confidence": 0.0,
            "significant_trends": 0,
            "success": True,
            "message": "No content data available for analysis",
        }


# Convenience function for running analysis
def run_daily_trend_analysis() -> dict[str, Any]:
    """Run daily trend analysis with default settings.

    Returns:
        Analysis results
    """
    scheduler = TrendScheduler()
    return scheduler.run_daily_trend_analysis()


if __name__ == "__main__":
    # Run analysis when script is executed directly
    result = run_daily_trend_analysis()
    print(f"Trend analysis completed: {result['message']}")
    if result["success"]:
        print(f"Trends detected: {result.get('trends_detected', 0)}")
        print(f"Items analyzed: {result.get('total_items_analyzed', 0)}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
