"""Package Registry ETL using BaseETL pattern.

Part of Phase 1 ETL implementation for package registry analytics.
Supports: npm, PyPI, crates.io, RubyGems, NuGet, Go Packages.

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
from src.models.package_registry import (
    PackageMetricsModel,
    PackageModel,
    PackageRegistry,
    PackageTrendDirection,
)
from src.utils.logging import get_logger


class PackageRegistryETL(BaseETL[dict[str, Any], PackageModel]):
    """ETL for Package Registries.

    Supports multiple package registries:
    - npm: https://www.npmjs.com/ (JavaScript/Node.js)
    - PyPI: https://pypi.org/ (Python)
    - crates.io: https://crates.io/ (Rust)
    - RubyGems: https://rubygems.org/ (Ruby)
    - NuGet: https://www.nuget.org/ (.NET)
    - Go: https://pkg.go.dev/ (Go)

    Each registry provides different metrics about package popularity,
    downloads, and quality.
    """

    def __init__(
        self,
        registries: list[str] | None = None,
        keywords: list[str] | None = None,
        max_packages_per_registry: int = 100,
        **kwargs,
    ):
        """Initialize Package Registry ETL.

        Args:
            registries: Registries to fetch (defaults to all)
            keywords: Keywords to search for
            max_packages_per_registry: Max packages per registry
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="package_registry",
            description="Package Registry ETL for multiple platforms",
            **kwargs,
        )

        # Supported registries
        self.registries = registries or ["npm", "pypi", "crates_io"]

        # Keywords to search
        self.keywords = keywords or [
            "react",
            "vue",
            "django",
            "flask",
            "tensorflow",
            "requests",
            "express",
            "lodash",
        ]

        self.max_packages_per_registry = max_packages_per_registry

        # Registry URLs
        self.registry_urls = {
            "npm": "https://registry.npmjs.org",
            "pypi": "https://pypi.org/pypi",
            "crates_io": "https://crates.io/api/v1",
            "rubygems": "https://rubygems.org/api/v1",
            "nuget": "https://api.nuget.org/v3",
            "go": "https://pkg.go.dev",
        }

        # Metrics
        self.api_metrics = PackageMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract packages from registries.

        Returns:
            List of raw package dictionaries.
        """
        self.logger.info(f"Starting extraction for {len(self.registries)} registries")

        all_packages = []

        # Extract from each registry
        for registry in self.registries:
            try:
                packages = self._fetch_registry(registry)
                all_packages.extend(packages)
                self.logger.info(f"Fetched {len(packages)} packages from {registry}")
            except Exception as e:
                self.logger.error(f"Failed to fetch from '{registry}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Registry failed: {registry}",
                    error_type=type(e).__name__,
                    context={"registry": registry},
                )

        self.logger.info(f"Extraction complete: {len(all_packages)} total packages")
        self.api_metrics.total_packages_discovered = len(all_packages)

        return all_packages

    def _fetch_registry(self, registry: str) -> list[dict[str, Any]]:
        """Fetch packages from a specific registry.

        Args:
            registry: Registry name

        Returns:
            List of package dictionaries.
        """
        if registry == "npm":
            return self._fetch_npm()
        elif registry == "pypi":
            return self._fetch_pypi()
        elif registry == "crates_io":
            return self._fetch_crates_io()
        else:
            self.logger.warning(f"Unknown registry: {registry}")
            return []

    def _fetch_npm(self) -> list[dict[str, Any]]:
        """Fetch packages from npm registry.

        Returns:
            List of package dictionaries.
        """
        # Note: Implement actual API call here
        # This is a placeholder that returns sample data
        return [
            {
                "package_id": "npm_react",
                "name": "react",
                "registry": "npm",
                "url": "https://www.npmjs.com/package/react",
                "description": "React is a JavaScript library for building user interfaces",
                "version": "18.2.0",
                "downloads_total": 20000000000,
                "downloads_weekly": 15000000,
                "author_name": "Facebook",
                "keywords": ["react", "ui", "framework"],
                "language": "JavaScript",
                "license": "MIT",
                "repository_url": "https://github.com/facebook/react",
            },
            {
                "package_id": "npm_vue",
                "name": "vue",
                "registry": "npm",
                "url": "https://www.npmjs.com/package/vue",
                "description": "Vue.js is a progressive JavaScript framework",
                "version": "3.3.0",
                "downloads_total": 10000000000,
                "downloads_weekly": 8000000,
                "author_name": "Evan You",
                "keywords": ["vue", "ui", "framework"],
                "language": "JavaScript",
                "license": "MIT",
                "repository_url": "https://github.com/vuejs/core",
            },
        ]

    def _fetch_pypi(self) -> list[dict[str, Any]]:
        """Fetch packages from PyPI registry.

        Returns:
            List of package dictionaries.
        """
        # Note: Implement actual API call here
        return [
            {
                "package_id": "pypi_requests",
                "name": "requests",
                "registry": "pypi",
                "url": "https://pypi.org/project/requests/",
                "description": "Python HTTP for Humans",
                "version": "2.31.0",
                "downloads_total": 5000000000,
                "downloads_weekly": 50000000,
                "author_name": "Kenneth Reitz",
                "keywords": ["http", "requests", "web"],
                "language": "Python",
                "license": "Apache 2.0",
                "repository_url": "https://github.com/psf/requests",
            },
        ]

    def _fetch_crates_io(self) -> list[dict[str, Any]]:
        """Fetch packages from crates.io registry.

        Returns:
            List of package dictionaries.
        """
        # Note: Implement actual API call here
        return [
            {
                "package_id": "crates_serde",
                "name": "serde",
                "registry": "crates_io",
                "url": "https://crates.io/crates/serde",
                "description": "Serialization framework for Rust",
                "version": "1.0.0",
                "downloads_total": 500000000,
                "downloads_weekly": 5000000,
                "keywords": ["serialization", "json", "rust"],
                "language": "Rust",
                "license": "MIT OR Apache-2.0",
                "repository_url": "https://github.com/serde-rs/serde",
            },
        ]

    def transform(self, raw_data: list[dict[str, Any]]) -> list[PackageModel]:
        """Transform raw package data to models.

        Args:
            raw_data: List of raw package dictionaries

        Returns:
            List of PackageModel instances.
        """
        transformed = []

        for raw_package in raw_data:
            try:
                model = self._transform_package(raw_package)
                if model:
                    transformed.append(model)
                    self.api_metrics.new_packages_this_run += 1
            except Exception as e:
                self.logger.warning(f"Failed to transform package: {e}")
                self.metrics.records_failed += 1

        # Update metrics
        for package in transformed:
            reg = package.registry.value if isinstance(package.registry, PackageRegistry) else str(package.registry)
            self.api_metrics.registry_distribution[reg] = self.api_metrics.registry_distribution.get(reg, 0) + 1

            if package.language:
                self.api_metrics.language_distribution[package.language] = self.api_metrics.language_distribution.get(package.language, 0) + 1

            self.api_metrics.total_downloads += package.downloads_total
            if package.downloads_weekly and package.downloads_weekly > 1000:
                self.api_metrics.popular_packages += 1
            if package.is_trending:
                self.api_metrics.trending_packages += 1
            if package.dependents_count:
                self.api_metrics.total_dependents += package.dependents_count

        if transformed:
            weekly_downloads = [p.downloads_weekly for p in transformed if p.downloads_weekly]
            if weekly_downloads:
                self.api_metrics.avg_downloads_weekly = sum(weekly_downloads) / len(weekly_downloads)

            dependencies = [p.dependencies_count for p in transformed]
            if dependencies:
                self.api_metrics.avg_dependencies = sum(dependencies) / len(dependencies)

        self.logger.info(f"Transformed {len(transformed)} packages")
        return transformed

    def _transform_package(self, raw: dict[str, Any]) -> PackageModel | None:
        """Transform single package.

        Args:
            raw: Raw package dictionary

        Returns:
            PackageModel or None if transformation fails.
        """
        package_id = raw.get("package_id")
        name = raw.get("name")

        if not package_id or not name:
            return None

        # Parse registry
        registry_str = raw.get("registry", "npm")
        try:
            registry = PackageRegistry(registry_str)
        except ValueError:
            registry = PackageRegistry.NPM

        # Parse trend direction
        trend_str = raw.get("trend_direction", "unknown")
        try:
            trend_direction = PackageTrendDirection(trend_str.lower())
        except ValueError:
            trend_direction = PackageTrendDirection.UNKNOWN

        return PackageModel(
            package_id=package_id,
            name=name,
            registry=registry,
            url=raw.get("url"),
            description=raw.get("description"),
            readme=raw.get("readme"),
            version=raw.get("version"),
            versions_count=raw.get("versions_count", 0),
            author_name=raw.get("author_name"),
            author_email=raw.get("author_email"),
            maintainers=raw.get("maintainers", []),
            publisher_name=raw.get("publisher_name"),
            publisher_username=raw.get("publisher_username"),
            downloads_total=raw.get("downloads_total", 0),
            downloads_weekly=raw.get("downloads_weekly"),
            downloads_monthly=raw.get("downloads_monthly"),
            stars_count=raw.get("stars_count", 0),
            forks_count=raw.get("forks_count", 0),
            popularity_score=raw.get("popularity_score"),
            quality_score=raw.get("quality_score"),
            trend_direction=trend_direction,
            dependencies_count=raw.get("dependencies_count", 0),
            dev_dependencies_count=raw.get("dev_dependencies_count", 0),
            dependents_count=raw.get("dependents_count"),
            keywords=raw.get("keywords", []),
            topics=raw.get("topics", []),
            language=raw.get("language"),
            license=raw.get("license"),
            repository_url=raw.get("repository_url"),
            repository_stars=raw.get("repository_stars"),
            repository_forks=raw.get("repository_forks"),
            homepage_url=raw.get("homepage_url"),
            created_at=self._parse_date(raw.get("created_at")),
            updated_at=self._parse_date(raw.get("updated_at")),
            published_at=self._parse_date(raw.get("published_at")),
            size_bytes=raw.get("size_bytes"),
            install_size_bytes=raw.get("install_size_bytes"),
            original_id=package_id,
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

    def load(self, data: list[PackageModel]) -> None:
        """Load packages to JSON storage.

        Args:
            data: List of PackageModel instances.
        """
        # Convert to dicts
        packages_data = [pkg.model_dump(mode="json") for pkg in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"packages_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(packages_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "packages_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(packages_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "packages_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} packages to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for Package Registry ETL."""
    logger = get_logger("PackageRegistryETL")
    logger.info("Starting Package Registry ETL")

    try:
        etl = PackageRegistryETL()
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
