"""Command-line interface for running web content watchers.

This script allows users to list available watchers, run specific watchers,
or run all available watchers. Watchers can be run once or continuously
at specified intervals.
"""

import argparse
from typing import List, Optional

# Add the project root to the path to ensure imports work correctly
from src.utils.logging import get_logger
from src.watchers.ms_skills_watcher import MSAppliedSkillsWatcher

# Initialize logger
logger = get_logger("WatcherRunner")


def list_available_watchers() -> List[str]:
    """
    List all available watchers in the system.

    Returns:
        List[str]: List of watcher names
    """
    return ["ms_applied_skills"]


def get_watcher_instance(watcher_name: str, check_interval: int = 3600):
    """
    Get an instance of the specified watcher.

    Args:
        watcher_name (str): Name of the watcher to instantiate
        check_interval (int): Time in seconds between checks

    Returns:
        Watcher instance or None if not found
    """
    if watcher_name == "ms_applied_skills":
        return MSAppliedSkillsWatcher(check_interval=check_interval)

    logger.error(f"Unknown watcher: {watcher_name}")
    return None


def run_watcher(
    watcher_name: str,
    continuous: bool,
    max_runs: Optional[int] = None,
    check_interval: int = 3600,
):
    """
    Run a specific watcher.

    Args:
        watcher_name (str): Name of the watcher to run
        continuous (bool): Whether to run continuously
        max_runs (int, optional): Maximum number of runs if not continuous
        check_interval (int): Time in seconds between checks
    """
    logger.info(f"Initializing watcher: {watcher_name}")

    watcher = get_watcher_instance(watcher_name, check_interval)
    if watcher:
        logger.info(f"Starting watcher: {watcher_name}")
        watcher.run(continuous=continuous, max_runs=max_runs)
    else:
        logger.error(f"Failed to initialize watcher: {watcher_name}")


def main():
    """Main function to parse arguments and run watchers."""
    parser = argparse.ArgumentParser(description="Run web page watchers")

    parser.add_argument(
        "watcher",
        nargs="?",
        choices=list_available_watchers() + ["all"],
        default="all",
        help="Watcher to run (default: all)",
    )

    parser.add_argument(
        "-o",
        "--once",
        action="store_true",
        help="Run watcher(s) once and exit",
    )

    parser.add_argument(
        "-n",
        "--num-runs",
        type=int,
        default=None,
        help="Number of times to run the watcher before exiting",
    )

    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=3600,
        help="Check interval in seconds (default: 3600)",
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List available watchers and exit",
    )

    args = parser.parse_args()

    if args.list:
        print("Available watchers:")
        for watcher in list_available_watchers():
            print(f"  - {watcher}")
        return

    continuous = not args.once
    max_runs = args.num_runs

    if args.watcher == "all":
        logger.info("Running all watchers")
        for watcher_name in list_available_watchers():
            run_watcher(watcher_name, continuous, max_runs, args.interval)
    else:
        run_watcher(args.watcher, continuous, max_runs, args.interval)


if __name__ == "__main__":
    logger.info("Watcher runner script started")
    main()
    logger.info("Watcher runner script completed")
