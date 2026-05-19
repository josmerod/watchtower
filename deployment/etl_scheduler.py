import time
import subprocess
import sys
import datetime
import os

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
        result = subprocess.run(
            ["bash", script_path],
            check=False, # Don't crash scheduler on ETL failure
            capture_output=True,
            text=True
        )
        
        # Log output
        print(f"[{datetime.datetime.now()}] ETL Execution Finished.")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"Warning: ETL script returned non-zero exit code: {result.returncode}")

        # Restart only the API server to pick up fresh ETL data from disk.
        # The dashboard reads from the API, so it auto-refreshes.
        # Do NOT restart the dashboard itself — that disrupts active users.
        try:
            subprocess.run(["supervisorctl", "restart", "api"], capture_output=True, text=True, timeout=30)
            print("API server restarted to load fresh data.")
        except Exception as e:
            print(f"Warning: Could not restart API server: {e}")

    except Exception as e:
        print(f"Error running ETL script: {e}")

def main():
    print(f"[{datetime.datetime.now()}] ETL Scheduler started. Interval: 2 hours.")
    
    # Run immediately on start? 
    # Maybe wait a bit to let dashboard start, or just run. 
    # Let's run immediately to ensure fresh data on deploy.
    run_etls()
    
    while True:
        # Sleep for 2 hours (2 * 3600 seconds)
        time.sleep(2 * 3600)
        run_etls()

if __name__ == "__main__":
    main()
