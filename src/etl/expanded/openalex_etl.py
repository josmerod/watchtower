"""OpenAlex ETL using BaseETL pattern.

Part of Phase 2 ETL implementation for academic research aggregation.
Includes 200M+ works, 50M+ authors, 80K+ venues from OpenAlex.

Author: Phase 2 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import requests

from src.etl.base import BaseETL
from src.models.openalex import (
    OpenAlexMetricsModel,
    OpenAlexWorkModel,
    WorkType,
)
from src.utils.logging import get_logger


class OpenAlexETL(BaseETL[dict[str, Any], OpenAlexWorkModel]):
    """ETL for OpenAlex - 200M+ Academic Works.

    Features:
    - 200M+ works (papers, books, datasets, etc.)
    - 50M+ authors with institutional data
    - 80K+ journals and conferences
    - Citation tracking and metrics
    - Open access identification
    - Concept-based classification

    API: https://docs.openalex.org/
    """

    def __init__(
        self,
        concepts: list[str] | None = None,
        institutions: list[str] | None = None,
        max_works: int = 1000,
        **kwargs,
    ):
        """Initialize OpenAlex ETL.

        Args:
            concepts: Research concepts to filter
            institutions: Institutions to filter
            max_works: Maximum works to fetch
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="openalex",
            description="OpenAlex ETL for 200M+ academic works",
            **kwargs,
        )

        # Default research concepts
        self.concepts = concepts or [
            "Artificial intelligence",
            "Machine learning",
            "Deep learning",
            "Computer science",
            "Software engineering",
            "Data science",
            "Python",
            "JavaScript",
        ]

        # Default institutions
        self.institutions = institutions or []

        self.max_works = max_works
        self.base_url = "https://api.openalex.org"

        # Metrics
        self.api_metrics = OpenAlexMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract works from OpenAlex API.

        Returns:
            List of raw work dictionaries.
        """
        self.logger.info("Starting extraction from OpenAlex")

        all_works = []

        # Extract by concepts
        for concept in self.concepts:
            try:
                works = self._fetch_by_concept(concept)
                all_works.extend(works)
                self.logger.info(f"Fetched {len(works)} works for concept: {concept}")
            except Exception as e:
                self.logger.error(f"Failed to fetch concept '{concept}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Concept failed: {concept}",
                    error_type=type(e).__name__,
                    context={"concept": concept},
                )

        self.logger.info(f"Extraction complete: {len(all_works)} total works")
        self.api_metrics.total_works_discovered = len(all_works)

        return all_works[: self.max_works]

    def _fetch_by_concept(self, concept: str) -> list[dict[str, Any]]:
        """Fetch works by research concept.

        Args:
            concept: Concept name

        Returns:
            List of work dictionaries.
        """
        url = f"{self.base_url}/works"
        # OpenAlex no longer accepts concept display names in a
        # `concepts.openalex:<name>` filter; that field expects IDs and now
        # returns HTTP 400 for names. Use the supported full-text/default search
        # filter as the no-auth public alternative.
        params = {
            "filter": f"default.search:{concept}",
            "per-page": 200,
            "sort": "publication_date:desc",
        }

        try:
            response = self.http_session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            self.api_metrics.successful_requests += 1

            # Add concept to each work
            for work in results:
                if "concepts" not in work:
                    work["concepts"] = []
                work["concepts"].append(concept)

            return results
        except requests.HTTPError as e:
            self.api_metrics.failed_requests += 1
            if e.response.status_code == 429:
                self.logger.warning("Rate limited by OpenAlex API")
            raise
        except Exception:
            self.api_metrics.failed_requests += 1
            raise

    def transform(self, raw_data: list[dict[str, Any]]) -> list[OpenAlexWorkModel]:
        """Transform raw OpenAlex data to models.

        Args:
            raw_data: List of raw work dictionaries

        Returns:
            List of OpenAlexWorkModel instances.
        """
        transformed = []

        for raw_work in raw_data:
            try:
                model = self._transform_work(raw_work)
                if model:
                    transformed.append(model)
            except Exception as e:
                self.logger.warning(f"Failed to transform work: {e}")
                self.metrics.records_failed += 1

        # Update metrics
        for work in transformed:
            work_type = getattr(work.type, "value", str(work.type))
            self.api_metrics.work_type_distribution[work_type] = self.api_metrics.work_type_distribution.get(work_type, 0) + 1

            if work.publication_year:
                year = str(work.publication_year)
                self.api_metrics.year_distribution[year] = self.api_metrics.year_distribution.get(year, 0) + 1

            self.api_metrics.total_citations += work.citations_count

            for concept in work.concepts:
                self.api_metrics.subject_distribution[concept] = self.api_metrics.subject_distribution.get(concept, 0) + 1

            if work.is_oa:
                self.api_metrics.oa_works += 1
            if work.is_highly_cited:
                self.api_metrics.highly_cited_works += 1

        if transformed:
            self.api_metrics.avg_citations_per_work = self.api_metrics.total_citations / len(transformed)

        self.logger.info(f"Transformed {len(transformed)} works")
        return transformed

    def _transform_work(self, raw: dict[str, Any]) -> OpenAlexWorkModel | None:
        """Transform single work.

        Args:
            raw: Raw work dictionary

        Returns:
            OpenAlexWorkModel or None if transformation fails.
        """
        work_id = raw.get("id")
        title = raw.get("title")

        if not work_id or not title:
            return None

        # Extract numeric ID from OpenAlex ID
        numeric_id = work_id.split("/")[-1] if "/" in work_id else work_id

        # Parse type
        type_str = raw.get("type", "journal-article")
        try:
            work_type = WorkType(type_str)
        except ValueError:
            work_type = WorkType.OTHER

        # Extract venue
        primary_location = raw.get("primary_location") or {}
        source = primary_location.get("source") or {}
        venue_id = source.get("id")
        venue_name = source.get("display_name")
        venue_issn = source.get("issn")
        if isinstance(venue_issn, list):
            venue_issn = venue_issn[0] if venue_issn else None
        publisher = source.get("publisher")

        # Extract authors
        authorships = raw.get("authorships") or []
        author_ids = [str(a.get("author", {}).get("id")) for a in authorships if a.get("author")]

        # Extract concepts. OpenAlex can return concept objects, and this ETL
        # also appends the query concept as a string for traceability.
        concepts_data = raw.get("concepts") or []
        concepts = []
        for concept in concepts_data:
            if isinstance(concept, str):
                concepts.append(concept)
            elif isinstance(concept, dict):
                score = concept.get("score")
                # OpenAlex concept scores are usually 0-1; old code compared
                # to 50, which discarded every valid concept.
                if concept.get("display_name") and (score is None or score > 0.3):
                    concepts.append(concept["display_name"])

        # Extract year
        publication_year = raw.get("publication_year")
        if publication_year:
            publication_year = int(publication_year)

        # Parse dates
        created_date = raw.get("created_date")
        if created_date:
            try:
                publication_date = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
            except ValueError:
                publication_date = None
        else:
            publication_date = None

        # Open access info
        open_access = raw.get("open_access") or {}
        is_oa = open_access.get("is_oa", False)
        oa_url = open_access.get("oa_url")

        return OpenAlexWorkModel(
            work_id=numeric_id,
            title=title,
            type=work_type,
            doi=raw.get("doi"),
            url=raw.get("id"),
            venue_id=venue_id,
            venue_name=venue_name,
            venue_issn=venue_issn,
            publisher=publisher,
            author_ids=author_ids,
            authors_count=len(author_ids),
            citations_count=raw.get("cited_by_count", 0),
            h_index=raw.get("h_index"),
            impact_factor=raw.get("impact_factor"),
            publication_year=publication_year,
            publication_date=publication_date,
            abstract=raw.get("abstract"),
            concepts=concepts,
            is_oa=is_oa,
            oa_url=oa_url,
            language=raw.get("language"),
            original_id=numeric_id,
            metadata=raw,
        )

    def load(self, data: list[OpenAlexWorkModel]) -> None:
        """Load works to JSON storage.

        Args:
            data: List of OpenAlexWorkModel instances.
        """
        # Convert to dicts
        works_data = [w.model_dump(mode="json") for w in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"openalex_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(works_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "openalex_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(works_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "openalex_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} works to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for OpenAlex ETL."""
    logger = get_logger("OpenAlexETL")
    logger.info("Starting OpenAlex ETL")

    try:
        etl = OpenAlexETL()
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
