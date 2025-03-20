import os
import sys
import time
import subprocess
import threading
import signal

""" 
This script is used to run all the orchestrator scripts in parallel.
It will start all the orchestrator scripts except the meta orchestrator.
It will also monitor the orchestrator scripts and restart them if they exit.
It will also log the output of the orchestrator scripts.
"""


# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import centralized logging utility
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories

logger = get_logger("Meta_Orchestrator")

# Global flag to control orchestrator processes
running = True


def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down all processes."""
    global running
    logger.info("Received termination signal. Shutting down all orchestrators...")
    running = False


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def ensure_meta_directories():
    """Ensure required directories exist."""
    directories = ["logs"]
    ensure_directories(directories)
    logger.info(f"Verified required directories exist: {', '.join(directories)}")


def find_orchestrator_scripts():
    """Find all orchestrator scripts except the meta orchestrator."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    orchestrator_files = []

    for file in os.listdir(current_dir):
        if file.endswith("_orchestrator.py") and file != "meta_orchestrator.py":
            orchestrator_files.append(os.path.join(current_dir, file))

    logger.info(
        f"Found {len(orchestrator_files)} orchestrator scripts: {[os.path.basename(f) for f in orchestrator_files]}"
    )
    return orchestrator_files


def run_orchestrator(script_path):
    """Run an orchestrator script as a subprocess."""
    script_name = os.path.basename(script_path)
    logger.info(f"Starting orchestrator: {script_name}")

    # Get the absolute path to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        logger.info(f"Started {script_name} with PID {process.pid}")

        # Monitor the process while the main program is running
        while running:
            # Check if process is still alive
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(
                    f"{script_name} exited unexpectedly with code {process.returncode}"
                )
                if stderr:
                    logger.error(f"{script_name} error output: {stderr}")
                if stdout:
                    logger.info(f"{script_name} output: {stdout}")

                # Restart the process if we're still running
                if running:
                    logger.info(f"Restarting {script_name}...")
                    process = subprocess.Popen(
                        [sys.executable, script_path],
                        cwd=project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                    )
                    logger.info(f"Restarted {script_name} with PID {process.pid}")

            time.sleep(5)

        # If we're exiting, terminate the process
        logger.info(f"Terminating {script_name} (PID {process.pid})")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning(f"{script_name} did not terminate gracefully, forcing kill")
            process.kill()

        stdout, stderr = process.communicate()
        if stderr:
            logger.warning(f"{script_name} final error output: {stderr}")

    except Exception as e:
        logger.error(f"Error running {script_name}: {str(e)}")


def main():
    global running
    logger.info("Starting Meta Orchestrator")

    # Ensure required directories exist
    ensure_meta_directories()

    # Find all orchestrator scripts
    orchestrator_scripts = find_orchestrator_scripts()

    if not orchestrator_scripts:
        logger.warning("No orchestrator scripts found. Nothing to run.")
        return

    # Start each orchestrator in its own thread
    threads = []
    for script in orchestrator_scripts:
        thread = threading.Thread(target=run_orchestrator, args=(script,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
        logger.info(f"Started thread for {os.path.basename(script)}")

    # Keep the main thread running
    logger.info("All orchestrators started. Meta Orchestrator is now monitoring...")
    try:
        while running and any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        running = False

    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=30)

    logger.info("Meta Orchestrator shutdown complete")


if __name__ == "__main__":
    main()
