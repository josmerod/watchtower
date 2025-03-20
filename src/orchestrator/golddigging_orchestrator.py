import os
import sys
import time
import subprocess
import schedule

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import centralized logging utility
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories

logger = get_logger("Golddigging_Orchestrator")


def ensure_golddigging_directories():
    """Ensure required directories exist."""
    directories = ["data/youtube", "logs"]
    ensure_directories(directories)
    logger.info(f"Verified required directories exist: {', '.join(directories)}")


def run_youtube_etl():
    """Run the YouTube ETL process."""
    try:
        logger.info("Starting YouTube ETL process...")
        start_time = time.time()

        # Get the absolute path to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        # Build the absolute path to the ETL script
        etl_script_path = os.path.join(
            project_root, "src", "etl", "goldigging", "goldigging_youtube_posts.py"
        )

        # Verify the script exists before running
        if not os.path.exists(etl_script_path):
            logger.error(f"ETL script not found at: {etl_script_path}")
            return False

        logger.info(f"Running ETL script: {etl_script_path}")

        # Run the ETL script as a module to avoid path issues
        result = subprocess.run(
            [sys.executable, etl_script_path],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Check if the process was successful
        if result.returncode != 0:
            logger.error(f"ETL process failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False

        # Log the output
        if result.stdout:
            logger.info(f"ETL Output: {result.stdout}")

        execution_time = time.time() - start_time
        logger.info(
            f"YouTube ETL process completed successfully in {execution_time:.2f} seconds"
        )

        return True
    except Exception as e:
        logger.error(f"Unexpected error running YouTube ETL: {str(e)}")
        return False


def main():
    """Main orchestrator function."""
    logger.info("Starting Golddigging Orchestrator")

    # Ensure required directories exist
    ensure_golddigging_directories()

    # Schedule the ETL job to run every 6 hours
    schedule.every(6).hours.do(run_youtube_etl)

    # Run immediately on startup
    logger.info("Running initial ETL job...")
    run_youtube_etl()

    # Keep the script running and execute scheduled jobs
    logger.info("Orchestrator running. Waiting for scheduled jobs...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check for pending jobs every minute


if __name__ == "__main__":
    main()
