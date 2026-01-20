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
        
        # Restart Dashboard to load fresh data
        print(f"[{datetime.datetime.now()}] Restarting Dashboard to refresh data...")
        restart_result = subprocess.run(
            ["supervisorctl", "restart", "dashboard"],
            capture_output=True,
            text=True
        )
        if restart_result.returncode == 0:
             print("Dashboard restarted successfully.")
        else:
             print(f"Error restarting dashboard: {restart_result.stderr}")
            
    except Exception as e:
        print(f"Error running ETL script: {e}")

def main():
    print(f"[{datetime.datetime.now()}] ETL Scheduler started. Interval: 4 hours.")
    
    # Run immediately on start? 
    # Maybe wait a bit to let dashboard start, or just run. 
    # Let's run immediately to ensure fresh data on deploy.
    run_etls()
    
    while True:
        # Sleep for 4 hours (4 * 3600 seconds)
        time.sleep(4 * 3600)
        run_etls()

if __name__ == "__main__":
    main()
