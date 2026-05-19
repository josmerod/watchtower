"""Stack Exchange ETL using BaseETL pattern.

Part of Phase 2 ETL implementation for Stack Exchange Network.
Supports 180+ sites including Stack Overflow, Server Fault, Super User, etc.

Author: Phase 2 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
import time as _time
from datetime import datetime
from typing import Any

import requests

from src.config.settings import get_settings
from src.etl.base import BaseETL
from src.models.stackexchange import (
    StackExchangeMetricsModel,
    StackExchangeQuestionModel,
    StackExchangeSite,
)
from src.utils.logging import get_logger


class StackExchangeETL(BaseETL[dict[str, Any], StackExchangeQuestionModel]):
    """ETL for Stack Exchange Network - 180+ Q&A sites.

    Features:
    - Multi-site support (Stack Overflow, Server Fault, etc.)
    - Question and answer tracking
    - Tag-based filtering
    - Engagement metrics
    - Reputation tracking

    API: https://api.stackexchange.com/
    """

    def __init__(
        self,
        sites: list[str] | None = None,
        tags: list[str] | None = None,
        max_questions_per_site: int = 100,
        api_key: str | None = None,
        **kwargs,
    ):
        """Initialize Stack Exchange ETL.

        Args:
            sites: Sites to fetch (defaults to major sites)
            tags: Tags to filter questions
            max_questions_per_site: Max questions per site
            api_key: Stack Exchange API key (higher rate limits)
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="stackexchange",
            description="Stack Exchange Network ETL for 180+ Q&A sites",
            **kwargs,
        )

        self.settings = get_settings()
        self.api_key = api_key or getattr(self.settings.api, "stackexchange_key", None)

        # Default major sites
        self.sites = sites or [
            "stackoverflow",
            "serverfault",
            "superuser",
            "askubuntu",
            "mathematics",
            "gaming",
            "softwareengineering",
        ]

        # Default programming tags for Stack Overflow
        self.tags = tags or [
            "python",
            "javascript",
            "java",
            "c#",
            "react",
            "node.js",
            "machine-learning",
            "docker",
        ]

        self.max_questions_per_site = max_questions_per_site
        self.base_url = "https://api.stackexchange.com/2.3"

        # Metrics
        self.api_metrics = StackExchangeMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract questions from Stack Exchange API.

        Returns:
            List of raw question dictionaries.
        """
        self.logger.info(f"Starting extraction for {len(self.sites)} sites")

        all_questions = []

        # Extract from each site
        for site in self.sites:
            try:
                questions = self._fetch_site_questions(site)
                all_questions.extend(questions)
                _time.sleep(2)  # Rate limit: avoid 429 from Stack Exchange API
                self.logger.info(f"Fetched {len(questions)} questions from {site}")
            except Exception as e:
                self.logger.error(f"Failed to fetch site '{site}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Site failed: {site}",
                    error_type=type(e).__name__,
                    context={"site": site},
                )

        self.logger.info(f"Extraction complete: {len(all_questions)} total questions")
        self.api_metrics.total_questions_discovered = len(all_questions)

        return all_questions

    def _fetch_site_questions(self, site: str) -> list[dict[str, Any]]:
        """Fetch questions from a specific site.

        Args:
            site: Site API name (e.g., "stackoverflow")

        Returns:
            List of question dictionaries.
        """
        url = f"{self.base_url}/questions"
        params = {
            "order": "desc",
            "sort": "activity",
            "site": site,
            "pagesize": min(100, self.max_questions_per_site),
            "filter": "withbody",
        }

        # Add tag filtering for Stack Overflow
        if site == "stackoverflow" and self.tags:
            params["tagged"] = ";".join(self.tags[:5])  # API limit: 5 tags max

        # Add API key if available (higher rate limits)
        if self.api_key:
            params["key"] = self.api_key

        try:
            response = self.http_session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.api_metrics.successful_requests += 1

            items = data.get("items", [])
            # Add site information to each question
            for item in items:
                item["site"] = site
                item["site_name"] = site.replace(".", " ").title()
                item["site_url"] = f"https://{site}.com" if "." in site else f"https://{site}.stackexchange.com"

            return items
        except requests.HTTPError as e:
            self.api_metrics.failed_requests += 1
            if e.response.status_code == 429:
                self.logger.warning("Rate limited by Stack Exchange API")
            raise
        except Exception:
            self.api_metrics.failed_requests += 1
            raise

    def transform(self, raw_data: list[dict[str, Any]]) -> list[StackExchangeQuestionModel]:
        """Transform raw Stack Exchange data to models.

        Args:
            raw_data: List of raw question dictionaries

        Returns:
            List of StackExchangeQuestionModel instances.
        """
        transformed = []

        for raw_question in raw_data:
            try:
                model = self._transform_question(raw_question)
                if model:
                    transformed.append(model)
                    self.api_metrics.new_questions_this_run += 1
            except Exception as e:
                self.logger.warning(f"Failed to transform question: {e}")
                self.metrics.records_failed += 1

        # Update metrics
        for question in transformed:
            site = question.site.value if isinstance(question.site, StackExchangeSite) else str(question.site)
            self.api_metrics.site_distribution[site] = self.api_metrics.site_distribution.get(site, 0) + 1

            for tag in question.tags:
                self.api_metrics.tag_distribution[tag] = self.api_metrics.tag_distribution.get(tag, 0) + 1

            self.api_metrics.avg_score = (self.api_metrics.avg_score or 0) + question.score
            self.api_metrics.avg_answers = (self.api_metrics.avg_answers or 0) + question.answers_count

            if question.answers_count > 0:
                self.api_metrics.answered_questions += 1
            if question.is_answered:
                self.api_metrics.accepted_answers += 1
            if question.is_trending:
                self.api_metrics.trending_questions += 1

        if transformed:
            self.api_metrics.avg_score = (self.api_metrics.avg_score or 0) / len(transformed)
            self.api_metrics.avg_answers = (self.api_metrics.avg_answers or 0) / len(transformed)

        self.logger.info(f"Transformed {len(transformed)} questions")
        return transformed

    def _transform_question(self, raw: dict[str, Any]) -> StackExchangeQuestionModel | None:
        """Transform single question.

        Args:
            raw: Raw question dictionary

        Returns:
            StackExchangeQuestionModel or None if transformation fails.
        """
        question_id = str(raw.get("question_id"))
        title = raw.get("title")

        if not question_id or not title:
            return None

        # Parse site
        site_str = raw.get("site", "stackoverflow")
        try:
            site = StackExchangeSite(site_str)
        except ValueError:
            site = StackExchangeSite.STACKOVERFLOW

        # Parse owner
        owner = raw.get("owner", {})
        author_id = str(owner.get("user_id", "unknown"))
        author_name = owner.get("display_name", "Unknown")

        # Parse dates
        created_at = self._parse_date(raw.get("creation_date"))
        last_activity_at = self._parse_date(raw.get("last_activity_date"))

        # Get accepted answer ID
        accepted_answer = raw.get("accepted_answer_id")
        if accepted_answer:
            accepted_answer = str(accepted_answer)

        return StackExchangeQuestionModel(
            question_id=question_id,
            title=title,
            body=raw.get("body"),
            excerpt=raw.get("excerpt"),
            url=raw.get("link", f"https://{site_str}.com/questions/{question_id}"),
            site=site,
            site_name=raw.get("site_name", site_str.title()),
            site_url=raw.get("site_url"),
            author_id=author_id,
            author_name=author_name,
            author_reputation=owner.get("reputation", 0),
            score=raw.get("score", 0),
            views_count=raw.get("view_count", 0),
            answers_count=raw.get("answer_count", 0),
            comments_count=raw.get("comment_count", 0),
            is_answered=raw.get("is_answered", False),
            accepted_answer_id=accepted_answer,
            tags=raw.get("tags", []),
            api_created_at=created_at,
            last_activity_at=last_activity_at,
            original_id=question_id,
            metadata=raw,
        )

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime.

        Args:
            date_str: Date string (Unix timestamp or ISO format)

        Returns:
            Datetime or None.
        """
        if not date_str:
            return None
        try:
            # Stack Exchange uses Unix timestamps
            if isinstance(date_str, (int, float)) or date_str.isdigit():
                return datetime.fromtimestamp(int(date_str))
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, OSError):
            return None

    def load(self, data: list[StackExchangeQuestionModel]) -> None:
        """Load questions to JSON storage.

        Args:
            data: List of StackExchangeQuestionModel instances.
        """
        # Convert to dicts
        questions_data = [q.model_dump(mode="json") for q in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"stackexchange_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "stackexchange_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "stackexchange_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} questions to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for Stack Exchange ETL."""
    logger = get_logger("StackExchangeETL")
    logger.info("Starting Stack Exchange ETL")

    try:
        etl = StackExchangeETL()
        metrics = etl.run()

        logger.info("ETL completed successfully")
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
