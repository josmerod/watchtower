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
    
    cmd = "kill -9 901727"
    print(f"--- {cmd} ---")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    print(stdout.read().decode('utf-8').strip())
    
    # Also find any other python processes in /app/.venv running with huge mem
    cmd2 = "pkill -9 -f 'goldigging_youtube_posts.py'"
    ssh.exec_command(cmd2, timeout=30)
    
    cmd3 = "docker restart watchtower"
    ssh.exec_command(cmd3, timeout=30)
    
    cmd4 = "free -h"
    stdin, stdout, stderr = ssh.exec_command(cmd4, timeout=30)
    print(stdout.read().decode('utf-8').strip())
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
