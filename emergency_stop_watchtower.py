import os
import paramiko
from dotenv import load_dotenv

load_dotenv()
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print(f"Connecting to {SERVER_IP}...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    
    commands = [
        "docker rm -f watchtower 2>/dev/null",
        "pkill -9 -f '/app/.venv/bin/python'",
        "pkill -9 -f yt-dlp",
        "pkill -9 -f playwright",
        "pkill -9 -f chromium",
        "free -h"
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd} ---")
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            print(stdout.read().decode('utf-8').strip())
        except Exception as ex:
            print(f"Timeout/Error running {cmd}: {ex}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
