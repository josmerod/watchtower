import os
import sys
import time
import subprocess

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import centralized logging utility
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories

logger = get_logger("GenAI_Orchestrator")


def ensure_genai_directories():
    """Ensure required directories exist."""
    directories = ["data/futurenews", "logs"]
    ensure_directories(directories)
    logger.info(f"Verified required directories exist: {', '.join(directories)}")


def run_futuretools_etl():
    """Run the futuretools ETL process."""
    try:
        logger.info("Starting futuretools ETL process...")
        start_time = time.time()

        # Get the absolute path to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        # Build the absolute path to the ETL script
        etl_script_path = os.path.join(
            project_root, "src", "etl", "news", "news_get_futuretools.py"
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
            f"Futuretools ETL process completed successfully in {execution_time:.2f} seconds"
        )

        return True
    except Exception as e:
        logger.error(f"Unexpected error running futuretools ETL: {str(e)}", exc_info=True)
        return False


def main():
    """Main orchestrator function - Runs the ETL task once."""
    logger.info("Starting GenAI Orchestrator Task (single run)")
    ensure_genai_directories()

    success = run_futuretools_etl()

    if success:
        logger.info("GenAI Orchestrator Task completed successfully.")
        sys.exit(0)
    else:
        logger.error("GenAI Orchestrator Task failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
