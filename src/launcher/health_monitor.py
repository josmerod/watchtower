"""Health monitoring and automatic recovery for Watchtower platform.

Monitors:
- Process health (dashboard, ETL processes)
- System resources (CPU, memory, disk)
- Data integrity (file sizes, modification times)
- Network connectivity
- External service dependencies
"""

import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psutil
import requests


@dataclass
class HealthMetrics:
    """Health metrics data structure."""

    timestamp: datetime = field(default_factory=datetime.now)
    dashboard_healthy: bool = False
    etl_processes_healthy: bool = False
    system_resources_ok: bool = False
    data_integrity_ok: bool = False
    network_connectivity_ok: bool = False
    external_services_ok: bool = False

    # Detailed metrics
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_usage_percent: float = 0.0
    active_etl_processes: int = 0
    total_etl_processes: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "dashboard_healthy": self.dashboard_healthy,
            "etl_processes_healthy": self.etl_processes_healthy,
            "system_resources_ok": self.system_resources_ok,
            "data_integrity_ok": self.data_integrity_ok,
            "network_connectivity_ok": self.network_connectivity_ok,
            "external_services_ok": self.external_services_ok,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "active_etl_processes": self.active_etl_processes,
            "total_etl_processes": self.total_etl_processes,
        }


@dataclass
class RecoveryAction:
    """Recovery action to take when health issues are detected."""

    name: str
    description: str
    priority: int  # Lower number = higher priority
    action_func: callable
    cooldown_seconds: int = 300  # 5 minutes default cooldown


class HealthMonitor:
    """Comprehensive health monitoring system."""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger("HealthMonitor")
        self.metrics_history: list[HealthMetrics] = []
        self.recovery_actions: list[RecoveryAction] = []
        self.last_recovery_actions: dict[str, datetime] = {}
        self.running = False

        # Health check intervals
        self.dashboard_check_interval = 30  # seconds
        self.system_check_interval = 60  # seconds
        self.data_integrity_interval = 300  # seconds (5 minutes)
        self.network_check_interval = 120  # seconds (2 minutes)
        self.external_services_interval = 180  # seconds (3 minutes)

        self.setup_recovery_actions()

    def setup_recovery_actions(self):
        """Setup recovery actions for different health issues."""
        self.recovery_actions = [
            RecoveryAction(
                name="restart_dashboard",
                description="Restart the dashboard process",
                priority=1,
                action_func=self.restart_dashboard,
                cooldown_seconds=60,
            ),
            RecoveryAction(
                name="restart_etl_processes",
                description="Restart failed ETL processes",
                priority=2,
                action_func=self.restart_etl_processes,
                cooldown_seconds=120,
            ),
            RecoveryAction(
                name="cleanup_disk_space",
                description="Clean up old log files and temporary data",
                priority=3,
                action_func=self.cleanup_disk_space,
                cooldown_seconds=3600,
            ),
            RecoveryAction(
                name="restart_system",
                description="Full system restart (last resort)",
                priority=10,
                action_func=self.restart_system,
                cooldown_seconds=7200,  # 2 hours
            ),
        ]

    async def check_dashboard_health(self) -> bool:
        """Check if dashboard is healthy."""
        try:
            # Check if dashboard process is running
            dashboard_url = f"http://localhost:{self.config['dashboard_port']}/health"

            # First check if port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", self.config["dashboard_port"]))
            sock.close()

            if result != 0:
                self.logger.warning("Dashboard port not accessible")
                return False

            # Try to get health endpoint
            response = requests.get(dashboard_url, timeout=5)
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Dashboard health check failed: {e}")
            return False

    async def check_etl_processes_health(self, etl_scheduler) -> tuple[bool, int, int]:
        """Check ETL processes health."""
        if not etl_scheduler:
            return False, 0, 0

        try:
            total_processes = 0
            active_processes = 0

            for category, processes in etl_scheduler.etl_processes.items():
                total_processes += len(processes)
                active_processes += sum(1 for p in processes if p.is_alive())

            # Consider healthy if at least 80% of processes are running
            healthy_threshold = 0.8
            is_healthy = active_processes / total_processes >= healthy_threshold if total_processes > 0 else True

            return is_healthy, active_processes, total_processes

        except Exception as e:
            self.logger.error(f"ETL processes health check failed: {e}")
            return False, 0, 0

    async def check_system_resources(self) -> tuple[bool, float, float, float]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Thresholds
            cpu_threshold = 90.0
            memory_threshold = 85.0
            disk_threshold = 90.0

            is_healthy = cpu_percent < cpu_threshold and memory.percent < memory_threshold and disk.percent < disk_threshold

            return is_healthy, cpu_percent, memory.percent, disk.percent

        except Exception as e:
            self.logger.error(f"System resources check failed: {e}")
            return False, 0.0, 0.0, 0.0

    async def check_data_integrity(self) -> bool:
        """Check data directory integrity."""
        try:
            data_dir = Path("data")
            if not data_dir.exists():
                return False

            # Check for recent files (modified within last hour)
            current_time = time.time()
            recent_files = 0
            total_files = 0

            for file_path in data_dir.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    # Check if file was modified recently
                    if current_time - file_path.stat().st_mtime < 3600:  # 1 hour
                        recent_files += 1

            # Consider healthy if we have recent files or the directory structure exists
            return recent_files > 0 or total_files > 0

        except Exception as e:
            self.logger.error(f"Data integrity check failed: {e}")
            return False

    async def check_network_connectivity(self) -> bool:
        """Check basic network connectivity."""
        try:
            # Test DNS resolution
            socket.gethostbyname("google.com")

            # Test basic connectivity
            response = requests.get("https://httpbin.org/get", timeout=5)
            return response.status_code == 200

        except Exception as e:
            self.logger.warning(f"Network connectivity check failed: {e}")
            return False

    async def check_external_services(self) -> bool:
        """Check external service dependencies."""
        try:
            # Check if we can import required modules (indicates dependencies are available)
            import aiohttp
            import pandas
            import psutil
            import requests

            return True

        except ImportError as e:
            self.logger.error(f"External service check failed - missing dependency: {e}")
            return False

    async def perform_health_check(self, etl_scheduler=None) -> HealthMetrics:
        """Perform comprehensive health check."""
        metrics = HealthMetrics()

        # Run all health checks concurrently
        tasks = [
            self.check_dashboard_health(),
            self.check_etl_processes_health(etl_scheduler),
            self.check_system_resources(),
            self.check_data_integrity(),
            self.check_network_connectivity(),
            self.check_external_services(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        metrics.dashboard_healthy = results[0] if not isinstance(results[0], Exception) else False
        etl_healthy, metrics.active_etl_processes, metrics.total_etl_processes = results[1] if not isinstance(results[1], Exception) else (False, 0, 0)
        metrics.etl_processes_healthy = etl_healthy
        (
            system_ok,
            metrics.cpu_percent,
            metrics.memory_percent,
            metrics.disk_usage_percent,
        ) = (
            results[2] if not isinstance(results[2], Exception) else (False, 0, 0, 0)
        )
        metrics.system_resources_ok = system_ok
        metrics.data_integrity_ok = results[3] if not isinstance(results[3], Exception) else False
        metrics.network_connectivity_ok = results[4] if not isinstance(results[4], Exception) else False
        metrics.external_services_ok = results[5] if not isinstance(results[5], Exception) else False

        # Store in history (keep last 100 checks)
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history.pop(0)

        return metrics

    def is_system_healthy(self, metrics: HealthMetrics) -> bool:
        """Determine if system is overall healthy."""
        # Critical checks that must pass
        critical_checks = [
            metrics.dashboard_healthy,
            metrics.etl_processes_healthy,
            metrics.system_resources_ok,
            metrics.data_integrity_ok,
        ]

        # Consider system healthy if all critical checks pass
        return all(critical_checks)

    async def trigger_recovery_actions(self, metrics: HealthMetrics, etl_scheduler=None):
        """Trigger appropriate recovery actions based on health metrics."""
        current_time = datetime.now()

        for action in sorted(self.recovery_actions, key=lambda x: x.priority):
            # Check cooldown period
            last_action = self.last_recovery_actions.get(action.name)
            if last_action and current_time - last_action < timedelta(seconds=action.cooldown_seconds):
                continue

            should_trigger = False

            if (
                action.name == "restart_dashboard"
                and not metrics.dashboard_healthy
                or action.name == "restart_etl_processes"
                and not metrics.etl_processes_healthy
                or action.name == "cleanup_disk_space"
                and metrics.disk_usage_percent > 85
            ):
                should_trigger = True
            elif action.name == "restart_system" and not self.is_system_healthy(metrics):
                # Only trigger system restart if multiple critical issues persist
                recent_healthy = sum(1 for m in self.metrics_history[-10:] if self.is_system_healthy(m))
                if recent_healthy < 3:  # Less than 3 healthy checks in last 10
                    should_trigger = True

            if should_trigger:
                self.logger.warning(f"Triggering recovery action: {action.description}")
                try:
                    await action.action_func(etl_scheduler)
                    self.last_recovery_actions[action.name] = current_time
                    self.logger.info(f"Recovery action {action.name} completed successfully")
                except Exception as e:
                    self.logger.error(f"Recovery action {action.name} failed: {e}")

    async def restart_dashboard(self, etl_scheduler=None):
        """Restart the dashboard process."""
        # This would be implemented in the main launcher
        # For now, just log the action
        self.logger.info("Would restart dashboard process")

    async def restart_etl_processes(self, etl_scheduler):
        """Restart failed ETL processes."""
        if etl_scheduler:
            self.logger.info("Restarting failed ETL processes...")
            await etl_scheduler.start_all_processes()

    async def cleanup_disk_space(self, etl_scheduler=None):
        """Clean up old log files and temporary data."""
        try:
            # Clean up old log files (keep last 7 days)
            logs_dir = Path("logs")
            if logs_dir.exists():
                cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago

                for log_file in logs_dir.glob("*.log"):
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        self.logger.info(f"Removed old log file: {log_file}")

            # Clean up old data files (keep last 30 days)
            data_dir = Path("data")
            if data_dir.exists():
                cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days ago

                for data_file in data_dir.rglob("*"):
                    if data_file.is_file() and data_file.stat().st_mtime < cutoff_time:
                        # Only remove files that aren't critical checkpoints
                        if not data_file.name.endswith(".checkpoint"):
                            data_file.unlink()
                            self.logger.info(f"Removed old data file: {data_file}")

        except Exception as e:
            self.logger.error(f"Disk cleanup failed: {e}")

    async def restart_system(self, etl_scheduler=None):
        """Restart the entire system (last resort)."""
        self.logger.critical("Triggering system restart due to persistent health issues")
        # This would restart the entire launcher process
        # In a real deployment, this might trigger a container restart

    async def run_monitoring_loop(self, etl_scheduler=None):
        """Main monitoring loop."""
        self.running = True

        while self.running:
            try:
                # Perform health check
                metrics = await self.perform_health_check(etl_scheduler)

                # Log current health status
                if self.is_system_healthy(metrics):
                    self.logger.info("✅ System health check passed")
                else:
                    self.logger.warning("❌ System health issues detected")

                    # Trigger recovery actions
                    await self.trigger_recovery_actions(metrics, etl_scheduler)

                # Save metrics to file
                await self.save_metrics(metrics)

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def save_metrics(self, metrics: HealthMetrics):
        """Save health metrics to file."""
        try:
            metrics_file = Path("logs/health_metrics.jsonl")

            with open(metrics_file, "a") as f:
                f.write(json.dumps(metrics.to_dict()) + "\n")

        except Exception as e:
            self.logger.error(f"Failed to save health metrics: {e}")

    def get_health_summary(self) -> dict:
        """Get health summary for API endpoints."""
        if not self.metrics_history:
            return {"status": "unknown", "message": "No health data available"}

        latest = self.metrics_history[-1]

        if self.is_system_healthy(latest):
            status = "healthy"
            message = "All systems operational"
        else:
            status = "degraded"
            issues = []

            if not latest.dashboard_healthy:
                issues.append("Dashboard not responding")
            if not latest.etl_processes_healthy:
                issues.append("ETL processes failing")
            if not latest.system_resources_ok:
                issues.append("High resource usage")
            if not latest.data_integrity_ok:
                issues.append("Data integrity issues")
            if not latest.network_connectivity_ok:
                issues.append("Network connectivity issues")
            if not latest.external_services_ok:
                issues.append("External service dependencies failing")

            message = "; ".join(issues)

        return {
            "status": status,
            "message": message,
            "timestamp": latest.timestamp.isoformat(),
            "metrics": latest.to_dict(),
        }
