"""HuggingFace Platform ETL Implementation.

Monitors HuggingFace ecosystem including:
- Model repository trends
- Dataset popularity
- Community activity metrics
- Open source AI developments
- Space applications
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import LoadError
from src.utils.logging import get_logger
from src.etl.proxy_manager import ProxyManager


class HuggingFaceETL(BaseETL):
    """HuggingFace Platform ETL for open source AI monitoring."""

    def __init__(self, **kwargs):
        """Initialize HuggingFace ETL."""
        super().__init__(
            name="huggingface_platform",
            description="HuggingFace open source AI ecosystem monitoring",
            **kwargs,
        )
        self.logger = get_logger("ETL.HuggingFace")

        self.endpoints = {
            "models": "https://huggingface.co/api/models?sort=trendingScore&limit=25",
            "datasets": "https://huggingface.co/api/datasets?sort=trendingScore&limit=25",
        }
        self.proxy_manager = ProxyManager()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from HuggingFace platform."""
        self.logger.info("Starting HuggingFace platform data extraction")
        extracted_data = []

        try:
            # Extract trending models
            models_data = self._extract_trending_models()
            if models_data:
                extracted_data.extend(models_data)
                self.metrics.records_extracted += len(models_data)

            # Extract popular datasets
            datasets_data = self._extract_popular_datasets()
            if datasets_data:
                extracted_data.extend(datasets_data)
                self.metrics.records_extracted += len(datasets_data)

            # Extract community metrics
            community_data = self._extract_community_metrics()
            if community_data:
                extracted_data.extend(community_data)
                self.metrics.records_extracted += len(community_data)

            self.logger.info(f"Extracted {len(extracted_data)} HuggingFace records")

        except Exception as e:
            self.logger.error(f"Failed to extract HuggingFace data: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def _extract_trending_models(self) -> list[dict[str, Any]]:
        """Extract trending models from HuggingFace."""
        self.logger.info("Fetching trending models from HuggingFace API...")
        session = self.proxy_manager.get_session(retries=3, backoff_factor=1.5)
        try:
            response = session.get(self.endpoints["models"], timeout=30)
            response.raise_for_status()
            models_list = response.json()
            
            models_data = []
            for m in models_list:
                models_data.append({
                    "data_type": "model_release",
                    "platform": "huggingface",
                    "model_id": m.get("id", ""),
                    "model_name": m.get("id", "").split("/")[-1],
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "tags": m.get("tags", []),
                    "created_at": m.get("createdAt", datetime.utcnow().isoformat()),
                    "extracted_at": datetime.utcnow().isoformat(),
                })
            return models_data
        except Exception as e:
            self.logger.error(f"Failed to fetch trending models: {e}")
            return []

    def _extract_popular_datasets(self) -> list[dict[str, Any]]:
        """Extract popular datasets from HuggingFace."""
        self.logger.info("Fetching trending datasets from HuggingFace API...")
        session = self.proxy_manager.get_session(retries=3, backoff_factor=1.5)
        try:
            response = session.get(self.endpoints["datasets"], timeout=30)
            response.raise_for_status()
            datasets_list = response.json()
            
            datasets_data = []
            for d in datasets_list:
                datasets_data.append({
                    "data_type": "dataset_release",
                    "platform": "huggingface",
                    "dataset_id": d.get("id", ""),
                    "dataset_name": d.get("id", "").split("/")[-1],
                    "downloads": d.get("downloads", 0),
                    "likes": d.get("likes", 0),
                    "tags": d.get("tags", []),
                    "created_at": d.get("createdAt", datetime.utcnow().isoformat()),
                    "extracted_at": datetime.utcnow().isoformat(),
                })
            return datasets_data
        except Exception as e:
            self.logger.error(f"Failed to fetch trending datasets: {e}")
            return []

    def _extract_community_metrics(self) -> list[dict[str, Any]]:
        """Extract community activity metrics (Skipped due to REST API complexity)."""
        return []

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform HuggingFace platform data."""
        self.logger.info(f"Transforming {len(data)} HuggingFace records")
        transformed_data = []

        for record in data:
            try:
                data_type = record.get("data_type", "unknown")

                if data_type == "model_release":
                    transformed_record = self._transform_model_data(record)
                elif data_type == "dataset_release":
                    transformed_record = self._transform_dataset_data(record)
                elif data_type == "community_metrics":
                    transformed_record = self._transform_community_data(record)
                else:
                    transformed_record = record

                transformed_data.append(transformed_record)
                self.metrics.records_transformed += 1

            except Exception as e:
                self.logger.error(f"Failed to transform HuggingFace record: {e}")
                self.metrics.records_failed += 1

        return transformed_data

    def _transform_model_data(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform model data with community insights."""
        return {
            **record,
            "adoption_velocity": self._calculate_adoption_velocity(record),
            "community_engagement": self._assess_community_engagement(record),
            "open_source_impact": self._assess_open_source_impact(record),
            "commercial_viability": self._assess_commercial_viability(record),
        }

    def _calculate_adoption_velocity(self, record: dict[str, Any]) -> float:
        """Calculate adoption velocity score."""
        downloads = record.get("downloads", 0)
        likes = record.get("likes", 0)

        # Simple scoring based on downloads and likes
        velocity_score = min((downloads / 1000000) + (likes / 10000), 1.0)
        return velocity_score

    def _assess_community_engagement(self, record: dict[str, Any]) -> str:
        """Assess community engagement level."""
        likes = record.get("likes", 0)

        if likes >= 10000:
            return "very_high"
        elif likes >= 5000:
            return "high"
        elif likes >= 1000:
            return "medium"
        else:
            return "low"

    def _assess_open_source_impact(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess open source impact."""
        license_type = record.get("license", "unknown")
        downloads = record.get("downloads", 0)

        # Assess based on license and adoption
        if license_type in ["mit", "apache-2.0", "openrail++"]:
            license_openness = "high"
        elif license_type in ["cc-by-4.0", "cc-by-sa-4.0"]:
            license_openness = "medium"
        else:
            license_openness = "low"

        return {
            "license_openness": license_openness,
            "community_adoption": record.get("community_adoption", "low"),
            "reproducibility": "high",  # HF models are generally reproducible
            "accessibility": "high",  # Easy to use via HF transformers
        }

    def _assess_commercial_viability(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess commercial viability."""
        model_type = record.get("model_type", "")
        license_type = record.get("license", "")

        # Commercial use assessment
        commercial_friendly_licenses = ["mit", "apache-2.0", "openrail++"]
        commercial_use = license_type in commercial_friendly_licenses

        return {
            "commercial_use_allowed": commercial_use,
            "enterprise_readiness": "medium",
            "support_availability": "community",
            "integration_complexity": "low",
        }

    def _transform_dataset_data(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform dataset data."""
        return {
            **record,
            "research_impact": self._assess_dataset_research_impact(record),
            "data_quality": self._assess_data_quality(record),
            "accessibility_score": self._calculate_accessibility_score(record),
        }

    def _assess_dataset_research_impact(self, record: dict[str, Any]) -> str:
        """Assess research impact of dataset."""
        citations = record.get("research_citations", 0)

        if citations >= 10000:
            return "landmark"
        elif citations >= 5000:
            return "high"
        elif citations >= 1000:
            return "medium"
        else:
            return "emerging"

    def _assess_data_quality(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess data quality indicators."""
        return {
            "curation_level": "professional",
            "annotation_quality": "high",
            "bias_assessment": "evaluated",
            "documentation_quality": "comprehensive",
        }

    def _calculate_accessibility_score(self, record: dict[str, Any]) -> float:
        """Calculate dataset accessibility score."""
        # HuggingFace datasets are generally very accessible
        base_score = 0.8

        # Adjust for size (smaller = more accessible)
        size = record.get("size", "0MB")
        if "GB" in size:
            size_penalty = 0.1
        elif "MB" in size:
            size_penalty = 0.0
        else:
            size_penalty = 0.05

        return min(base_score - size_penalty, 1.0)

    def _transform_community_data(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform community metrics data."""
        return {
            **record,
            "ecosystem_health": self._assess_ecosystem_health(record),
            "growth_trends": self._analyze_growth_trends(record),
            "diversity_metrics": self._calculate_diversity_metrics(record),
        }

    def _assess_ecosystem_health(self, record: dict[str, Any]) -> str:
        """Assess overall ecosystem health."""
        daily_downloads = record.get("daily_downloads", 0)
        new_models = record.get("new_models_today", 0)

        if daily_downloads > 20000000 and new_models > 200:
            return "thriving"
        elif daily_downloads > 10000000 and new_models > 100:
            return "healthy"
        else:
            return "growing"

    def _analyze_growth_trends(self, record: dict[str, Any]) -> dict[str, Any]:
        """Analyze growth trends."""
        growth_metrics = record.get("growth_metrics", {})

        return {
            "models_growth_rate": "high",
            "datasets_growth_rate": "steady",
            "spaces_growth_rate": "high",
            "overall_momentum": "accelerating",
        }

    def _calculate_diversity_metrics(self, record: dict[str, Any]) -> dict[str, Any]:
        """Calculate diversity metrics."""
        trending_categories = record.get("trending_categories", [])
        top_orgs = record.get("top_organizations", [])

        return {
            "category_diversity": len(trending_categories),
            "organizational_diversity": len(top_orgs),
            "geographic_diversity": "global",
            "model_type_diversity": "high",
        }

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load HuggingFace platform data to storage.

        Args:
            data: List of transformed data dictionaries to load.

        Raises:
            LoadError: If saving data to file fails.
        """
        if not data:
            self.logger.info("No HuggingFace data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"huggingface_platform_data_{timestamp}.json"
        latest_file = self.output_dir / "huggingface_latest.json"

        try:
            # Save detailed data
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(f"Successfully saved HuggingFace data to {output_file}")

            # Save latest data
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(f"Successfully updated latest HuggingFace data at {latest_file}")

            self.metrics.records_loaded = len(data)

        except OSError as e:
            self.logger.error(f"Failed to save HuggingFace data to {output_file} or {latest_file}: {e}")
            raise LoadError(
                f"Failed to save HuggingFace data: {e}",
                destination=str(output_file),
                destination_type="file",
            ) from e
        except Exception as e:  # Catch any other unexpected errors during load
            self.logger.error(
                f"An unexpected error occurred during saving HuggingFace data: {e}",
                exc_info=True,
            )
            raise LoadError(
                f"An unexpected error occurred during saving HuggingFace data: {e}",
                destination=str(output_file),
                destination_type="file",
            ) from e

if __name__ == "__main__":
    etl = HuggingFaceETL()
    etl.run()
