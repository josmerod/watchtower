"""Health monitoring utilities for Watchtower dashboard."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.web.dashboard.models import ETLHealthMetrics, HealthStatus, MetricsSummary, MetricsCacheEntry


class HealthMonitor:
    """Health monitoring and metrics collection service."""

    def __init__(self, data_dir: str = "data"):
        """Initialize health monitor.

        Args:
            data_dir: Base data directory path
        """
        self.data_dir = Path(data_dir)
        self.metrics_dir = self.data_dir / "metrics"
        self.start_time = time.time()
        self._cache: Dict[str, MetricsCacheEntry] = {}

    def get_uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time

    def read_latest_etl_metrics(self) -> Dict[str, Any]:
        """Read latest ETL metrics from aggregated metrics file.

        Returns:
            Dictionary containing latest ETL run metrics
        """
        try:
            latest_metrics_file = self.metrics_dir / "etl_runs_latest.json"
            if not latest_metrics_file.exists():
                return {}

            with open(latest_metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data.get("runs", {})
        except Exception:
            return {}

    def read_per_etl_metrics(self, etl_name: str) -> Optional[Dict[str, Any]]:
        """Read latest metrics for a specific ETL.

        Args:
            etl_name: Name of the ETL process

        Returns:
            Latest metrics data or None if not found
        """
        try:
            latest_file = self.metrics_dir / etl_name / "latest_metrics.json"
            if not latest_file.exists():
                return None

            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def calculate_etl_health(self, etl_name: str, recent_runs: int = 10) -> ETLHealthMetrics:
        """Calculate health status for a specific ETL.

        Args:
            etl_name: Name of the ETL process
            recent_runs: Number of recent runs to analyze

        Returns:
            ETL health metrics
        """
        latest_metrics = self.read_per_etl_metrics(etl_name)

        if not latest_metrics:
            return ETLHealthMetrics(
                etl_name=etl_name,
                status="unknown",
                error_rate=100.0,
                error_count=0,
                total_runs=0
            )

        # Extract basic metrics
        success_rate = latest_metrics.get("success_rate", 0.0)
        error_count = latest_metrics.get("error_count", 0)
        last_run_time = None

        if latest_metrics.get("end_time"):
            try:
                last_run_time = datetime.fromisoformat(latest_metrics["end_time"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        # Determine ETL status
        if success_rate >= 90:
            status = "healthy"
        elif success_rate >= 70:
            status = "degraded"
        else:
            status = "failed"

        return ETLHealthMetrics(
            etl_name=etl_name,
            last_run_time=last_run_time,
            success_rate=success_rate,
            error_count=error_count,
            total_runs=1,  # We're looking at latest run
            status=status
        )

    def calculate_overall_health(self) -> HealthStatus:
        """Calculate overall system health status.

        Returns:
            Overall health status
        """
        etl_metrics = self.read_latest_etl_metrics()

        if not etl_metrics:
            return HealthStatus(
                status="down",
                timestamp=datetime.utcnow(),
                uptime_seconds=self.get_uptime_seconds(),
                details={"reason": "No ETL metrics available"}
            )

        # Analyze recent ETL runs
        total_runs = len(etl_metrics)
        failed_runs = 0
        degraded_runs = 0

        for etl_name, metrics_data in etl_metrics.items():
            if not isinstance(metrics_data, dict):
                continue

            success_rate = metrics_data.get("success_rate", 0.0)
            if success_rate < 70:
                failed_runs += 1
            elif success_rate < 90:
                degraded_runs += 1

        # Calculate failure percentage
        failure_percentage = (failed_runs / total_runs * 100) if total_runs > 0 else 0

        # Determine overall status
        if failure_percentage > 10:  # AC2: >10% failed = degraded
            status = "degraded"
        elif failure_percentage > 50:  # Very high failure rate = down
            status = "down"
        elif not self._can_read_data_files():
            status = "down"  # AC3: Can't read data files = down
        else:
            status = "ok"

        details = {
            "total_etl_runs": total_runs,
            "failed_runs": failed_runs,
            "degraded_runs": degraded_runs,
            "failure_percentage": failure_percentage,
            "can_read_data_files": self._can_read_data_files()
        }

        return HealthStatus(
            status=status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime_seconds=self.get_uptime_seconds(),
            details=details
        )

    def _can_read_data_files(self) -> bool:
        """Check if dashboard can read essential data files.

        Returns:
            True if data files are readable
        """
        try:
            # Check a few critical data files
            critical_files = [
                self.data_dir / "metrics" / "etl_runs_latest.json",
                self.data_dir / "shortcuts" / "predefined_shortcuts.json"
            ]

            readable_count = 0
            for file_path in critical_files:
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json.load(f)
                        readable_count += 1
                    except Exception:
                        pass

            # Consider system healthy if at least 50% of critical files are readable
            return readable_count >= len(critical_files) // 2

        except Exception:
            return False

    def generate_metrics_summary(self) -> MetricsSummary:
        """Generate comprehensive metrics summary.

        Returns:
            Metrics summary with all required fields
        """
        etl_metrics = self.read_latest_etl_metrics()

        # Calculate total sources and items
        total_sources = len(etl_metrics)
        total_items = 0
        last_etl_run_times = {}
        error_rates_per_source = {}
        etl_health = []

        for etl_name, metrics_data in etl_metrics.items():
            if not isinstance(metrics_data, dict):
                continue

            # Extract metrics
            items_loaded = metrics_data.get("records_loaded", 0)
            total_items += items_loaded

            # Last run time
            end_time = metrics_data.get("end_time")
            if end_time:
                try:
                    last_etl_run_times[etl_name] = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    last_etl_run_times[etl_name] = None
            else:
                last_etl_run_times[etl_name] = None

            # Error rate
            success_rate = metrics_data.get("success_rate", 100.0)
            error_rates_per_source[etl_name] = 100.0 - success_rate

            # Individual ETL health
            etl_health.append(self.calculate_etl_health(etl_name))

        # Performance metrics
        performance_metrics = {
            "total_etl_processes": total_sources,
            "healthy_etl_count": sum(1 for health in etl_health if health.status == "healthy"),
            "degraded_etl_count": sum(1 for health in etl_health if health.status == "degraded"),
            "failed_etl_count": sum(1 for health in etl_health if health.status == "failed"),
            "server_uptime_seconds": self.get_uptime_seconds()
        }

        return MetricsSummary(
            generated_at=datetime.utcnow(),
            total_sources=total_sources,
            total_items=total_items,
            last_etl_run_times=last_etl_run_times,
            error_rates_per_source=error_rates_per_source,
            etl_health=etl_health,
            performance_metrics=performance_metrics
        )

    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired.

        Args:
            cache_key: Cache key for the response

        Returns:
            Cached response data or None
        """
        if cache_key not in self._cache:
            return None

        cache_entry = self._cache[cache_key]
        if cache_entry.is_expired():
            del self._cache[cache_key]
            return None

        return cache_entry.data

    def set_cached_response(self, cache_key: str, data: Dict[str, Any], ttl_minutes: int = 5) -> None:
        """Cache response data with TTL.

        Args:
            cache_key: Cache key for the response
            data: Response data to cache
            ttl_minutes: Time to live in minutes
        """
        self._cache[cache_key] = MetricsCacheEntry(
            data=data,
            timestamp=datetime.utcnow(),
            ttl_minutes=ttl_minutes
        )

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()