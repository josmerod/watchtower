import os
import paramiko
from dotenv import load_dotenv
import sys

load_dotenv()

SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

if not SERVER_IP or not PASSWORD:
    print("Error: UNRAID_HOST and UNRAID_PASSWORD must be set in .env file")
    sys.exit(1)

def check_logs():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)
        
        # 3. Check Specific Failing ETLs
        log_files = [
            "news_get_ycombinator.log",
            "opensource_projects_etl.log", 
            "news_get_gittrends.log",
            "news_get_hackernews_ask.log"
        ]
        
        for log_file in log_files:
            print(f"\n--- Checking {log_file} (Last 50 lines) ---")
            cmd = f"tail -n 50 /mnt/user/appdata/watchtower/logs/{log_file}"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            content = stdout.read().decode()
            if content:
                print(content)
            else:
                print(f"Log file '{log_file}' empty or not found.")
                
            print(f"--- Grepping for errors in {log_file} ---")
            cmd = f"grep -i 'error' /mnt/user/appdata/watchtower/logs/{log_file} | tail -n 5"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            print(stdout.read().decode())
    
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_logs()
