"""
Robust date parsing utility for Watchtower application.
Handles various date formats and provides fallback mechanisms.
"""

import re
from datetime import datetime, timezone
from typing import Optional, List
from dateutil import parser as dateutil_parser
import logging

logger = logging.getLogger(__name__)

class RobustDateParser:
    """Robust date parser that handles multiple formats and provides graceful fallbacks."""
    
    # Common date formats ordered by specificity
    DATETIME_FORMATS = [
        "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO 8601 with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S%z",     # ISO 8601 without microseconds, with timezone
        "%Y-%m-%d %H:%M:%S%z",     # Common format with timezone
        "%Y-%m-%dT%H:%M:%S",       # ISO 8601, no timezone (assumed UTC later)
        "%Y-%m-%d %H:%M:%S",       # Common format, no timezone (assumed UTC later)
        "%a, %d %b %Y %H:%M:%S %Z", # RFC 822/1123 (e.g., "Mon, 01 Jan 2024 12:00:00 GMT")
        "%a, %d %b %Y %H:%M:%S %z", # RFC 822/1123 with numeric timezone
        "%Y-%m-%d",                # Date only
        "%m/%d/%Y %I:%M:%S %p",    # e.g., 01/20/2024 10:00:00 AM
        "%d/%m/%Y %H:%M:%S",       # e.g., 20/01/2024 10:00:00
        "%d.%m.%Y",                # European format: 27.12.2024
        "%d.%m.%y",                # European format short year: 27.12.24
        "%m.%d.%y",                # US format short year: 12.27.24
        "%d/%m/%Y",                # European format: 27/12/2024
        "%m/%d/%Y",                # US format: 12/27/2024
        "%Y%m%d",                  # Compact format: 20241227
        "%B %d, %Y",               # Long format: December 27, 2024
        "%b %d, %Y",               # Short format: Dec 27, 2024
        "%d %B %Y",                # European long: 27 December 2024
        "%d %b %Y",                # European short: 27 Dec 2024
    ]
    
    @staticmethod
    def parse_date(date_str: str, suppress_warnings: bool = False) -> Optional[datetime]:
        """
        Parse a date string using multiple strategies.
        
        Args:
            date_str: The date string to parse
            suppress_warnings: Whether to suppress parsing warnings
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not date_str or str(date_str).strip() == "":
            return None
            
        s_date = str(date_str).strip()
        
        # Strategy 1: Try ISO 8601 format first (most reliable)
        try:
            dt = datetime.fromisoformat(s_date.replace('Z', '+00:00'))
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
            
        # Strategy 2: Handle problematic formats like "6.12.25"
        problematic_patterns = [
            (r'^(\d{1,2})\.(\d{1,2})\.(\d{2})$', RobustDateParser._parse_dot_format_short),
            (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', RobustDateParser._parse_dot_format_long),
            (r'^(\d{1,2})/(\d{1,2})/(\d{2})$', RobustDateParser._parse_slash_format_short),
            (r'^(\d{1,2})-(\d{1,2})-(\d{2})$', RobustDateParser._parse_dash_format_short),
        ]
        
        for pattern, parser_func in problematic_patterns:
            match = re.match(pattern, s_date)
            if match:
                try:
                    return parser_func(match.groups())
                except (ValueError, TypeError):
                    continue
        
        # Strategy 3: Try dateutil parser (very flexible)
        try:
            dt = dateutil_parser.parse(s_date)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
            
        # Strategy 4: Try common string formats using strptime
        for fmt in RobustDateParser.DATETIME_FORMATS:
            try:
                dt = datetime.strptime(s_date, fmt)
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
                
        # Strategy 5: Try epoch timestamp
        if s_date.replace('.', '', 1).isdigit() and len(s_date) >= 10:
            try:
                timestamp = float(s_date)
                # Heuristic: if timestamp is very large, it might be milliseconds
                if timestamp > 3 * (10**9):  # Roughly year 2065 in seconds
                    timestamp /= 1000.0
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, TypeError):
                pass
                
        # Strategy 6: Try relative time parsing (e.g., "2 hours ago")
        relative_dt = RobustDateParser._parse_relative_time(s_date)
        if relative_dt:
            return relative_dt
            
        # All strategies failed
        if not suppress_warnings:
            logger.debug(f"Could not parse date string: {s_date} with any known format.")
        
        return None
        
    @staticmethod
    def _parse_dot_format_short(groups: tuple) -> datetime:
        """Parse dates like '6.12.25' - assume day.month.year"""
        day, month, year = groups
        
        # Convert 2-digit year to 4-digit (assume 20xx for years 00-30, 19xx for 31-99)
        year_int = int(year)
        if year_int <= 30:
            year_int += 2000
        else:
            year_int += 1900
            
        return datetime(year_int, int(month), int(day), tzinfo=timezone.utc)
        
    @staticmethod
    def _parse_dot_format_long(groups: tuple) -> datetime:
        """Parse dates like '6.12.2025' - assume day.month.year"""
        day, month, year = groups
        return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
        
    @staticmethod
    def _parse_slash_format_short(groups: tuple) -> datetime:
        """Parse dates like '12/6/25' - assume month/day/year (US format)"""
        month, day, year = groups
        
        # Convert 2-digit year to 4-digit
        year_int = int(year)
        if year_int <= 30:
            year_int += 2000
        else:
            year_int += 1900
            
        return datetime(year_int, int(month), int(day), tzinfo=timezone.utc)
        
    @staticmethod
    def _parse_dash_format_short(groups: tuple) -> datetime:
        """Parse dates like '12-6-25' - assume month-day-year (US format)"""
        month, day, year = groups
        
        # Convert 2-digit year to 4-digit
        year_int = int(year)
        if year_int <= 30:
            year_int += 2000
        else:
            year_int += 1900
            
        return datetime(year_int, int(month), int(day), tzinfo=timezone.utc)
        
    @staticmethod
    def _parse_relative_time(date_str: str) -> Optional[datetime]:
        """Parse relative time strings like '2 hours ago', '3 days ago'"""
        import re
        from datetime import timedelta
        
        # Pattern for relative time: number + unit + ago
        pattern = r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago'
        match = re.search(pattern, date_str.lower())
        
        if not match:
            return None
            
        amount = int(match.group(1))
        unit = match.group(2)
        
        now = datetime.now(timezone.utc)
        
        if unit == 'second':
            return now - timedelta(seconds=amount)
        elif unit == 'minute':
            return now - timedelta(minutes=amount)
        elif unit == 'hour':
            return now - timedelta(hours=amount)
        elif unit == 'day':
            return now - timedelta(days=amount)
        elif unit == 'week':
            return now - timedelta(weeks=amount)
        elif unit == 'month':
            return now - timedelta(days=amount * 30)  # Approximate
        elif unit == 'year':
            return now - timedelta(days=amount * 365)  # Approximate
            
        return None
        
    @staticmethod
    def format_datetime(dt: Optional[datetime], format_str: str = '%Y-%m-%d %H:%M UTC') -> str:
        """Format datetime with fallback for None values."""
        if dt is None:
            return "Date N/A"
        try:
            return dt.strftime(format_str)
        except (ValueError, AttributeError):
            return "Date N/A"


# Convenience functions for common use cases
def parse_date(date_str: str, suppress_warnings: bool = False) -> Optional[datetime]:
    """Parse a date string using robust parsing strategies."""
    return RobustDateParser.parse_date(date_str, suppress_warnings)


def format_date(dt: Optional[datetime], format_str: str = '%Y-%m-%d') -> str:
    """Format a datetime object with fallback."""
    return RobustDateParser.format_datetime(dt, format_str)


def parse_and_format_date(date_str: str, format_str: str = '%Y-%m-%d', suppress_warnings: bool = False) -> str:
    """Parse and format a date string in one step."""
    parsed_dt = parse_date(date_str, suppress_warnings)
    return format_date(parsed_dt, format_str) 