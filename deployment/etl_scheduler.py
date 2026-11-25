import datetime
import os
import subprocess
import sys
import time


def run_etls():
    """Runs the ETL execution script."""
    print(f"[{datetime.datetime.now()}] Starting ETL execution...")

    # Ensure we are in the right directory or use absolute paths for the script
    # Assuming this script is run from /app as per supervisord config config

    # We use the shell script for Linux environments
    script_path = "./run_all_etl.sh"

    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        return

    try:
        # Run the shell script using subprocess
        # uv run is already handled inside run_all_etl.sh or we assume the environment from supervisord
        result = subprocess.run(["bash", script_path], check=False, capture_output=True, text=True)  # Don't crash scheduler on ETL failure

        # Log output
        print(f"[{datetime.datetime.now()}] ETL Execution Finished.")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        if result.returncode != 0:
            print(f"Warning: ETL script returned non-zero exit code: {result.returncode}")

        # Restart only the API server to pick up fresh ETL data from disk.
        # The dashboard reads the same data files directly, so it needs no restart.
        # Do NOT restart the dashboard itself — that disrupts active users.
        try:
            subprocess.run(["supervisorctl", "restart", "api"], capture_output=True, text=True, timeout=30)
            print("API server restarted to load fresh data.")
        except Exception as e:
            print(f"Warning: Could not restart API server: {e}")

    except Exception as e:
        print(f"Error running ETL script: {e}")


def get_interval() -> int:
    """Return the ETL cycle interval in seconds.

    ``WATCHTOWER_ETL_INTERVAL`` is documented in
    docs/technical/ADVANCED_DEPLOYMENT_GUIDE.md and set by ``src/launcher/cli.py``,
    but the sleep here used to be hardcoded to 2 h, so the variable had no
    effect in the container (T-114). The default keeps today's effective
    cadence; invalid values fall back to it.
    """
    raw = os.getenv("WATCHTOWER_ETL_INTERVAL", "7200")
    try:
        return int(raw)
    except ValueError:
        print(f"Warning: WATCHTOWER_ETL_INTERVAL={raw!r} is not an int; using 7200 s.")
        return 7200


def main():
    interval_s = get_interval()
    print(f"[{datetime.datetime.now()}] ETL Scheduler started. Interval: {interval_s} s.")

    # Run immediately on start?
    # Maybe wait a bit to let dashboard start, or just run.
    # Let's run immediately to ensure fresh data on deploy.
    run_etls()

    while True:
        time.sleep(interval_s)
        run_etls()


if __name__ == "__main__":
    main()
