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

def force_restart():
    print(f"[{datetime.datetime.now()}] Connecting to {SERVER_IP}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)
        
        # 1. Check Data Freshness BEFORE restart to diagnose
        print("\n--- Checking Remote Data Freshness (TechCrunch) ---")
        cmd_check = "stat -c '%y' /mnt/user/appdata/watchtower/data/news/techcrunch_latest.json"
        stdin, stdout, stderr = ssh.exec_command(cmd_check)
        ts = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if ts:
            print(f"Remote File Timestamp: {ts}")
        else:
            print(f"Could not stat file: {err}")
            # Try to list the directory to see what's there
            stdin, stdout, stderr = ssh.exec_command("ls -l /mnt/user/appdata/watchtower/data/news/")
            print("Directory listing:")
            print(stdout.read().decode())

        # 2. Restart Container
        print("\n--- Restarting Watchtower Container ---")
        stdin, stdout, stderr = ssh.exec_command("docker restart watchtower")
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code == 0:
            print("Container restart command execution: SUCCESS")
            print(stdout.read().decode())
        else:
            print("Container restart command execution: FAILED")
            print("STDERR:", stderr.read().decode())

        # 3. Verify it's up
        print("\n--- Verifying Container Status ---")
        stdin, stdout, stderr = ssh.exec_command("docker ps | grep watchtower")
        print(stdout.read().decode())

        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    force_restart()
