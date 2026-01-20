import paramiko
import sys

# Configuration
SERVER_IP = "192.168.31.126"
USERNAME = "root"
PASSWORD = "Josele1305!" 
LOG_FILE = "/mnt/user/appdata/watchtower/logs/dashboard.err.log"

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
