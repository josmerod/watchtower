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
        # Kill all docker builds
        "pkill -9 -f 'docker build'",
        "pkill -9 -f 'buildx'",
        
        # Kill any python processes matching /app/.venv to stop running orchestrators
        "pkill -9 -f '/app/.venv/bin/python'",
        
        # Check free memory
        "free -h",
        
        # Run top 10 memory consumers
        "ps aux --sort=-%mem | head -n 11"
    ]
    
    for cmd in commands:
        print(f"--- {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        out = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        if out: print(out)
        if err: print("STDERR:", err)
        
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
