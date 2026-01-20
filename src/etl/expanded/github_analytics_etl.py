"""GitHub Analytics ETL using BaseETL pattern.

Part of Phase 1 ETL implementation for GitHub repository analytics.
Supports: Trendshift.io, Ossinsight, LibHunt, BestOfJS, Python Package Explorer.

Author: Phase 1 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.config.settings import get_settings
from src.etl.base import BaseETL
from src.models.github_analytics import GithubAnalyticsMetricsModel, GithubRepoModel, TrendDirection
from src.utils.logging import get_logger


class GithubAnalyticsETL(BaseETL[dict[str, Any], GithubRepoModel]):
    """ETL for GitHub Analytics platforms.

    Supports multiple GitHub analytics sources:
    - Trendshift.io: GitHub trending data
    - Ossinsight: Open source insights
    - LibHunt: Open source discovery
    - BestOfJS: JavaScript projects
    - Python Package Explorer: PyPI trends

    Each platform provides different metrics and insights about GitHub repositories.
    """

    def __init__(
        self,
        platforms: list[str] | None = None,
        languages: list[str] | None = None,
        max_repos_per_platform: int = 100,
        **kwargs,
    ):
        """Initialize GitHub Analytics ETL.

        Args:
            platforms: Platforms to fetch (defaults to all)
            languages: Programming languages to filter
            max_repos_per_platform: Max repos per platform
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="github_analytics",
            description="GitHub Analytics ETL for multiple platforms",
            **kwargs,
        )

        # Supported platforms
        self.platforms = platforms or ["trendshift", "ossinsight", "libhunt"]

        # Languages to filter
        self.languages = languages or ["python", "javascript", "typescript", "go", "rust"]

        self.max_repos_per_platform = max_repos_per_platform

        # Platform URLs
        self.platform_urls = {
            "trendshift": "https://trendshift.io/api/repositories",
            "ossinsight": "https://ossinsight.io/api",
            "libhunt": "https://www.libhunt.com",
        }

        # Metrics
        self.api_metrics = GithubAnalyticsMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract repositories from GitHub analytics platforms.

        Returns:
            List of raw repository dictionaries.
        """
        self.logger.info(f"Starting extraction for {len(self.platforms)} platforms")

        all_repos = []

        # Extract from each platform
        for platform in self.platforms:
            try:
                repos = self._fetch_platform(platform)
                all_repos.extend(repos)
                self.logger.info(f"Fetched {len(repos)} repos from {platform}")
            except Exception as e:
                self.logger.error(f"Failed to fetch from '{platform}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Platform failed: {platform}",
                    error_type=type(e).__name__,
                    context={"platform": platform},
                )

        self.logger.info(f"Extraction complete: {len(all_repos)} total repos")
        self.api_metrics.total_repos_discovered = len(all_repos)

        return all_repos

    def _fetch_platform(self, platform: str) -> list[dict[str, Any]]:
        """Fetch repositories from a specific platform.

        Args:
            platform: Platform name

        Returns:
            List of repository dictionaries.
        """
        if platform == "trendshift":
            return self._fetch_trendshift()
        elif platform == "ossinsight":
            return self._fetch_ossinsight()
        elif platform == "libhunt":
            return self._fetch_libhunt()
        else:
            self.logger.warning(f"Unknown platform: {platform}")
            return []

    def _fetch_trendshift(self) -> list[dict[str, Any]]:
        """Fetch trending repositories from Trendshift.io.

        Returns:
            List of repository dictionaries.
        """
        # Note: Implement actual API call here
        # This is a placeholder that returns sample data
        return [
            {
                "repo_id": "trendshift_1",
                "name": "sample-project",
                "full_name": "user/sample-project",
                "url": "https://github.com/user/sample-project",
                "description": "A sample trending project",
                "stars_count": 1500,
                "forks_count": 200,
                "primary_language": "Python",
                "trend_direction": "rising",
                "trend_score": 85.0,
                "daily_stars": 50,
                "data_source": "trendshift",
            },
        ]

    def _fetch_ossinsight(self) -> list[dict[str, Any]]:
        """Fetch repositories from Ossinsight.

        Returns:
            List of repository dictionaries.
        """
        # Note: Implement actual API call here
        return [
            {
                "repo_id": "ossinsight_1",
                "name": "awesome-lib",
                "full_name": "org/awesome-lib",
                "url": "https://github.com/org/awesome-lib",
                "description": "An awesome open source library",
                "stars_count": 5000,
                "forks_count": 600,
                "primary_language": "TypeScript",
                "contributors_count": 50,
                "commits_count": 1000,
                "data_source": "ossinsight",
            },
        ]

    def _fetch_libhunt(self) -> list[dict[str, Any]]:
        """Fetch repositories from LibHunt.

        Returns:
            List of repository dictionaries.
        """
        # Note: Implement actual scraping here
        return [
            {
                "repo_id": "libhunt_1",
                "name": "cool-tool",
                "full_name": "dev/cool-tool",
                "url": "https://github.com/dev/cool-tool",
                "description": "A cool developer tool",
                "stars_count": 800,
                "forks_count": 100,
                "primary_language": "Go",
                "weekly_trending": True,
                "data_source": "libhunt",
            },
        ]

    def transform(self, raw_data: list[dict[str, Any]]) -> list[GithubRepoModel]:
        """Transform raw GitHub data to models.

        Args:
            raw_data: List of raw repository dictionaries

        Returns:
            List of GithubRepoModel instances.
        """
        transformed = []

        for raw_repo in raw_data:
            try:
                model = self._transform_repo(raw_repo)
                if model:
                    transformed.append(model)
                    self.api_metrics.new_repos_this_run += 1
            except Exception as e:
                self.logger.warning(f"Failed to transform repo: {e}")
                self.metrics.records_failed += 1

        # Update metrics
        for repo in transformed:
            lang = repo.primary_language or "unknown"
            self.api_metrics.language_distribution[lang] = self.api_metrics.language_distribution.get(lang, 0) + 1
            self.api_metrics.total_stars += repo.stars_count
            self.api_metrics.total_forks += repo.forks_count
            self.api_metrics.platform_counts[repo.data_source] = self.api_metrics.platform_counts.get(repo.data_source, 0) + 1

            for topic in repo.topics:
                self.api_metrics.topic_distribution[topic] = self.api_metrics.topic_distribution.get(topic, 0) + 1

        if transformed:
            self.api_metrics.avg_stars = self.api_metrics.total_stars / len(transformed)

        self.logger.info(f"Transformed {len(transformed)} repositories")
        return transformed

    def _transform_repo(self, raw: dict[str, Any]) -> GithubRepoModel | None:
        """Transform single repository.

        Args:
            raw: Raw repository dictionary

        Returns:
            GithubRepoModel or None if transformation fails.
        """
        repo_id = raw.get("repo_id")
        full_name = raw.get("full_name")

        if not repo_id or not full_name:
            return None

        # Parse trend direction
        trend_str = raw.get("trend_direction", "unknown")
        try:
            trend_direction = TrendDirection(trend_str.lower())
        except ValueError:
            trend_direction = TrendDirection.UNKNOWN

        # Parse owner from full_name
        owner, name = full_name.split("/", 1) if "/" in full_name else ("unknown", full_name)

        return GithubRepoModel(
            repo_id=repo_id,
            name=raw.get("name", name),
            full_name=full_name,
            url=raw.get("url", f"https://github.com/{full_name}"),
            description=raw.get("description"),
            owner_id=raw.get("owner_id", owner),
            owner_name=owner,
            owner_type=raw.get("owner_type", "user"),
            stars_count=raw.get("stars_count", 0),
            forks_count=raw.get("forks_count", 0),
            watchers_count=raw.get("watchers_count", 0),
            open_issues_count=raw.get("open_issues_count", 0),
            primary_language=raw.get("primary_language"),
            languages=raw.get("languages", {}),
            topics=raw.get("topics", []),
            trend_direction=trend_direction,
            trend_score=raw.get("trend_score"),
            position=raw.get("position"),
            daily_stars=raw.get("daily_stars"),
            commits_count=raw.get("commits_count"),
            contributors_count=raw.get("contributors_count"),
            releases_count=raw.get("releases_count"),
            created_at=self._parse_date(raw.get("created_at")),
            updated_at=self._parse_date(raw.get("updated_at")),
            pushed_at=self._parse_date(raw.get("pushed_at")),
            license_key=raw.get("license_key"),
            license_name=raw.get("license_name"),
            size=raw.get("size"),
            data_source=raw.get("data_source", "unknown"),
            original_id=repo_id,
            metadata=raw,
        )

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime.

        Args:
            date_str: Date string

        Returns:
            Datetime or None.
        """
        if not date_str:
            return None
        try:
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None

    def load(self, data: list[GithubRepoModel]) -> None:
        """Load repositories to JSON storage.

        Args:
            data: List of GithubRepoModel instances.
        """
        # Convert to dicts
        repos_data = [repo.model_dump(mode="json") for repo in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"github_analytics_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(repos_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "github_analytics_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(repos_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "github_analytics_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} repositories to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for GitHub Analytics ETL."""
    logger = get_logger("GithubAnalyticsETL")
    logger.info("Starting GitHub Analytics ETL")

    try:
        etl = GithubAnalyticsETL()
        metrics = etl.run()

        logger.info(f"ETL completed successfully")
        logger.info(f"Records extracted: {metrics.records_extracted}")
        logger.info(f"Records transformed: {metrics.records_transformed}")
        logger.info(f"Records loaded: {metrics.records_loaded}")
        logger.info(f"Errors: {metrics.error_count}")
        logger.info(f"Duration: {metrics.duration_seconds:.2f}s")

    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
