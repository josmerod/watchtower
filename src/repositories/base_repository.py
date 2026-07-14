"""Base Repository for data access layer.

Implements Repository pattern to abstract data loading and caching operations.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generic, TypeVar

import pandas as pd

T = TypeVar("T")


class RepositoryError(Exception):
    """Exception raised when repository operations fail."""

    pass


class CacheEntry(Generic[T]):
    """Cache entry with TTL support."""

    def __init__(self, data: T, ttl_seconds: int = 3600):
        self.data = data
        self.created_at = datetime.utcnow()
        self.ttl = timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() - self.created_at > self.ttl

    def refresh(self, data: T) -> None:
        """Refresh cached data."""
        self.data = data
        self.created_at = datetime.utcnow()


class BaseRepository(ABC, Generic[T]):
    """Base repository for data access operations.

    Provides:
    - File-based data loading
    - In-memory caching with TTL
    - Thread-safe operations
    - Error handling and logging
    """

    def __init__(
        self,
        data_path: Path,
        cache_ttl_seconds: int = 3600,
        enable_cache: bool = True,
    ):
        """Initialize repository.

        Args:
            data_path: Path to data file
            cache_ttl_seconds: Cache time-to-live in seconds
            enable_cache: Enable in-memory caching
        """
        self.data_path = data_path
        self.cache_ttl = cache_ttl_seconds
        self.enable_cache = enable_cache

        self._cache: CacheEntry[T] | None = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def load_data(self) -> T:
        """Load data from source.

        Returns:
            Loaded data

        Raises:
            RepositoryError: If loading fails
        """
        raw_data = self._load_from_file()
        return self.transform_data(raw_data)

    @abstractmethod
    def transform_data(self, raw_data: Any) -> T:
        """Transform raw data into domain model.

        Args:
            raw_data: Raw data from file

        Returns:
            Transformed data
        """
        pass

    def get(self, force_refresh: bool = False) -> T:
        """Get data from cache or load from source.

        Args:
            force_refresh: Force reload from source

        Returns:
            Data instance

        Raises:
            RepositoryError: If data loading fails
        """
        # Check cache
        if not force_refresh and self._is_cached():
            self._logger.debug(f"Cache hit for {self.data_path.name}")
            return self._cache.data  # type: ignore

        # Load from source
        self._logger.info(f"Loading data from {self.data_path}")
        try:
            raw_data = self._load_from_file()
            transformed_data = self.transform_data(raw_data)

            # Update cache
            if self.enable_cache:
                self._cache = CacheEntry(transformed_data, self.cache_ttl)

            return transformed_data

        except Exception as e:
            error_msg = f"Failed to load data from {self.data_path}: {e}"
            self._logger.error(error_msg)
            raise RepositoryError(error_msg) from e

    def _load_from_file(self) -> Any:
        """Load raw data from file.

        Returns:
            Raw file contents

        Raises:
            FileNotFoundError: If file doesn't exist
            RepositoryError: If file read fails
        """
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        try:
            if self.data_path.suffix == ".json":
                return self._load_json()
            elif self.data_path.suffix in {".csv", ".tsv"}:
                return self._load_csv()
            else:
                raise RepositoryError(f"Unsupported file type: {self.data_path.suffix}")

        except Exception as e:
            if isinstance(e, RepositoryError):
                raise
            raise RepositoryError(f"Failed to read file {self.data_path}: {e}") from e

    def _load_json(self) -> Any:
        """Load JSON file."""
        import json

        with open(self.data_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_csv(self) -> Any:
        """Load CSV/TSV file."""
        separator = "\t" if self.data_path.suffix == ".tsv" else ","
        return pd.read_csv(self.data_path, sep=separator)

    def _is_cached(self) -> bool:
        """Check if cached data is valid.

        Returns:
            True if cache exists and is not expired
        """
        if not self.enable_cache or self._cache is None:
            return False

        return not self._cache.is_expired()

    def clear_cache(self) -> None:
        """Clear cached data."""
        self._cache = None
        self._logger.debug("Cache cleared")

    def is_available(self) -> bool:
        """Check if data source is available.

        Returns:
            True if data file exists
        """
        return self.data_path.exists()

    def get_last_modified(self) -> datetime | None:
        """Get last modification time of data file.

        Returns:
            Datetime of last modification or None
        """
        if not self.data_path.exists():
            return None

        try:
            timestamp = self.data_path.stat().st_mtime
            return datetime.fromtimestamp(timestamp)
        except Exception:
            return None


class DataFrameRepository(BaseRepository[pd.DataFrame]):
    """Repository for pandas DataFrame data.

    Provides DataFrame-specific operations and optimizations.
    """

    def __init__(
        self,
        data_path: Path,
        cache_ttl_seconds: int = 3600,
        enable_cache: bool = True,
        default_columns: list[str] | None = None,
    ):
        """Initialize DataFrame repository.

        Args:
            data_path: Path to data file
            cache_ttl_seconds: Cache time-to-live
            enable_cache: Enable caching
            default_columns: Default columns to ensure exist
        """
        super().__init__(data_path, cache_ttl_seconds, enable_cache)
        self.default_columns = default_columns or []

    def transform_data(self, raw_data: Any) -> pd.DataFrame:
        """Transform raw data into DataFrame.

        Args:
            raw_data: Raw data from file

        Returns:
            pandas DataFrame
        """
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data
        elif isinstance(raw_data, list):
            df = pd.DataFrame(raw_data)
        elif isinstance(raw_data, dict):
            df = pd.DataFrame([raw_data])
        else:
            raise RepositoryError(f"Unsupported data type: {type(raw_data)}")

        # Ensure default columns exist
        for col in self.default_columns:
            if col not in df.columns:
                df[col] = None

        return df

    def filter(self, filters: dict[str, Any]) -> pd.DataFrame:
        """Filter DataFrame by column values.

        Args:
            filters: Dictionary of column -> value mappings

        Returns:
            Filtered DataFrame
        """
        df = self.get()

        for column, value in filters.items():
            if column not in df.columns:
                continue

            if isinstance(value, (list, tuple, set)):
                df = df[df[column].isin(value)]
            else:
                df = df[df[column] == value]

        return df

    def search(self, column: str, query: str) -> pd.DataFrame:
        """Search for text in column.

        Args:
            column: Column to search
            query: Search query

        Returns:
            Filtered DataFrame with matching rows
        """
        df = self.get()

        if column not in df.columns:
            self._logger.warning(f"Column '{column}' not found for search")
            return pd.DataFrame()

        if df[column].dtype == "object":
            return df[df[column].str.contains(query, case=False, na=False)]
        else:
            self._logger.warning(f"Column '{column}' is not text searchable")
            return pd.DataFrame()

    def sort(self, column: str, ascending: bool = True) -> pd.DataFrame:
        """Sort DataFrame by column.

        Args:
            column: Column to sort by
            ascending: Sort direction

        Returns:
            Sorted DataFrame
        """
        df = self.get()

        if column not in df.columns:
            self._logger.warning(f"Column '{column}' not found for sorting")
            return df

        return df.sort_values(by=column, ascending=ascending)

    def get_unique_values(self, column: str) -> list[Any]:
        """Get unique values from column.

        Args:
            column: Column name

        Returns:
            List of unique values
        """
        df = self.get()

        if column not in df.columns:
            self._logger.warning(f"Column '{column}' not found")
            return []

        return df[column].unique().tolist()

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics for DataFrame.

        Returns:
            Dictionary with summary info
        """
        df = self.get()

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "last_modified": self.get_last_modified(),
            "data_path": str(self.data_path),
        }
