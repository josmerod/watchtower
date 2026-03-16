"""Course data manager for dashboard components.

Thread-safe data loading and caching manager for course data from multiple sources.
Replaces global state anti-pattern with encapsulated, testable data management.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from src.utils.logging import get_logger


@dataclass
class CourseDataManagerConfig:
    """Configuration for course data manager."""

    coursera_path: Path
    udemy_path: Path
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour default


class CourseDataManager:
    """Thread-safe manager for course data loading and caching.

    Replaces global state anti-pattern with encapsulated data management.
    Provides thread-safe data loading with configurable caching.

    Example:
        >>> config = CourseDataManagerConfig(...)
        >>> manager = CourseDataManager(config)
        >>> df = manager.get_data("coursera")
        >>> print(len(df))
        150
    """

    def __init__(self, config: CourseDataManagerConfig) -> None:
        """Initialize the course data manager.

        Args:
            config: Configuration for data paths and caching behavior
        """
        self._config = config
        self._data: Dict[str, pd.DataFrame] = {}
        self._loaded: Dict[str, bool] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(self.__class__.__name__)

    def get_data(self, source: str) -> pd.DataFrame:
        """Get data for a specific source, loading if necessary.

        Thread-safe data retrieval with automatic loading and caching.

        Args:
            source: Data source identifier (e.g., "coursera", "udemy")

        Returns:
            DataFrame containing the source data. Returns empty DataFrame if
            source not found or loading fails.

        Raises:
            ValueError: If source identifier is unknown

        Example:
            >>> manager = CourseDataManager(config)
            >>> coursera_df = manager.get_data("coursera")
            >>> udemy_df = manager.get_data("udemy")
        """
        with self._lock:
            if source not in ["coursera", "udemy"]:
                raise ValueError(
                    f"Unknown source: {source}. "
                    f"Available: coursera, udemy"
                )

            if self._should_reload(source):
                self._load_source(source)
                self._cache_timestamps[source] = datetime.now(timezone.utc)

            return self._data.get(source, pd.DataFrame()).copy()

    def _should_reload(self, source: str) -> bool:
        """Check if data needs to be reloaded based on cache state.

        Args:
            source: Data source identifier

        Returns:
            True if data should be reloaded, False if cached data is valid
        """
        # Never loaded
        if not self._loaded.get(source, False):
            return True

        # Caching disabled
        if not self._config.enable_cache:
            return True

        # No cache timestamp
        cached_time = self._cache_timestamps.get(source)
        if not cached_time:
            return True

        # Cache expired
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        return age > self._config.cache_ttl_seconds

    def _load_source(self, source: str) -> None:
        """Load data from source with error handling.

        Args:
            source: Data source identifier
        """
        loaders = {
            "coursera": self._load_coursera,
            "udemy": self._load_udemy,
        }

        loader = loaders.get(source)
        if not loader:
            self.logger.error(f"No loader found for source: {source}")
            self._data[source] = pd.DataFrame()
            self._loaded[source] = True
            return

        try:
            loader()
            self._loaded[source] = True
            count = len(self._data.get(source, pd.DataFrame()))
            self.logger.info(f"Loaded {count} courses from {source}")
        except Exception as e:
            self.logger.error(f"Failed to load {source}: {e}", exc_info=True)
            self._data[source] = pd.DataFrame()
            self._loaded[source] = True

    def _load_coursera(self) -> None:
        """Load and normalize Coursera data.

        Reads Coursera courses from JSON file and normalizes column names
        and date formats for consistent handling.
        """
        path = self._config.coursera_path

        if not path.exists():
            self.logger.warning(f"Coursera file not found: {path}")
            self._data["coursera"] = pd.DataFrame()
            return

        try:
            df = pd.read_json(path)
        except Exception as e:
            self.logger.error(f"Failed to read Coursera data: {e}")
            self._data["coursera"] = pd.DataFrame()
            return

        if df.empty:
            self.logger.info(f"Coursera data file is empty: {path}")
            self._data["coursera"] = pd.DataFrame()
            return

        # Normalize column names
        df = self._normalize_coursera(df)

        self._data["coursera"] = df

    def _normalize_coursera(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Coursera DataFrame columns and formats.

        Args:
            df: Raw Coursera DataFrame

        Returns:
            Normalized DataFrame with standard columns
        """
        # Rename common alternative column names
        rename_map = {
            "name": "title",
            "link": "url",
            "partner": "institution",
            "category": "subject",
            "startDate": "start_date_str",
            "isFree": "is_free",
            "hasCertificate": "certificate_offered",
            "retrieved_at": "scraped_at_str",
            "last_updated": "scraped_at_str",
        }
        df = df.rename(columns=rename_map)

        # Ensure required columns exist
        required_cols = [
            "title",
            "url",
            "description",
            "institution",
            "subject",
            "language",
            "duration",
            "start_date_str",
            "is_free",
            "certificate_offered",
            "scraped_at_str",
        ]
        for col in required_cols:
            if col not in df.columns:
                df[col] = None

        # Parse date columns
        df["start_date"] = df["start_date_str"].apply(self._parse_date)
        df["scraped_at"] = df["scraped_at_str"].apply(self._parse_date)

        # Sort by scraped date (newest first)
        if "scraped_at" in df.columns:
            df = df.sort_values(by="scraped_at", ascending=False, na_position="last")

        return df

    def _load_udemy(self) -> None:
        """Load and normalize Udemy data."""
        path = self._config.udemy_path

        if not path.exists():
            self.logger.warning(f"Udemy file not found: {path}")
            self._data["udemy"] = pd.DataFrame()
            return

        try:
            df = pd.read_json(path)
        except Exception as e:
            self.logger.error(f"Failed to read Udemy data: {e}")
            self._data["udemy"] = pd.DataFrame()
            return

        if df.empty:
            self.logger.info(f"Udemy data file is empty: {path}")
            self._data["udemy"] = pd.DataFrame()
            return

        # Normalize Udemy-specific columns
        df = self._normalize_udemy(df)

        self._data["udemy"] = df

    def _normalize_udemy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Udemy DataFrame columns and formats.

        Args:
            df: Raw Udemy DataFrame

        Returns:
            Normalized DataFrame with standard columns
        """
        # Udemy-specific normalization
        rename_map = {
            "course_title": "title",
            "course_url": "url",
            "course_description": "description",
        }
        df = df.rename(columns=rename_map)

        # Ensure required columns
        required_cols = ["title", "url", "description"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = None

        return df

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parse date string with multiple format support.

        Attempts to parse dates in ISO format, common date formats,
        and Unix timestamps. Returns UTC datetime or None if parsing fails.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime in UTC or None if parsing fails

        Example:
            >>> CourseDataManager._parse_date("2024-01-15")
            datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
            >>> CourseDataManager._parse_date("Jan 15, 2024")
            datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
            >>> CourseDataManager._parse_date(None)
            None
        """
        if pd.isna(date_str) or not date_str:
            return None

        # Try ISO format first (most common)
        try:
            dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except (ValueError, AttributeError):
            pass

        # Try common formats
        common_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        # Try Unix timestamp (seconds or milliseconds)
        try:
            ts = float(date_str)
            if ts > 10000000000:  # Milliseconds
                ts /= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError):
            pass

        self.logger.warning(f"Could not parse date: {date_str}")
        return None

    def invalidate_cache(self, source: str | None = None) -> None:
        """Invalidate cache for specific source or all sources.

        Args:
            source: Specific source to invalidate, or None for all sources

        Example:
            >>> manager.invalidate_cache("coursera")  # Invalidate specific
            >>> manager.invalidate_cache()  # Invalidate all
        """
        with self._lock:
            if source:
                self._loaded[source] = False
                self._cache_timestamps.pop(source, None)
                self.logger.info(f"Invalidated cache for {source}")
            else:
                self._loaded.clear()
                self._cache_timestamps.clear()
                self.logger.info("Invalidated all caches")

    def get_available_sources(self) -> list[str]:
        """Get list of available data sources.

        Returns:
            List of source identifiers that have successfully loaded data

        Example:
            >>> sources = manager.get_available_sources()
            >>> print(sources)
            ['coursera', 'udemy']
        """
        with self._lock:
            return [
                source
                for source, loaded in self._loaded.items()
                if loaded and not self._data.get(source, pd.DataFrame()).empty
            ]

    def get_source_stats(self) -> Dict[str, int]:
        """Get statistics for each data source.

        Returns:
            Dictionary mapping source names to record counts

        Example:
            >>> stats = manager.get_source_stats()
            >>> print(stats)
            {'coursera': 150, 'udemy': 75}
        """
        with self._lock:
            return {
                source: len(df)
                for source, df in self._data.items()
                if source in self._loaded and self._loaded[source]
            }
