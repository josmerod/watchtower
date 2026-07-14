"""Unified date parsing utilities.

Provides centralized date parsing logic with support for multiple formats,
timezones, and error handling. Eliminates code duplication across ETLs
and dashboard components.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.constants.etl import DATE_COMMON_FORMATS, DATE_ISO_FORMAT
from src.utils.logging import get_logger


class DateParser:
    """Unified date parsing with multiple format support.

    Provides consistent date parsing across the codebase with support for
    ISO formats, common date formats, Unix timestamps, and error handling.

    Example:
        >>> parser = DateParser()
        >>> dt = parser.parse("2024-01-15")
        >>> print(dt)
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

        >>> dt = parser.parse("Jan 15, 2024")
        >>> print(dt)
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

        >>> dt = parser.parse(None)
        >>> print(dt)
        None
    """

    def __init__(
        self,
        default_timezone: datetime.timezone = timezone.utc,
        raise_on_error: bool = False,
    ) -> None:
        """Initialize the date parser.

        Args:
            default_timezone: Default timezone for parsed dates (default: UTC)
            raise_on_error: If True, raise exceptions on parse errors;
                          if False, return None and log warning (default: False)
        """
        self.default_timezone = default_timezone
        self.raise_on_error = raise_on_error
        self.logger = get_logger(self.__class__.__name__)

    def parse(
        self,
        date_str: str | None | float | int,
        format_str: str | None = None,
    ) -> datetime | None:
        """Parse date string with automatic format detection.

        Attempts to parse dates in the following order:
        1. ISO format with timezone (2024-01-15T10:30:00+00:00)
        2. ISO format without timezone (2024-01-15T10:30:00)
        3. Custom format if provided
        4. Common date formats (YYYY-MM-DD, DD/MM/YYYY, etc.)
        5. Unix timestamp (seconds or milliseconds)

        Args:
            date_str: Date string, Unix timestamp, or None
            format_str: Optional specific format string for parsing

        Returns:
            Parsed datetime in default timezone, or None if parsing fails

        Raises:
            ValueError: If raise_on_error=True and parsing fails

        Example:
            >>> parser = DateParser()
            >>> parser.parse("2024-01-15")
            datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

            >>> parser.parse(1705305600)  # Unix timestamp
            datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
        """
        # Handle None or NaN
        if pd.isna(date_str) or date_str is None:
            return None

        # Handle numeric (Unix timestamp)
        if isinstance(date_str, (int, float)):
            return self._parse_timestamp(date_str)

        # Convert to string for parsing
        date_str = str(date_str).strip()

        # Try custom format first if provided
        if format_str:
            result = self._parse_with_format(date_str, format_str)
            if result:
                return result

        # Try ISO format with timezone
        result = self._parse_iso_with_tz(date_str)
        if result:
            return result

        # Try ISO format without timezone
        result = self._parse_iso_no_tz(date_str)
        if result:
            return result

        # Try common formats
        for fmt in DATE_COMMON_FORMATS:
            result = self._parse_with_format(date_str, fmt)
            if result:
                return result

        # Try Unix timestamp as string
        result = self._parse_timestamp(date_str)
        if result:
            return result

        # All parsing attempts failed
        if self.raise_on_error:
            raise ValueError(f"Could not parse date: {date_str}")

        self.logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_iso_with_tz(self, date_str: str) -> datetime | None:
        """Parse ISO format with timezone.

        Args:
            date_str: Date string in ISO format with timezone

        Returns:
            Parsed datetime or None if parsing fails
        """
        try:
            # Replace Z with +00:00 for UTC
            normalized = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            return dt.astimezone(self.default_timezone)
        except (ValueError, AttributeError):
            return None

    def _parse_iso_no_tz(self, date_str: str) -> datetime | None:
        """Parse ISO format without timezone.

        Args:
            date_str: Date string in ISO format without timezone

        Returns:
            Parsed datetime in default timezone or None if parsing fails
        """
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.replace(tzinfo=self.default_timezone)
        except (ValueError, AttributeError):
            return None

    def _parse_with_format(self, date_str: str, format_str: str) -> datetime | None:
        """Parse date with specific format string.

        Args:
            date_str: Date string to parse
            format_str: Format string for parsing

        Returns:
            Parsed datetime in default timezone or None if parsing fails
        """
        try:
            dt = datetime.strptime(date_str, format_str)
            return dt.replace(tzinfo=self.default_timezone)
        except ValueError:
            return None

    def _parse_timestamp(self, timestamp: str | int | float) -> datetime | None:
        """Parse Unix timestamp (seconds or milliseconds).

        Args:
            timestamp: Unix timestamp as string, int, or float

        Returns:
            Parsed datetime in default timezone or None if parsing fails
        """
        try:
            ts = float(timestamp)

            # Detect milliseconds vs seconds
            if ts > 10000000000:  # Milliseconds
                ts /= 1000

            return datetime.fromtimestamp(ts, tz=self.default_timezone)
        except (ValueError, OSError):
            return None

    def parse_batch(
        self,
        date_strings: list[str | None],
        format_str: str | None = None,
    ) -> list[datetime | None]:
        """Parse multiple date strings efficiently.

        Args:
            date_strings: List of date strings to parse
            format_str: Optional specific format string for all dates

        Returns:
            List of parsed datetimes (None for failed parses)

        Example:
            >>> parser = DateParser()
            >>> dates = ["2024-01-15", "2024-01-16", None]
            >>> parser.parse_batch(dates)
            [datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
             datetime.datetime(2024, 1, 16, 0, 0, tzinfo=datetime.timezone.utc),
             None]
        """
        return [self.parse(date_str, format_str) for date_str in date_strings]

    def format(
        self,
        dt: datetime | None,
        format_str: str = DATE_ISO_FORMAT,
    ) -> str | None:
        """Format datetime to string.

        Args:
            dt: Datetime to format (None returns None)
            format_str: Format string for output

        Returns:
            Formatted date string or None if dt is None

        Example:
            >>> parser = DateParser()
            >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            >>> parser.format(dt)
            '2024-01-15T10:30:00'
        """
        if dt is None:
            return None

        try:
            return dt.strftime(format_str)
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Failed to format datetime {dt}: {e}")
            return None

    def to_iso_format(self, dt: datetime | None) -> str | None:
        """Convert datetime to ISO format string.

        Args:
            dt: Datetime to convert (None returns None)

        Returns:
            ISO formatted string or None

        Example:
            >>> parser = DateParser()
            >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            >>> parser.to_iso_format(dt)
            '2024-01-15T10:30:00+00:00'
        """
        if dt is None:
            return None

        return dt.isoformat()

    def is_valid(self, date_str: str | None) -> bool:
        """Check if date string can be parsed.

        Args:
            date_str: Date string to validate

        Returns:
            True if date can be parsed, False otherwise

        Example:
            >>> parser = DateParser()
            >>> parser.is_valid("2024-01-15")
            True
            >>> parser.is_valid("invalid-date")
            False
        """
        return self.parse(date_str) is not None

    def now(self) -> datetime:
        """Get current time in default timezone.

        Returns:
            Current datetime in default timezone

        Example:
            >>> parser = DateParser()
            >>> now = parser.now()
            >>> isinstance(now, datetime)
            True
        """
        return datetime.now(self.default_timezone)

    def age_in_days(self, dt: datetime | None) -> int | None:
        """Calculate age of datetime in days.

        Args:
            dt: Datetime to calculate age for (None returns None)

        Returns:
            Age in days or None if dt is None

        Example:
            >>> parser = DateParser()
            >>> old_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            >>> age = parser.age_in_days(old_date)
            >>> print(age)
            359  # Approximate, depends on current date
        """
        if dt is None:
            return None

        now = self.now()
        delta = now - dt
        return delta.days


# Singleton instance for convenience
_default_parser: DateParser | None = None


def get_date_parser() -> DateParser:
    """Get the default date parser instance.

    Returns:
        Shared DateParser instance with UTC timezone

    Example:
        >>> parser = get_date_parser()
        >>> dt = parser.parse("2024-01-15")
    """
    global _default_parser
    if _default_parser is None:
        _default_parser = DateParser()
    return _default_parser


# Convenience functions for common operations
def parse_date(date_str: str | None, format_str: str | None = None) -> datetime | None:
    """Parse date string using default parser.

    Convenience function that uses the shared DateParser instance.

    Args:
        date_str: Date string to parse
        format_str: Optional specific format for parsing

    Returns:
        Parsed datetime or None

    Example:
        >>> parse_date("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
    """
    return get_date_parser().parse(date_str, format_str)


def format_date(dt: datetime | None, format_str: str = DATE_ISO_FORMAT) -> str | None:
    """Format datetime to string using default parser.

    Convenience function that uses the shared DateParser instance.

    Args:
        dt: Datetime to format
        format_str: Format string for output

    Returns:
        Formatted date string or None

    Example:
        >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> format_date(dt)
        '2024-01-15T10:30:00'
    """
    return get_date_parser().format(dt, format_str)


def to_iso_format(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format using default parser.

    Convenience function that uses the shared DateParser instance.

    Args:
        dt: Datetime to convert

    Returns:
        ISO formatted string or None

    Example:
        >>> dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> to_iso_format(dt)
        '2024-01-15T10:30:00+00:00'
    """
    return get_date_parser().to_iso_format(dt)
