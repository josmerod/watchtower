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
        # Kill the hanging docker build
        "pkill -9 -f 'docker build'",
        "pkill -9 -f 'buildx'",
        
        # Kill python processes consuming too much memory
        "for pid in $(ps aux --sort=-%mem | awk 'NR<=10 {if($4>10 || $3>50) print $2}'); do kill -9 $pid 2>/dev/null; done",
        
        # In case watchtower didn't cleanly go down
        "docker rm -f watchtower 2>/dev/null",
        
        # Kill runaway chromium/playwright instances if any
        "pkill -9 -f chromium",
        "pkill -9 -f chrome",
        
        # Get free memory now
        "free -h",
        
        # Get top processes
        "ps aux --sort=-%mem | head -n 10"
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
