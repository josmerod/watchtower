"""Statistics reporter for the Udemy Universal miner.

This module provides functionality to track, store, and display detailed
statistics about course enrollment, scraping performance, and user activity.
"""

import json
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from logger import get_logger

logger = get_logger(__name__)

STATS_FILE = "enrollment_statistics.json"
DAILY_STATS_FILE = "daily_statistics.json"


@dataclass
class EnrollmentStats:
    """Statistics for a single enrollment session."""

    session_id: str
    timestamp: str
    duration: float
    enrolled: int = 0
    already_enrolled: int = 0
    expired: int = 0
    excluded: int = 0
    failed: int = 0
    total_processed: int = 0
    amount_saved: float = 0.0
    sites_scraped: list[str] = None
    categories_processed: dict[str, int] = None
    languages_processed: dict[str, int] = None

    def __post_init__(self):
        if self.sites_scraped is None:
            self.sites_scraped = []
        if self.categories_processed is None:
            self.categories_processed = {}
        if self.languages_processed is None:
            self.languages_processed = {}


@dataclass
class SiteStats:
    """Statistics for a specific scraping site."""

    site_name: str
    courses_found: int = 0
    courses_processed: int = 0
    success_rate: float = 0.0
    avg_processing_time: float = 0.0
    errors: int = 0
    last_scraped: str = ""


@dataclass
class DailyStats:
    """Daily aggregated statistics."""

    date: str
    sessions: int = 0
    total_enrolled: int = 0
    total_processed: int = 0
    total_saved: float = 0.0
    active_sites: list[str] = None
    avg_session_duration: float = 0.0

    def __post_init__(self):
        if self.active_sites is None:
            self.active_sites = []


class StatisticsReporter:
    """Handles tracking and reporting of enrollment statistics."""

    def __init__(self, stats_file: str = STATS_FILE):
        """Initialize the statistics reporter.

        Args:
            stats_file: Path to the statistics file
        """
        self.stats_file = stats_file
        self.daily_stats_file = DAILY_STATS_FILE
        self.logger = logger
        self.current_session = None
        self.session_start_time = None
        self.site_stats = defaultdict(lambda: SiteStats(""))

        # Load existing statistics
        self.all_stats = self._load_statistics()
        self.daily_stats = self._load_daily_statistics()

    def _load_statistics(self) -> list[EnrollmentStats]:
        """Load statistics from file.

        Returns:
            List of enrollment statistics
        """
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file) as f:
                    data = json.load(f)
                    return [EnrollmentStats(**stat) for stat in data]
            return []
        except Exception as e:
            self.logger.warning(f"Failed to load statistics: {e}")
            return []

    def _save_statistics(self):
        """Save statistics to file."""
        try:
            with open(self.stats_file, "w") as f:
                json.dump([asdict(stat) for stat in self.all_stats], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save statistics: {e}")

    def _load_daily_statistics(self) -> dict[str, DailyStats]:
        """Load daily statistics from file.

        Returns:
            Dictionary of daily statistics
        """
        try:
            if os.path.exists(self.daily_stats_file):
                with open(self.daily_stats_file) as f:
                    data = json.load(f)
                    return {date: DailyStats(**stats) for date, stats in data.items()}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to load daily statistics: {e}")
            return {}

    def _save_daily_statistics(self):
        """Save daily statistics to file."""
        try:
            with open(self.daily_stats_file, "w") as f:
                json.dump(
                    {date: asdict(stats) for date, stats in self.daily_stats.items()},
                    f,
                    indent=2,
                )
        except Exception as e:
            self.logger.error(f"Failed to save daily statistics: {e}")

    def start_session(self, session_id: str = None) -> str:
        """Start a new enrollment session.

        Args:
            session_id: Optional custom session ID

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}"

        self.current_session = EnrollmentStats(
            session_id=session_id, timestamp=datetime.now().isoformat(), duration=0.0
        )
        self.session_start_time = time.time()
        self.site_stats.clear()

        self.logger.info(f"Started enrollment session: {session_id}")
        return session_id

    def end_session(self) -> EnrollmentStats | None:
        """End the current enrollment session.

        Returns:
            Final session statistics or None if no session active
        """
        if self.current_session is None:
            self.logger.warning("No active session to end")
            return None

        # Calculate session duration
        if self.session_start_time:
            self.current_session.duration = time.time() - self.session_start_time

        # Calculate totals
        self.current_session.total_processed = (
            self.current_session.enrolled
            + self.current_session.already_enrolled
            + self.current_session.expired
            + self.current_session.excluded
            + self.current_session.failed
        )

        # Add to all stats
        self.all_stats.append(self.current_session)

        # Update daily statistics
        self._update_daily_statistics(self.current_session)

        # Save statistics
        self._save_statistics()
        self._save_daily_statistics()

        session_stats = self.current_session
        self.current_session = None
        self.session_start_time = None

        self.logger.info(f"Ended enrollment session: {session_stats.session_id}")
        return session_stats

    def _update_daily_statistics(self, session: EnrollmentStats):
        """Update daily statistics with session data.

        Args:
            session: Enrollment session statistics
        """
        date = session.timestamp.split("T")[0]  # Extract date part

        if date not in self.daily_stats:
            self.daily_stats[date] = DailyStats(date=date)

        daily = self.daily_stats[date]
        daily.sessions += 1
        daily.total_enrolled += session.enrolled
        daily.total_processed += session.total_processed
        daily.total_saved += session.amount_saved

        # Update active sites
        for site in session.sites_scraped:
            if site not in daily.active_sites:
                daily.active_sites.append(site)

        # Calculate average session duration
        daily.avg_session_duration = (
            daily.avg_session_duration * (daily.sessions - 1) + session.duration
        ) / daily.sessions

    def record_enrollment(
        self,
        status: str,
        amount_saved: float = 0.0,
        category: str = None,
        language: str = None,
    ):
        """Record a course enrollment result.

        Args:
            status: Enrollment status ('enrolled', 'already_enrolled', 'expired', 'excluded', 'failed')
            amount_saved: Amount saved in currency
            category: Course category
            language: Course language
        """
        if self.current_session is None:
            self.logger.warning("No active session to record enrollment")
            return

        # Update counters
        if status == "enrolled":
            self.current_session.enrolled += 1
            self.current_session.amount_saved += amount_saved
        elif status == "already_enrolled":
            self.current_session.already_enrolled += 1
        elif status == "expired":
            self.current_session.expired += 1
        elif status == "excluded":
            self.current_session.excluded += 1
        elif status == "failed":
            self.current_session.failed += 1

        # Track categories
        if category:
            if category not in self.current_session.categories_processed:
                self.current_session.categories_processed[category] = 0
            self.current_session.categories_processed[category] += 1

        # Track languages
        if language:
            if language not in self.current_session.languages_processed:
                self.current_session.languages_processed[language] = 0
            self.current_session.languages_processed[language] += 1

    def record_site_activity(
        self,
        site_name: str,
        courses_found: int = 0,
        processing_time: float = 0.0,
        errors: int = 0,
    ):
        """Record activity for a specific site.

        Args:
            site_name: Name of the scraping site
            courses_found: Number of courses found
            processing_time: Time taken to process
            errors: Number of errors encountered
        """
        if self.current_session is None:
            return

        # Update site statistics
        site_stat = self.site_stats[site_name]
        site_stat.site_name = site_name
        site_stat.courses_found += courses_found
        site_stat.courses_processed += 1
        site_stat.errors += errors
        site_stat.last_scraped = datetime.now().isoformat()

        # Calculate average processing time
        if site_stat.courses_processed > 0:
            site_stat.avg_processing_time = (
                site_stat.avg_processing_time * (site_stat.courses_processed - 1)
                + processing_time
            ) / site_stat.courses_processed

        # Calculate success rate
        if site_stat.courses_processed > 0:
            site_stat.success_rate = (
                (site_stat.courses_processed - site_stat.errors)
                / site_stat.courses_processed
            ) * 100

        # Add to session sites
        if site_name not in self.current_session.sites_scraped:
            self.current_session.sites_scraped.append(site_name)

    def get_session_summary(self) -> dict[str, Any] | None:
        """Get summary of current or last session.

        Returns:
            Dictionary containing session summary
        """
        session = self.current_session or (
            self.all_stats[-1] if self.all_stats else None
        )
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "timestamp": session.timestamp,
            "duration": session.duration,
            "results": {
                "enrolled": session.enrolled,
                "already_enrolled": session.already_enrolled,
                "expired": session.expired,
                "excluded": session.excluded,
                "failed": session.failed,
                "total_processed": session.total_processed,
            },
            "amount_saved": session.amount_saved,
            "sites_scraped": session.sites_scraped,
            "categories": session.categories_processed,
            "languages": session.languages_processed,
            "success_rate": (session.enrolled / max(1, session.total_processed)) * 100,
        }

    def display_session_report(self, session: EnrollmentStats = None):
        """Display a detailed session report.

        Args:
            session: Session to report on, or current/last session if None
        """
        if session is None:
            session = self.current_session or (
                self.all_stats[-1] if self.all_stats else None
            )

        if not session:
            self.logger.info("No session data available")
            return

        # Format duration
        duration_str = f"{session.duration:.1f}s"
        if session.duration > 60:
            duration_str = f"{session.duration / 60:.1f}m"

        # Calculate success rate
        success_rate = (session.enrolled / max(1, session.total_processed)) * 100

        self.logger.info("=" * 60)
        self.logger.info("📊 ENROLLMENT SESSION REPORT")
        self.logger.info("=" * 60)
        self.logger.info(f"Session ID:           {session.session_id}")
        self.logger.info(f"Timestamp:            {session.timestamp}")
        self.logger.info(f"Duration:             {duration_str}")
        self.logger.info("")
        self.logger.info("📈 ENROLLMENT RESULTS:")
        self.logger.info(f"  Successfully Enrolled:  {session.enrolled}")
        self.logger.info(f"  Already Enrolled:       {session.already_enrolled}")
        self.logger.info(f"  Expired Coupons:        {session.expired}")
        self.logger.info(f"  Excluded Courses:       {session.excluded}")
        self.logger.info(f"  Failed Attempts:        {session.failed}")
        self.logger.info(f"  Total Processed:        {session.total_processed}")
        self.logger.info(f"  Success Rate:           {success_rate:.1f}%")
        self.logger.info("")
        self.logger.info(f"💰 AMOUNT SAVED:          ${session.amount_saved:.2f}")
        self.logger.info("")

        if session.sites_scraped:
            self.logger.info("🌐 SITES SCRAPED:")
            for site in session.sites_scraped:
                self.logger.info(f"  • {site}")
            self.logger.info("")

        if session.categories_processed:
            self.logger.info("📚 CATEGORIES PROCESSED:")
            for category, count in sorted(
                session.categories_processed.items(), key=lambda x: x[1], reverse=True
            ):
                self.logger.info(f"  • {category}: {count}")
            self.logger.info("")

        if session.languages_processed:
            self.logger.info("🌍 LANGUAGES PROCESSED:")
            for language, count in sorted(
                session.languages_processed.items(), key=lambda x: x[1], reverse=True
            ):
                self.logger.info(f"  • {language}: {count}")

        self.logger.info("=" * 60)

    def display_overall_statistics(self, days: int = 30):
        """Display overall statistics for the specified period.

        Args:
            days: Number of days to include in statistics
        """
        if not self.all_stats:
            self.logger.info("No statistics available")
            return

        # Filter statistics by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_stats = [
            stat
            for stat in self.all_stats
            if datetime.fromisoformat(stat.timestamp) >= cutoff_date
        ]

        if not recent_stats:
            self.logger.info(f"No statistics available for the last {days} days")
            return

        # Calculate totals
        total_enrolled = sum(stat.enrolled for stat in recent_stats)
        total_processed = sum(stat.total_processed for stat in recent_stats)
        total_saved = sum(stat.amount_saved for stat in recent_stats)
        total_sessions = len(recent_stats)
        avg_duration = sum(stat.duration for stat in recent_stats) / len(recent_stats)

        # Calculate success rate
        success_rate = (total_enrolled / max(1, total_processed)) * 100

        # Get most active sites
        site_counts = defaultdict(int)
        for stat in recent_stats:
            for site in stat.sites_scraped:
                site_counts[site] += 1

        self.logger.info("=" * 60)
        self.logger.info(f"📊 OVERALL STATISTICS (Last {days} days)")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Sessions:           {total_sessions}")
        self.logger.info(f"Total Enrolled:           {total_enrolled}")
        self.logger.info(f"Total Processed:          {total_processed}")
        self.logger.info(f"Total Saved:              ${total_saved:.2f}")
        self.logger.info(f"Average Session Duration: {avg_duration / 60:.1f}m")
        self.logger.info(f"Overall Success Rate:     {success_rate:.1f}%")
        self.logger.info("")

        if site_counts:
            self.logger.info("🌐 MOST ACTIVE SITES:")
            for site, count in sorted(
                site_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                self.logger.info(f"  • {site}: {count} sessions")

        self.logger.info("=" * 60)

    def export_statistics(self, format: str = "json", filename: str = None) -> str:
        """Export statistics to file.

        Args:
            format: Export format ('json', 'csv')
            filename: Output filename (auto-generated if None)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"udemy_statistics_{timestamp}.{format}"

        try:
            if format == "json":
                with open(filename, "w") as f:
                    json.dump(
                        {
                            "sessions": [asdict(stat) for stat in self.all_stats],
                            "daily_stats": {
                                date: asdict(stats)
                                for date, stats in self.daily_stats.items()
                            },
                            "exported_at": datetime.now().isoformat(),
                        },
                        f,
                        indent=2,
                    )
            elif format == "csv":
                import csv

                with open(filename, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "Session ID",
                            "Timestamp",
                            "Duration",
                            "Enrolled",
                            "Already Enrolled",
                            "Expired",
                            "Excluded",
                            "Failed",
                            "Total Processed",
                            "Amount Saved",
                            "Sites Scraped",
                            "Success Rate",
                        ]
                    )
                    for stat in self.all_stats:
                        success_rate = (
                            stat.enrolled / max(1, stat.total_processed)
                        ) * 100
                        writer.writerow(
                            [
                                stat.session_id,
                                stat.timestamp,
                                stat.duration,
                                stat.enrolled,
                                stat.already_enrolled,
                                stat.expired,
                                stat.excluded,
                                stat.failed,
                                stat.total_processed,
                                stat.amount_saved,
                                ";".join(stat.sites_scraped),
                                success_rate,
                            ]
                        )

            self.logger.info(f"Statistics exported to: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to export statistics: {e}")
            return ""


# Global instance
stats_reporter = StatisticsReporter()


def start_session(session_id: str = None) -> str:
    """Convenience function to start a statistics session."""
    return stats_reporter.start_session(session_id)


def end_session() -> EnrollmentStats | None:
    """Convenience function to end a statistics session."""
    return stats_reporter.end_session()


def record_enrollment(
    status: str, amount_saved: float = 0.0, category: str = None, language: str = None
):
    """Convenience function to record enrollment."""
    stats_reporter.record_enrollment(status, amount_saved, category, language)


def record_site_activity(
    site_name: str,
    courses_found: int = 0,
    processing_time: float = 0.0,
    errors: int = 0,
):
    """Convenience function to record site activity."""
    stats_reporter.record_site_activity(
        site_name, courses_found, processing_time, errors
    )


def display_session_report():
    """Convenience function to display session report."""
    stats_reporter.display_session_report()


def display_overall_statistics(days: int = 30):
    """Convenience function to display overall statistics."""
    stats_reporter.display_overall_statistics(days)


if __name__ == "__main__":
    # Test the statistics reporter
    print("Testing statistics reporter...")

    # Start a test session
    session_id = start_session("test_session")

    # Record some test activities
    record_site_activity("Tutorial Bar", 50, 5.2, 0)
    record_site_activity("Discudemy", 30, 3.1, 1)

    record_enrollment("enrolled", 50.0, "development", "en")
    record_enrollment("enrolled", 30.0, "business", "en")
    record_enrollment("already_enrolled")
    record_enrollment("expired")
    record_enrollment("excluded")

    # End session and display report
    end_session()
    display_session_report()
    display_overall_statistics()
