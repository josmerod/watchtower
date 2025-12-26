"""Repository Manager for aggregated data access.

Manages multiple repositories and provides unified data access interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.repositories.base_repository import BaseRepository, DataFrameRepository


class RepositoryManager:
    """Manager for multiple repositories.

    Provides:
    - Centralized repository management
    - Aggregated data access
    - Batch operations
    - Cache management
    """

    def __init__(self, name: str):
        """Initialize repository manager.

        Args:
            name: Manager name for logging
        """
        self.name = name
        self._repositories: dict[str, BaseRepository] = {}
        self._logger = logging.getLogger(f"RepositoryManager.{name}")

    def register(self, key: str, repository: BaseRepository) -> None:
        """Register a repository.

        Args:
            key: Repository identifier
            repository: Repository instance
        """
        self._repositories[key] = repository
        self._logger.debug(f"Registered repository: {key}")

    def unregister(self, key: str) -> None:
        """Unregister a repository.

        Args:
            key: Repository identifier
        """
        self._repositories.pop(key, None)
        self._logger.debug(f"Unregistered repository: {key}")

    def get(self, key: str, force_refresh: bool = False) -> Any:
        """Get data from specific repository.

        Args:
            key: Repository identifier
            force_refresh: Force reload from source

        Returns:
            Data from repository

        Raises:
            KeyError: If repository not found
        """
        if key not in self._repositories:
            raise KeyError(f"Repository '{key}' not found")

        return self._repositories[key].get(force_refresh)

    def get_all(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get data from all repositories.

        Args:
            force_refresh: Force reload from all sources

        Returns:
            Dictionary mapping repository keys to data
        """
        return {key: repo.get(force_refresh) for key, repo in self._repositories.items()}

    def refresh_all(self) -> None:
        """Refresh all repositories."""
        for key, repo in self._repositories.items():
            try:
                repo.get(force_refresh=True)
                self._logger.info(f"Refreshed repository: {key}")
            except Exception as e:
                self._logger.error(f"Failed to refresh {key}: {e}")

    def clear_cache_all(self) -> None:
        """Clear cache for all repositories."""
        for key, repo in self._repositories.items():
            try:
                repo.clear_cache()
                self._logger.debug(f"Cleared cache for: {key}")
            except Exception as e:
                self._logger.error(f"Failed to clear cache for {key}: {e}")

    def get_available_repositories(self) -> list[str]:
        """Get list of repository identifiers.

        Returns:
            List of registered repository keys
        """
        return list(self._repositories.keys())

    def is_available(self, key: str) -> bool:
        """Check if repository is available.

        Args:
            key: Repository identifier

        Returns:
            True if repository exists and data file exists
        """
        if key not in self._repositories:
            return False

        return self._repositories[key].is_available()

    def get_summary_all(self) -> dict[str, dict[str, Any]]:
        """Get summary for all repositories.

        Returns:
            Dictionary mapping repository keys to summaries
        """
        summaries = {}

        for key, repo in self._repositories.items():
            try:
                if isinstance(repo, DataFrameRepository):
                    data = repo.get()
                    summaries[key] = {
                        "type": "DataFrame",
                        "rows": len(data),
                        "columns": len(data.columns),
                        "cached": repo._is_cached(),
                        "available": repo.is_available(),
                    }
                else:
                    summaries[key] = {
                        "type": "Generic",
                        "cached": repo._is_cached(),
                        "available": repo.is_available(),
                    }
            except Exception as e:
                summaries[key] = {"error": str(e)}

        return summaries


class AggregatedRepository(DataFrameRepository):
    """Repository that aggregates data from multiple sources.

    Combines data from multiple repositories into a single DataFrame.
    """

    def __init__(
        self,
        name: str,
        repositories: dict[str, DataFrameRepository],
        merge_column: str | None = None,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize aggregated repository.

        Args:
            name: Repository name
            repositories: Dictionary of name -> repository mappings
            merge_column: Column to merge on (if applicable)
            cache_ttl_seconds: Cache TTL
        """
        # Dummy path (not used for aggregated data)
        super().__init__(Path("aggregated"), cache_ttl_seconds)

        self.name = name
        self.repositories = repositories
        self.merge_column = merge_column
        self._logger = logging.getLogger(f"AggregatedRepository.{name}")

    def load_data(self) -> pd.DataFrame:
        """Load and aggregate data from all repositories.

        Returns:
            Aggregated DataFrame
        """
        dataframes = []

        for name, repo in self.repositories.items():
            try:
                df = repo.get()
                if not df.empty:
                    # Add source column
                    df = df.copy()
                    df["source"] = name
                    dataframes.append(df)
                    self._logger.info(f"Loaded {len(df)} rows from {name}")
            except Exception as e:
                self._logger.warning(f"Failed to load from {name}: {e}")

        if not dataframes:
            self._logger.warning("No data loaded from any repository")
            return pd.DataFrame()

        # Concatenate all dataframes
        result = pd.concat(dataframes, ignore_index=True)
        self._logger.info(f"Aggregated {len(result)} total rows")

        return result

    def transform_data(self, raw_data: Any) -> pd.DataFrame:
        """Transform raw data (already a DataFrame from load_data).

        Args:
            raw_data: Raw data (should be DataFrame)

        Returns:
            DataFrame
        """
        if isinstance(raw_data, pd.DataFrame):
            return raw_data

        return super().transform_data(raw_data)


def create_courses_repository_manager() -> RepositoryManager:
    """Create repository manager for course data.

    Returns:
        Configured RepositoryManager for courses
    """
    from src.web.dashboard.utils import get_data_path

    manager = RepositoryManager("courses")

    # Register course repositories
    manager.register(
        "coursera",
        DataFrameRepository(
            get_data_path("classcentral", "coursera_courses.json"),
            default_columns=["title", "url", "rating"],
        ),
    )
    manager.register(
        "udemy",
        DataFrameRepository(
            get_data_path("udemy", "udemy_courses.json"),
            default_columns=["title", "url", "rating"],
        ),
    )
    manager.register(
        "pluralsight",
        DataFrameRepository(
            get_data_path("pluralsight_courses", "pluralsight_courses.json"),
            default_columns=["title", "url", "rating"],
        ),
    )
    manager.register(
        "khan",
        DataFrameRepository(
            get_data_path("courses", "khan_academy_latest.json"),
            default_columns=["title", "url"],
        ),
    )

    return manager


def create_news_repository_manager() -> RepositoryManager:
    """Create repository manager for news data.

    Returns:
        Configured RepositoryManager for news
    """
    from src.web.dashboard.utils import get_data_path

    manager = RepositoryManager("news")

    # Register news repositories
    manager.register(
        "hackernews",
        DataFrameRepository(
            get_data_path("hackernews", "hackernews_stories.json"),
            default_columns=["title", "url", "score"],
        ),
    )
    manager.register(
        "reddit",
        DataFrameRepository(
            get_data_path("reddit", "reddit_posts.json"),
            default_columns=["title", "url", "score"],
        ),
    )
    manager.register(
        "medium",
        DataFrameRepository(
            get_data_path("medium", "medium_posts.json"),
            default_columns=["title", "url"],
        ),
    )

    return manager


def create_games_repository_manager() -> RepositoryManager:
    """Create repository manager for games data.

    Returns:
        Configured RepositoryManager for games
    """
    from src.web.dashboard.utils import get_data_path

    manager = RepositoryManager("games")

    # Register games repositories
    manager.register(
        "free_games",
        DataFrameRepository(
            get_data_path("games", "free_games_latest.json"),
            default_columns=["title", "url", "platform"],
        ),
    )
    manager.register(
        "new_releases",
        DataFrameRepository(
            get_data_path("games", "new_releases_latest.json"),
            default_columns=["title", "url", "release_date"],
        ),
    )

    return manager
