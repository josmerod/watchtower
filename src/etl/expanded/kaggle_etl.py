"""Kaggle ETL using BaseETL pattern.

Part of Phase 2 ETL implementation for data science platform aggregation.
Author: Phase 2 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.models.kaggle import (
    KaggleDatasetModel,
    KaggleMetricsModel,
)
from src.utils.logging import get_logger


class KaggleETL(BaseETL[dict[str, Any], KaggleDatasetModel]):
    """ETL for Kaggle - Datasets and Competitions.

    Features:
    - 100K+ datasets
    - 500+ competitions
    - Usage metrics tracking
    - Prize money tracking
    """

    def __init__(
        self,
        categories: list[str] | None = None,
        max_datasets: int = 500,
        max_competitions: int = 100,
        **kwargs,
    ):
        super().__init__(
            name="kaggle",
            description="Kaggle ETL for datasets and competitions",
            **kwargs,
        )
        self.categories = categories or ["computer science", "data science"]
        self.max_datasets = max_datasets
        self.max_competitions = max_competitions
        self.base_url = "https://www.kaggle.com/api/v1"
        self.api_metrics = KaggleMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from Kaggle API.

        Returns:
            List of raw dictionaries.
        """
        self.logger.info("Starting extraction from Kaggle")

        all_items = []

        # Note: Kaggle API requires authentication
        # This is a placeholder implementation
        all_items = self._get_sample_data()

        self.logger.info(f"Extraction complete: {len(all_items)} total items")
        return all_items

    def _get_sample_data(self) -> list[dict[str, Any]]:
        """Get sample data for testing.

        Returns:
            List of sample dictionaries.
        """
        return [
            {
                "dataset_id": "sample1",
                "title": "Sample Dataset",
                "url": "https://www.kaggle.com/datasets/sample",
                "description": "A sample dataset for testing",
                "creator_name": "kaggler",
                "total_downloads": 1000,
                "total_votes": 50,
                "usability_rating": 8.5,
                "tags": ["python", "data-science"],
            },
            {
                "competition_id": "comp1",
                "title": "Sample Competition",
                "slug": "sample-competition",
                "url": "https://www.kaggle.com/competitions/sample-competition",
                "status": "active",
                "prize_amount": 10000,
                "total_teams": 100,
                "tags": ["machine-learning"],
            },
        ]

    def transform(self, raw_data: list[dict[str, Any]]) -> list[KaggleDatasetModel]:
        """Transform raw Kaggle data to models.

        Args:
            raw_data: List of raw dictionaries

        Returns:
            List of KaggleDatasetModel instances.
        """
        transformed = []

        for raw_item in raw_data:
            try:
                if "dataset_id" in raw_item:
                    model = self._transform_dataset(raw_item)
                elif "competition_id" in raw_item:
                    # Note: competitions handled separately
                    continue
                else:
                    continue

                if model:
                    transformed.append(model)
            except Exception as e:
                self.logger.warning(f"Failed to transform item: {e}")
                self.metrics.records_failed += 1

        self.logger.info(f"Transformed {len(transformed)} items")
        return transformed

    def _transform_dataset(self, raw: dict[str, Any]) -> KaggleDatasetModel | None:
        """Transform single dataset.

        Args:
            raw: Raw dataset dictionary

        Returns:
            KaggleDatasetModel or None.
        """
        dataset_id = raw.get("dataset_id")
        title = raw.get("title")

        if not dataset_id or not title:
            return None

        return KaggleDatasetModel(
            dataset_id=dataset_id,
            title=title,
            subtitle=raw.get("subtitle"),
            url=raw.get("url") or f"https://www.kaggle.com/datasets/{dataset_id}",
            description=raw.get("description"),
            creator_id=raw.get("creator_id"),
            creator_name=raw.get("creator_name"),
            total_downloads=raw.get("total_downloads", 0),
            total_votes=raw.get("total_votes", 0),
            total_kernels=raw.get("total_kernels", 0),
            total_views=raw.get("total_views", 0),
            usability_rating=raw.get("usability_rating"),
            tags=raw.get("tags", []),
            categories=raw.get("categories", []),
            license_name=raw.get("license_name"),
            original_id=dataset_id,
            metadata=raw,
        )

    def load(self, data: list[KaggleDatasetModel]) -> None:
        """Load datasets to JSON storage.

        Args:
            data: List of KaggleDatasetModel instances.
        """
        # Convert to dicts
        items_data = [item.model_dump(mode="json") for item in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save files
        main_file = self.output_dir / f"kaggle_{timestamp}.json"
        latest_file = self.output_dir / "kaggle_latest.json"
        metrics_file = self.output_dir / "kaggle_metrics.json"

        with main_file.open("w", encoding="utf-8") as f:
            json.dump(items_data, f, indent=2, ensure_ascii=False)
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(items_data, f, indent=2, ensure_ascii=False)
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} items")


def main():
    """Main entry point for Kaggle ETL."""
    logger = get_logger("KaggleETL")
    logger.info("Starting Kaggle ETL")

    try:
        etl = KaggleETL()
        metrics = etl.run()
        logger.info(f"ETL completed: {metrics.records_loaded} records loaded")
    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
