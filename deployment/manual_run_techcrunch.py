import os
import paramiko
from dotenv import load_dotenv
import sys
import datetime

load_dotenv()

SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

if not SERVER_IP or not PASSWORD:
    print("Error: UNRAID_HOST and UNRAID_PASSWORD must be set in .env file")
    sys.exit(1)

def run_remote_etl():
    print(f"[{datetime.datetime.now()}] Connecting to {SERVER_IP}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)
        
        # Run inside the container
        # We need to find the container ID or name. We know it's 'watchtower' from previous steps.
        
        # Run with redirection to capture clean output
        cmd = "docker exec watchtower bash -c 'uv run python src/etl/news/news_get_techcrunch.py > /tmp/tc_run.log 2>&1; cat /tmp/tc_run.log; ls -l /app/data/news/techcrunch_latest.json'"
        
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Stream output
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("\n--- REMOTE OUTPUT ---")
        print(out)
        print("\n--- REMOTE STDERR (SSH Layer) ---")
        print(err)
        
        exit_code = stdout.channel.recv_exit_status()
        print(f"\nExit Code: {exit_code}")

        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_remote_etl()
