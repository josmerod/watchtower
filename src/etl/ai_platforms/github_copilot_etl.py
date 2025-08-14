"""GitHub Copilot ETL Implementation.

Monitors GitHub Copilot ecosystem including:
- Code generation usage statistics
- Feature updates and improvements
- Developer adoption metrics
- Enterprise integration developments
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
import os  # Required for IOError, OSError

from src.etl.base import BaseETL
from src.utils.logging import get_logger
from src.exceptions.etl import LoadError


class GitHubCopilotETL(BaseETL):
    """GitHub Copilot ETL for developer tool monitoring."""

    def __init__(self, **kwargs):
        """Initialize GitHub Copilot ETL."""
        super().__init__(
            name="github_copilot",
            description="GitHub Copilot code generation tool monitoring",
            **kwargs,
        )
        self.logger = get_logger("ETL.GitHubCopilot")

        self.endpoints = {
            "docs": "https://docs.github.com/en/copilot",
            "blog": "https://github.blog/tag/github-copilot/",
            "pricing": "https://github.com/features/copilot",
            "enterprise": "https://github.com/enterprise",
        }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from GitHub Copilot platform."""
        self.logger.info("Starting GitHub Copilot data extraction")
        extracted_data = []

        try:
            # Extract usage metrics (mock data for now)
            usage_data = self._extract_usage_metrics()
            if usage_data:
                extracted_data.extend(usage_data)
                self.metrics.records_extracted += len(usage_data)

            # Extract feature updates
            feature_data = self._extract_feature_updates()
            if feature_data:
                extracted_data.extend(feature_data)
                self.metrics.records_extracted += len(feature_data)

            self.logger.info(f"Extracted {len(extracted_data)} GitHub Copilot records")

        except Exception as e:
            self.logger.error(f"Failed to extract GitHub Copilot data: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def _extract_usage_metrics(self) -> list[dict[str, Any]]:
        """Extract GitHub Copilot usage metrics."""
        usage_data = []

        # Mock usage metrics - in production this would come from GitHub's APIs
        mock_usage = [
            {
                "data_type": "developer_tool",
                "platform": "github",
                "tool_name": "GitHub Copilot",
                "tool_type": "code_completion",
                "supported_languages": [
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "go",
                    "ruby",
                ],
                "integration_type": "ide_plugin",
                "adoption_metrics": {
                    "total_users": 1500000,
                    "daily_active_users": 750000,
                    "code_suggestions_daily": 25000000,
                    "acceptance_rate": 0.35,
                    "languages_coverage": 30,
                },
                "pricing_model": "subscription",
                "pricing_details": {
                    "individual": "$10/month",
                    "business": "$19/user/month",
                    "enterprise": "custom",
                },
                "user_reviews": {"github_marketplace": 4.2, "vs_code_marketplace": 4.1},
                "extracted_at": datetime.utcnow().isoformat(),
            }
        ]

        usage_data.extend(mock_usage)
        return usage_data

    def _extract_feature_updates(self) -> list[dict[str, Any]]:
        """Extract GitHub Copilot feature updates."""
        feature_data = []

        # Mock feature updates
        mock_features = [
            {
                "data_type": "platform_update",
                "platform": "github",
                "update_type": "feature",
                "title": "GitHub Copilot Chat",
                "description": "Conversational AI assistant for development",
                "announcement_date": datetime.utcnow().isoformat(),
                "impact_level": "high",
                "feature_updates": [
                    "chat_interface",
                    "context_awareness",
                    "multi_file_support",
                ],
                "developer_impact": "high",
                "enterprise_features": True,
                "extracted_at": datetime.utcnow().isoformat(),
            }
        ]

        feature_data.extend(mock_features)
        return feature_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform GitHub Copilot data."""
        self.logger.info(f"Transforming {len(data)} GitHub Copilot records")
        transformed_data = []

        for record in data:
            try:
                # Add GitHub Copilot specific intelligence
                transformed_record = {
                    **record,
                    "developer_productivity_impact": self._assess_productivity_impact(
                        record
                    ),
                    "market_position": self._assess_market_position(record),
                    "competitive_advantages": self._identify_competitive_advantages(
                        record
                    ),
                }

                transformed_data.append(transformed_record)
                self.metrics.records_transformed += 1

            except Exception as e:
                self.logger.error(f"Failed to transform GitHub Copilot record: {e}")
                self.metrics.records_failed += 1

        return transformed_data

    def _assess_productivity_impact(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess developer productivity impact."""
        adoption_metrics = record.get("adoption_metrics", {})
        acceptance_rate = adoption_metrics.get("acceptance_rate", 0)

        if acceptance_rate >= 0.4:
            impact_level = "very_high"
        elif acceptance_rate >= 0.3:
            impact_level = "high"
        elif acceptance_rate >= 0.2:
            impact_level = "medium"
        else:
            impact_level = "low"

        return {
            "productivity_impact": impact_level,
            "time_savings_estimate": f"{acceptance_rate * 100:.0f}% code completion",
            "developer_satisfaction": "high",
            "learning_curve": "minimal",
        }

    def _assess_market_position(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assess market position."""
        return {
            "market_position": "leader",
            "first_mover_advantage": True,
            "github_ecosystem_integration": "native",
            "enterprise_adoption": "strong",
        }

    def _identify_competitive_advantages(self, record: dict[str, Any]) -> list[str]:
        """Identify competitive advantages."""
        return [
            "Native GitHub integration",
            "Trained on public code repositories",
            "Multi-language support",
            "IDE ecosystem integration",
            "Microsoft/OpenAI backing",
        ]

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load GitHub Copilot data to storage.

        Args:
            data: List of transformed data dictionaries to load.

        Raises:
            LoadError: If saving data to file fails.
        """
        if not data:
            self.logger.info("No GitHub Copilot data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"github_copilot_data_{timestamp}.json"
        latest_file = self.output_dir / "github_copilot_latest.json"

        try:
            # Save detailed data
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(f"Successfully saved GitHub Copilot data to {output_file}")

            # Save latest data
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(
                f"Successfully updated latest GitHub Copilot data at {latest_file}"
            )

            self.metrics.records_loaded = len(data)

        except (IOError, OSError) as e:
            self.logger.error(
                f"Failed to save GitHub Copilot data to {output_file} or {latest_file}: {e}"
            )
            raise LoadError(
                f"Failed to save GitHub Copilot data: {e}",
                destination=str(output_file),
                destination_type="file",
            ) from e
        except Exception as e:  # Catch any other unexpected errors during load
            self.logger.error(
                f"An unexpected error occurred during saving GitHub Copilot data: {e}",
                exc_info=True,
            )
            raise LoadError(
                f"An unexpected error occurred during saving GitHub Copilot data: {e}",
                destination=str(output_file),
                destination_type="file",
            ) from e
