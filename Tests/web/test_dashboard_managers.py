"""Comprehensive tests for dashboard data managers and utilities.

Tests cover:
- CourseDataManager thread-safety
- CourseDataManager caching
- CourseDataManager error handling
- DateParser utilities
- DateParser edge cases
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.utils.date_parser import (
    DateParser,
    format_date,
    get_date_parser,
    parse_date,
    to_iso_format,
)
from src.web.dashboard.managers.course_data_manager import (
    CourseDataManager,
    CourseDataManagerConfig,
)

# =============================================================================
# CourseDataManager Tests
# =============================================================================


class TestCourseDataManagerConfig:
    """Test CourseDataManagerConfig configuration."""

    def test_config_initialization(self, tmp_path: Path):
        """Test config initialization."""
        config = CourseDataManagerConfig(
            coursera_path=tmp_path / "coursera.json",
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
            enable_cache=True,
            cache_ttl_seconds=1800,
        )

        assert config.enable_cache is True
        assert config.cache_ttl_seconds == 1800

    def test_config_defaults(self, tmp_path: Path):
        """Test config default values."""
        config = CourseDataManagerConfig(
            coursera_path=tmp_path / "coursera.json",
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
        )

        assert config.enable_cache is True  # Default
        assert config.cache_ttl_seconds == 3600  # Default


class TestCourseDataManager:
    """Test CourseDataManager functionality."""

    @pytest.fixture
    def sample_data(self):
        """Create sample course data."""
        return pd.DataFrame(
            [
                {
                    "title": "Course 1",
                    "url": "https://example.com/course1",
                    "description": "Description 1",
                    "institution": "Institution 1",
                    "subject": "Subject 1",
                    "language": "en",
                    "duration": "10 hours",
                    "start_date_str": "2024-01-15",
                    "is_free": True,
                    "certificate_offered": True,
                    "scraped_at_str": "2024-01-10T00:00:00Z",
                },
                {
                    "title": "Course 2",
                    "url": "https://example.com/course2",
                    "description": "Description 2",
                    "institution": "Institution 2",
                    "subject": "Subject 2",
                    "language": "en",
                    "duration": "15 hours",
                    "start_date_str": "2024-02-01",
                    "is_free": False,
                    "certificate_offered": False,
                    "scraped_at_str": "2024-01-10T00:00:00Z",
                },
            ]
        )

    @pytest.fixture
    def manager(self, tmp_path: Path, sample_data: pd.DataFrame):
        """Create CourseDataManager with sample data."""
        # Write sample data files
        coursera_path = tmp_path / "coursera.json"
        udemy_path = tmp_path / "udemy.json"
        pluralsight_path = tmp_path / "pluralsight.json"
        khan_path = tmp_path / "khan.json"

        # Write Coursera data
        coursera_path.write_text(sample_data.to_json(orient="records", indent=2))

        # Create empty files for other sources
        udemy_path.write_text("[]")
        pluralsight_path.write_text("[]")
        khan_path.write_text("[]")

        # Create manager
        config = CourseDataManagerConfig(
            coursera_path=coursera_path,
            udemy_path=udemy_path,
            pluralsight_path=pluralsight_path,
            khan_academy_path=khan_path,
            enable_cache=True,
            cache_ttl_seconds=3600,
        )
        return CourseDataManager(config)

    def test_manager_initialization(self, manager: CourseDataManager):
        """Test manager initialization."""
        assert manager._config is not None
        assert manager._data == {}
        assert manager._loaded == {}
        assert manager._cache_timestamps == {}
        assert isinstance(manager._lock, threading.Lock)

    def test_manager_get_data_coursera(self, manager: CourseDataManager):
        """Test getting Coursera data."""
        df = manager.get_data("coursera")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["title"] == "Course 1"
        assert df.iloc[1]["title"] == "Course 2"

        # Check that columns are normalized
        assert "title" in df.columns
        assert "url" in df.columns
        assert "description" in df.columns

    def test_manager_get_data_caches_results(self, manager: CourseDataManager):
        """Test that data is cached after first load."""
        # First call
        df1 = manager.get_data("coursera")
        loaded_time_1 = manager._cache_timestamps.get("coursera")

        # Second call (should use cache)
        df2 = manager.get_data("coursera")
        loaded_time_2 = manager._cache_timestamps.get("coursera")

        # Should be the same timestamp (cache hit)
        assert loaded_time_1 == loaded_time_2

        # Data should be identical
        pd.testing.assert_frame_equal(df1, df2)

    def test_manager_get_data_invalid_source(self, manager: CourseDataManager):
        """Test getting data from invalid source."""
        with pytest.raises(ValueError, match="Unknown source"):
            manager.get_data("invalid_source")

    def test_manager_get_data_file_not_found(self, tmp_path: Path):
        """Test getting data when file doesn't exist."""
        config = CourseDataManagerConfig(
            coursera_path=tmp_path / "nonexistent.json",
            udemy_path=tmp_path / "nonexistent.json",
            pluralsight_path=tmp_path / "nonexistent.json",
            khan_academy_path=tmp_path / "nonexistent.json",
        )
        manager = CourseDataManager(config)

        df = manager.get_data("coursera")

        # Should return empty DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_manager_get_data_invalid_json(self, tmp_path: Path):
        """Test getting data when file contains invalid JSON."""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not valid json {]")

        config = CourseDataManagerConfig(
            coursera_path=invalid_path,
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
        )
        manager = CourseDataManager(config)

        df = manager.get_data("coursera")

        # Should return empty DataFrame on error
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_manager_invalidate_cache_specific_source(self, manager: CourseDataManager):
        """Test invalidating cache for specific source."""
        # Load data
        df1 = manager.get_data("coursera")
        cache_time_1 = manager._cache_timestamps.get("coursera")

        # Invalidate cache
        manager.invalidate_cache("coursera")

        # Cache should be cleared
        assert manager._cache_timestamps.get("coursera") is None
        assert not manager._loaded.get("coursera", False)

    def test_manager_invalidate_cache_all_sources(self, manager: CourseDataManager):
        """Test invalidating cache for all sources."""
        # Load multiple sources
        manager.get_data("coursera")
        manager.get_data("udemy")

        # Invalidate all
        manager.invalidate_cache()

        # All caches should be cleared
        assert manager._cache_timestamps == {}
        assert manager._loaded == {}

    def test_manager_get_available_sources(self, manager: CourseDataManager):
        """Test getting available sources."""
        # Load data
        manager.get_data("coursera")
        manager.get_data("udemy")

        available = manager.get_available_sources()

        # Coursera should be available (has data)
        # Udemy should not be available (empty data)
        assert "coursera" in available

    def test_manager_get_source_stats(self, manager: CourseDataManager):
        """Test getting source statistics."""
        # Load data
        manager.get_data("coursera")
        manager.get_data("udemy")

        stats = manager.get_source_stats()

        assert stats["coursera"] == 2
        assert stats["udemy"] == 0  # Empty file

    def test_manager_thread_safety(self, tmp_path: Path, sample_data: pd.DataFrame):
        """Test that manager is thread-safe."""
        # Write sample data
        coursera_path = tmp_path / "coursera.json"
        coursera_path.write_text(sample_data.to_json(orient="records"))

        config = CourseDataManagerConfig(
            coursera_path=coursera_path,
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
        )
        manager = CourseDataManager(config)

        # Concurrent access from multiple threads
        results = []
        threads = []

        def load_data(source: str):
            df = manager.get_data(source)
            results.append(len(df))

        # Spawn multiple threads
        for _ in range(5):
            thread = threading.Thread(target=lambda: load_data("coursera"))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All threads should return same result
        assert all(result == 2 for result in results)

    def test_manager_cache_expiration(self, manager: CourseDataManager, monkeypatch):
        """Test cache expiration based on TTL."""
        # Load data
        df1 = manager.get_data("coursera")

        # Mock time to simulate cache expiration
        mock_time = datetime.now(timezone.utc)
        with patch("src.web.dashboard.managers.course_data_manager.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Set cache time to past
            old_time = mock_time.timestamp() - 4000  # More than 3600s TTL
            manager._cache_timestamps["coursera"] = datetime.fromtimestamp(old_time, tz=timezone.utc)

            # Next call should reload from disk
            df2 = manager.get_data("coursera")

            # Data should be the same
            pd.testing.assert_frame_equal(df1, df2)

    def test_manager_parse_date(self, manager: CourseDataManager):
        """Test date parsing in manager."""
        # ISO format
        result = manager._parse_date("2024-01-15T00:00:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        # Common format
        result = manager._parse_date("2024-01-15")
        assert result is not None

        # Invalid format
        result = manager._parse_date("invalid-date")
        assert result is None

    def test_manager_normalize_coursera(self, manager: CourseDataManager):
        """Test Coursera data normalization."""
        # Create raw DataFrame with alternative column names
        raw_data = pd.DataFrame(
            [
                {
                    "name": "Course 1",  # Should be renamed to "title"
                    "link": "https://example.com/1",  # Should be renamed to "url"
                    "partner": "Institution 1",  # Should be renamed to "institution"
                    "category": "Subject 1",  # Should be renamed to "subject"
                    "startDate": "2024-01-15",  # Should be renamed to "start_date_str"
                    "isFree": True,  # Should be renamed to "is_free"
                    "hasCertificate": True,  # Should be renamed to "certificate_offered"
                }
            ]
        )

        normalized = manager._normalize_coursera(raw_data)

        # Check column renaming
        assert "title" in normalized.columns
        assert "url" in normalized.columns
        assert "institution" in normalized.columns
        assert "subject" in normalized.columns
        assert "start_date_str" in normalized.columns
        assert "is_free" in normalized.columns
        assert "certificate_offered" in normalized.columns

        # Check values
        assert normalized.iloc[0]["title"] == "Course 1"


# =============================================================================
# DateParser Tests
# =============================================================================


class TestDateParser:
    """Test DateParser functionality."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = DateParser()
        assert parser.default_timezone == timezone.utc
        assert parser.raise_on_error is False

    def test_parser_custom_timezone(self):
        """Test parser with custom timezone."""
        import datetime as dt

        custom_tz = dt.timezone(dt.timedelta(hours=5))
        parser = DateParser(default_timezone=custom_tz)
        assert parser.default_timezone == custom_tz

    def test_parser_raise_on_error(self):
        """Test parser with raise_on_error=True."""
        parser = DateParser(raise_on_error=True)

        with pytest.raises(ValueError):
            parser.parse("invalid-date")

    def test_parse_iso_format_with_tz(self):
        """Test parsing ISO format with timezone."""
        parser = DateParser()

        result = parser.parse("2024-01-15T10:30:00+00:00")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_iso_format_without_tz(self):
        """Test parsing ISO format without timezone."""
        parser = DateParser()

        result = parser.parse("2024-01-15T10:30:00")

        assert result is not None
        assert result.tzinfo == timezone.utc  # Should default to UTC

    def test_parse_z_suffix(self):
        """Test parsing ISO format with Z suffix."""
        parser = DateParser()

        result = parser.parse("2024-01-15T10:30:00Z")

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_common_formats(self):
        """Test parsing common date formats."""
        parser = DateParser()

        # YYYY-MM-DD
        result = parser.parse("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        # DD/MM/YYYY
        result = parser.parse("15/01/2024")
        assert result is not None
        assert result.day == 15

        # MM/DD/YYYY
        result = parser.parse("01/15/2024")
        assert result is not None
        assert result.month == 1

        # Jan 15, 2024
        result = parser.parse("Jan 15, 2024")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

        # January 15, 2024
        result = parser.parse("January 15, 2024")
        assert result is not None
        assert result.month == 1

    def test_parse_unix_timestamp_seconds(self):
        """Test parsing Unix timestamp in seconds."""
        parser = DateParser()

        # 2024-01-15 00:00:00 UTC = 1705305600 seconds
        result = parser.parse(1705305600)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_unix_timestamp_milliseconds(self):
        """Test parsing Unix timestamp in milliseconds."""
        parser = DateParser()

        # 2024-01-15 00:00:00 UTC = 1705305600000 milliseconds
        result = parser.parse(1705305600000)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_none(self):
        """Test parsing None."""
        parser = DateParser()

        result = parser.parse(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        parser = DateParser()

        result = parser.parse("")
        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        parser = DateParser()

        result = parser.parse("not-a-date")
        assert result is None

    def test_parse_custom_format(self):
        """Test parsing with custom format string."""
        parser = DateParser()

        result = parser.parse("2024.01.15", format_str="%Y.%m.%d")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_batch(self):
        """Test batch date parsing."""
        parser = DateParser()

        dates = ["2024-01-15", "2024-01-16", None, "invalid-date"]
        results = parser.parse_batch(dates)

        assert len(results) == 4
        assert results[0] is not None
        assert results[1] is not None
        assert results[2] is None
        assert results[3] is None

    def test_format(self):
        """Test formatting datetime to string."""
        parser = DateParser()

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = parser.format(dt, format_str="%Y-%m-%d")

        assert result == "2024-01-15"

    def test_format_none(self):
        """Test formatting None returns None."""
        parser = DateParser()

        result = parser.format(None)
        assert result is None

    def test_to_iso_format(self):
        """Test converting to ISO format."""
        parser = DateParser()

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = parser.to_iso_format(dt)

        assert result == "2024-01-15T10:30:00+00:00"

    def test_to_iso_format_none(self):
        """Test converting None to ISO format."""
        parser = DateParser()

        result = parser.to_iso_format(None)
        assert result is None

    def test_is_valid(self):
        """Test date validation."""
        parser = DateParser()

        assert parser.is_valid("2024-01-15") is True
        assert parser.is_valid("Jan 15, 2024") is True
        assert parser.is_valid("invalid-date") is False
        assert parser.is_valid(None) is False

    def test_now(self):
        """Test getting current time."""
        parser = DateParser()

        now = parser.now()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_age_in_days(self):
        """Test calculating age in days."""
        parser = DateParser()

        old_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        age = parser.age_in_days(old_date)

        assert isinstance(age, int)
        assert age > 0  # Should be positive

    def test_age_in_days_none(self):
        """Test calculating age for None."""
        parser = DateParser()

        age = parser.age_in_days(None)
        assert age is None


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Test convenience functions for date parsing."""

    def test_parse_date(self):
        """Test parse_date convenience function."""
        result = parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_format_date(self):
        """Test format_date convenience function."""
        dt = datetime(2024, 1, 15, tzinfo=timezone.utc)
        result = format_date(dt)
        assert result == "2024-01-15T00:00:00"

    def test_to_iso_format(self):
        """Test to_iso_format convenience function."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = to_iso_format(dt)
        assert result == "2024-01-15T10:30:00+00:00"

    def test_get_date_parser_singleton(self):
        """Test get_date_parser returns singleton."""
        parser1 = get_date_parser()
        parser2 = get_date_parser()

        # Should return same instance
        assert parser1 is parser2


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_leap_year_date(self):
        """Test parsing leap year date."""
        parser = DateParser()

        result = parser.parse("2024-02-29")  # Leap year
        assert result is not None
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

    def test_parse_end_of_month(self):
        """Test parsing end of month dates."""
        parser = DateParser()

        result = parser.parse("2024-01-31")  # Jan has 31 days
        assert result is not None
        assert result.day == 31

    def test_parse_negative_timestamp(self):
        """Test parsing negative timestamp (before Unix epoch)."""
        parser = DateParser()

        result = parser.parse(-86400)  # One day before epoch
        assert result is not None
        assert result.year == 1969
        assert result.month == 12
        assert result.day == 31

    def test_manager_empty_dataframe(self, tmp_path: Path):
        """Test manager handling empty DataFrame."""
        empty_path = tmp_path / "empty.json"
        empty_path.write_text("[]")

        config = CourseDataManagerConfig(
            coursera_path=empty_path,
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
        )
        manager = CourseDataManager(config)

        df = manager.get_data("coursera")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_manager_cache_disabled(self, tmp_path: Path, sample_data: pd.DataFrame):
        """Test manager with caching disabled."""
        coursera_path = tmp_path / "coursera.json"
        coursera_path.write_text(sample_data.to_json(orient="records"))

        config = CourseDataManagerConfig(
            coursera_path=coursera_path,
            udemy_path=tmp_path / "udemy.json",
            pluralsight_path=tmp_path / "pluralsight.json",
            khan_academy_path=tmp_path / "khan.json",
            enable_cache=False,  # Disable caching
        )
        manager = CourseDataManager(config)

        # First call
        df1 = manager.get_data("coursera")

        # Should not be cached (cache disabled)
        assert manager._cache_timestamps.get("coursera") is None

        # Second call should reload from disk
        df2 = manager.get_data("coursera")

        # Data should be identical
        pd.testing.assert_frame_equal(df1, df2)
