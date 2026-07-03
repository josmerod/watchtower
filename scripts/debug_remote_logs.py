import paramiko
import sys

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

if not SERVER_IP or not PASSWORD:
    print("Error: UNRAID_HOST and UNRAID_PASSWORD must be set in .env file")
    sys.exit(1)


def fetch_logs():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)

        print("--- Log Files in /mnt/user/appdata/watchtower/logs ---")
        stdin, stdout, stderr = ssh.exec_command("ls -1 /mnt/user/appdata/watchtower/logs")
        print(stdout.read().decode())

        print("--- Content of scheduler.err.log ---")
        stdin, stdout, stderr = ssh.exec_command("cat /mnt/user/appdata/watchtower/logs/scheduler.err.log | tail -n 50")
        print(stdout.read().decode())

        print("--- Content of scheduler.out.log ---")
        stdin, stdout, stderr = ssh.exec_command("cat /mnt/user/appdata/watchtower/logs/scheduler.out.log | tail -n 50")
        print(stdout.read().decode())

        print("--- Supervisord Log ---")
        stdin, stdout, stderr = ssh.exec_command("cat /mnt/user/appdata/watchtower/logs/supervisord.log | tail -n 20")
        print(stdout.read().decode())

        print("--- Data Directory Timestamps (News) ---")
        stdin, stdout, stderr = ssh.exec_command("ls -lt /mnt/user/appdata/watchtower/data/news/ | head -n 10")
        print(stdout.read().decode())

        ssh.close()
    except Exception as e:
        print(f"Error fetching logs: {e}")

        ssh.close()
    except Exception as e:
        print(f"Error fetching logs: {e}")


if __name__ == "__main__":
    fetch_logs()
