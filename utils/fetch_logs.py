import os
import sys

import paramiko
from dotenv import load_dotenv

load_dotenv()

# Configuration — read from environment (see .env.example).
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")
LOG_FILE = "/mnt/user/appdata/watchtower/logs/dashboard.err.log"

if not SERVER_IP or not PASSWORD:
    print("Error: UNRAID_HOST and UNRAID_PASSWORD must be set in .env file")
    sys.exit(1)


def fetch_logs():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)

        print(f"Fetching logs from {LOG_FILE}...")
        stdin, stdout, stderr = ssh.exec_command(f"tail -n 50 {LOG_FILE}")

        print("--- REMOTE LOGS START ---")
        print(stdout.read().decode())
        print(stderr.read().decode())
        print("--- REMOTE LOGS END ---")

        ssh.close()
    except Exception as e:
        print(f"Error fetching logs: {e}")


if __name__ == "__main__":
    fetch_logs()
