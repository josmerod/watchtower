#!/usr/bin/env python3
"""Watchtower Unified Launcher

Main entry point for the Watchtower intelligence platform.
Supports multiple execution modes:
- Development: Hot reload, debug logging
- Production: Containerized deployment
- ETL-only: Run ETL processes only
- Dashboard-only: Run dashboard only

Features:
- Intelligent ETL scheduling with parallel execution
- Hot reload for development
- Health monitoring and automatic recovery
- Cross-platform service management
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    from .health_monitor import HealthMonitor
except ImportError:
    try:
        # Handle case when run as script from src/launcher directory
        from health_monitor import HealthMonitor
    except ImportError:
        # Handle case when run from project root
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from health_monitor import HealthMonitor


class ExecutionMode(Enum):
    """Execution modes for the launcher."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    ETL_ONLY = "etl_only"
    DASHBOARD_ONLY = "dashboard_only"


@dataclass
class ProcessInfo:
    """Information about a running process."""

    name: str
    process: psutil.Process
    start_time: float
    last_health_check: float = field(default_factory=time.time)
    restart_count: int = 0
    max_restarts: int = 3

    def is_alive(self) -> bool:
        """Check if process is still running."""
        try:
            return self.process.is_running() and self.process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def should_restart(self) -> bool:
        """Check if process should be restarted."""
        return not self.is_alive() and self.restart_count < self.max_restarts


class ETLScheduler:
    """Intelligent ETL scheduler with parallel execution and monitoring."""

    def __init__(self, config: dict):
        self.config = config
        self.etl_processes: dict[str, ProcessInfo] = {}
        self.running = False
        self.logger = logging.getLogger("ETLScheduler")

        # ETL categories for parallel execution
        self.etl_categories = {
            "news": [
                "src/etl/news/news_get_ycombinator.py",
                "src/etl/news/news_get_futuretools.py",
                "src/etl/news/news_get_genai_medium.py",
                "src/etl/news/news_get_kdnuggets.py",
                "src/etl/news/news_get_bensbites.py",
                "src/etl/news/news_get_planesvalencia.py",
                "src/etl/news/valencia_events_etl.py",
                "src/etl/news/news_get_gooddevs.py",
                "src/etl/news/news_get_podcasts.py",
                "src/etl/news/news_get_newsapi.py",
                "src/etl/news/news_get_producthunt.py",
                "src/etl/news/news_get_indiehackers.py",
                "src/etl/news/news_get_gittrends.py",
                "src/etl/github/github_trending_rss_etl.py",
                "src/etl/news/news_get_hackernews_ask.py",
                "src/etl/news/news_get_stackoverflow_trends.py",
                "src/etl/news/news_get_media_rss.py",
                "src/etl/news/news_get_meneame.py",
                "src/etl/news/news_get_kagi.py",
                "src/etl/news/news_get_devto.py",
                "src/etl/news/news_get_techcrunch.py",
                "src/etl/news/news_get_venturebeat.py",
                "src/etl/news/news_get_freecodecamp.py",
                "src/etl/news/news_get_google_ai_blog.py",
                "src/etl/news/news_get_lobsters.py",
                "src/etl/news/news_get_arstechnica.py",
            ],
            "reddit": [
                "src/etl/news/reddit_unified_etl.py",
                "src/etl/giveaways/reddit_giveaways_etl.py",
            ],
            "deals": [
                "src/etl/deals/run_all_deals.py",
                "src/etl/deals/slickdeals_etl.py",
                "src/etl/deals/woot_etl.py",
                "src/etl/deals/isthereanydeal_rss_etl.py",
            ],
            "courses": [
                "src/etl/goldigging/goldigging_coursera_courses.py",
                "src/etl/goldigging/goldigging_pluralsight_courses.py",
                "src/etl/goldigging/goldigging_youtube_posts.py",
                "src/etl/goldigging/goldigging_scavenging_etl.py",
                "src/etl/goldigging/goldigging_deeplearningai_courses.py",
                "src/etl/goldigging/gumroad_scraper_etl.py",
                "src/etl/courses/ms_applied_skills_etl.py",
                "src/etl/courses/khan_academy_etl.py",
            ],
            "research": [
                "src/etl/arxiv/arxiv_etl.py",
            ],
            "entertainment": [
                "src/etl/anime/mal_etl.py",
                "src/etl/entertainment/trakt_trending_etl.py",
                "src/etl/entertainment/spotify_browse_etl.py",
            ],
            "ai_platforms": [
                "src/etl/ai_platforms/papers_with_code_etl.py",
                "src/etl/ai_platforms/replicate_models_etl.py",
                "src/etl/ai_platforms/replicate_explore_playwright_etl.py",
            ],
            "intelligence": [
                "src/etl/intelligence/sec_edgar_rss.py",
                "src/etl/intelligence/who_outbreaks_rss.py",
            ],
            "games": [
                "src/etl/games/games_get_deals.py",
                "src/etl/games/games_get_humblebundles.py",
                "src/etl/games/games_get_new_releases.py",
                "src/etl/games/games_get_itchio_trending.py",
                "src/etl/games/games_get_epic_free.py",
                "src/etl/games/enhanced_free_games_etl.py",
                "src/etl/games/games_get_gog_rss.py",
                "src/etl/games/games_get_isthereanydeal_api.py",
                "src/etl/games/games_get_metacritic_rss.py",
                "src/etl/games/games_get_giantbomb.py",
            ],
            "watchers": [
                "src/watchers/ms_skills_watcher.py",
            ],
            "media": [
                "src/etl/youtube_shorts_ocr_etl.py",
            ],
            "public_aid": [
                "src/etl/spanish_public_aid/spanish_public_aid_etl.py",
            ],
            "community": [
                "src/etl/fourchan/fourchan_generals_etl.py",
            ],
        }

    def _start_etl_process(self, script_path: str, category: str) -> ProcessInfo | None:
        """Start a single ETL process."""
        try:
            if not os.path.exists(script_path):
                self.logger.warning(f"ETL script not found: {script_path}")
                return None

            # Use uv run for consistent environment
            cmd = [sys.executable, "-m", "uv", "run", "python", script_path]

            process = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())

            process_info = ProcessInfo(
                name=f"{category}_{os.path.basename(script_path)}",
                process=process,
                start_time=time.time(),
            )

            self.etl_processes[process_info.name] = process_info
            self.logger.info(f"Started ETL process: {process_info.name}")

            return process_info

        except Exception as e:
            self.logger.error(f"Failed to start ETL process {script_path}: {e}")
            return None

    async def start_category_processes(self, category: str) -> list[ProcessInfo]:
        """Start all ETL processes for a category."""
        processes = []
        for script_path in self.etl_categories.get(category, []):
            process_info = self._start_etl_process(script_path, category)
            if process_info:
                processes.append(process_info)

        return processes

    async def start_all_processes(self) -> dict[str, list[ProcessInfo]]:
        """Start all ETL processes organized by category."""
        self.logger.info("Starting all ETL processes...")

        category_processes = {}
        for category in self.etl_categories:
            self.logger.info(f"Starting {category} ETL processes...")
            processes = await self.start_category_processes(category)
            category_processes[category] = processes

            # Small delay between categories to prevent overwhelming the system
            await asyncio.sleep(1)

        return category_processes

    async def monitor_processes(self):
        """Monitor running ETL processes and restart failed ones."""
        while self.running:
            try:
                failed_processes = []

                for name, process_info in list(self.etl_processes.items()):
                    if not process_info.is_alive():
                        if process_info.should_restart():
                            self.logger.warning(f"ETL process {name} died, restarting...")
                            # For now, we'll restart the entire category
                            category = name.split("_")[0]
                            failed_processes.append((name, category))
                        else:
                            self.logger.error(f"ETL process {name} exceeded max restarts, removing")
                            del self.etl_processes[name]

                # Restart failed categories
                for name, category in failed_processes:
                    if category in self.etl_processes:
                        # Remove dead processes from category
                        self.etl_processes[category] = [p for p in self.etl_processes[category] if p.is_alive()]

                    # Restart the category
                    self.logger.info(f"Restarting {category} processes...")
                    new_processes = await self.start_category_processes(category)
                    if category not in self.etl_processes:
                        self.etl_processes[category] = []
                    self.etl_processes[category].extend(new_processes)

            except Exception as e:
                self.logger.error(f"Error in process monitoring: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def shutdown(self):
        """Gracefully shutdown all ETL processes."""
        self.logger.info("Shutting down ETL processes...")
        self.running = False

        for name, process_info in self.etl_processes.items():
            try:
                if process_info.is_alive():
                    self.logger.info(f"Terminating process {name}")
                    process_info.process.terminate()

                    # Give it 10 seconds to terminate gracefully
                    try:
                        process_info.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Force killing process {name}")
                        process_info.process.kill()
            except Exception as e:
                self.logger.error(f"Error terminating process {name}: {e}")

        self.etl_processes.clear()


class HotReloadHandler(FileSystemEventHandler):
    """File system event handler for hot reload."""

    def __init__(self, callback):
        self.callback = callback
        self.last_reload = 0

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only reload Python files
        if event.src_path.endswith(".py"):
            current_time = time.time()
            # Debounce rapid changes
            if current_time - self.last_reload > 2:
                self.last_reload = current_time
                self.callback(event.src_path)


class WatchtowerLauncher:
    """Main launcher class for Watchtower platform."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.DEVELOPMENT):
        self.mode = mode
        self.etl_scheduler: ETLScheduler | None = None
        self.dashboard_process: ProcessInfo | None = None
        self.hot_reload_observer: Observer | None = None
        self.health_monitor: HealthMonitor | None = None
        self.running = False

        # Configuration
        self.config = {
            "etl_interval": int(os.getenv("WATCHTOWER_ETL_INTERVAL", "3600")),
            "dashboard_port": int(os.getenv("WATCHTOWER_DASHBOARD_PORT", "7777")),
            "log_level": os.getenv("WATCHTOWER_LOG_LEVEL", "INFO"),
            "hot_reload": os.getenv("WATCHTOWER_HOT_RELOAD", "false").lower() == "true",
        }

        # Setup logging after config is set
        self.setup_logging()

        self.logger = logging.getLogger("WatchtowerLauncher")
        # Test hot reload functionality

    def setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config["log_level"].upper())

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("logs/launcher.log"),
            ],
        )

    async def start_dashboard(self) -> ProcessInfo:
        """Start the dashboard process."""
        self.logger.info("Starting Watchtower Dashboard...")

        try:
            # Use uv run for consistent environment
            cmd = [
                sys.executable,
                "-m",
                "uv",
                "run",
                "python",
                "run_watchtower_dashboard.py",
            ]

            process = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())

            process_info = ProcessInfo(name="watchtower_dashboard", process=process, start_time=time.time())

            self.logger.info(f"Dashboard started with PID {process.pid}")
            return process_info

        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            raise

    async def start_etl_scheduler(self) -> ETLScheduler:
        """Start the ETL scheduler."""
        self.logger.info("Starting ETL Scheduler...")

        scheduler = ETLScheduler(self.config)

        # Start process monitoring in background
        asyncio.create_task(scheduler.monitor_processes())

        # Start all ETL processes
        await scheduler.start_all_processes()

        return scheduler

    async def start_health_monitor(self) -> HealthMonitor:
        """Start the health monitor."""
        self.logger.info("Starting Health Monitor...")

        monitor = HealthMonitor(self.config)

        # Start monitoring loop in background
        asyncio.create_task(monitor.run_monitoring_loop(self.etl_scheduler))

        return monitor

    def setup_hot_reload(self):
        """Setup hot reload for development mode."""
        if not self.config["hot_reload"] or self.mode != ExecutionMode.DEVELOPMENT:
            return

        def on_file_change(file_path):
            self.logger.info(f"File changed: {file_path}, triggering reload...")
            # For now, just log the change
            # In a full implementation, this would restart relevant processes
            pass

        event_handler = HotReloadHandler(on_file_change)
        self.hot_reload_observer = Observer()
        self.hot_reload_observer.schedule(event_handler, "src", recursive=True)
        self.hot_reload_observer.start()

        self.logger.info("Hot reload enabled for development mode")

    async def run(self):
        """Main run loop."""
        self.logger.info(f"Starting Watchtower in {self.mode.value} mode")
        self.running = True

        try:
            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGINT, self.signal_handler)

            # Setup hot reload if enabled
            self.setup_hot_reload()

            # Start dashboard if not ETL-only mode
            if self.mode not in [ExecutionMode.ETL_ONLY]:
                self.dashboard_process = await self.start_dashboard()

            # Start ETL scheduler if not dashboard-only mode
            if self.mode not in [ExecutionMode.DASHBOARD_ONLY]:
                self.etl_scheduler = await self.start_etl_scheduler()

            # Start health monitor
            self.health_monitor = await self.start_health_monitor()

            # Main monitoring loop
            last_etl_run = 0

            while self.running:
                current_time = time.time()

                # Run ETL processes periodically (if not in continuous mode)
                if self.etl_scheduler and current_time - last_etl_run > self.config["etl_interval"]:
                    self.logger.info("Running scheduled ETL processes...")
                    await self.etl_scheduler.start_all_processes()
                    last_etl_run = current_time

                # Health monitoring is handled by the health monitor itself
                # We just need to keep the main loop running

                await asyncio.sleep(10)  # Main loop sleep

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown all processes."""
        self.logger.info("Shutting down Watchtower...")
        self.running = False

        # Stop hot reload observer
        if self.hot_reload_observer:
            self.hot_reload_observer.stop()
            self.hot_reload_observer.join()

        # Shutdown health monitor
        if self.health_monitor:
            self.health_monitor.running = False

        # Shutdown ETL scheduler
        if self.etl_scheduler:
            await self.etl_scheduler.shutdown()

        # Shutdown dashboard
        if self.dashboard_process and self.dashboard_process.is_alive():
            self.logger.info("Terminating dashboard process...")
            try:
                self.dashboard_process.process.terminate()
                self.dashboard_process.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.dashboard_process.process.kill()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Watchtower Unified Launcher")
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.value for mode in ExecutionMode],
        default=ExecutionMode.DEVELOPMENT.value,
        help="Execution mode",
    )

    args = parser.parse_args()

    # Determine mode from environment if not specified
    mode_str = os.getenv("WATCHTOWER_MODE", args.mode)
    mode = ExecutionMode(mode_str)

    # Create and run launcher
    launcher = WatchtowerLauncher(mode)

    try:
        asyncio.run(launcher.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
