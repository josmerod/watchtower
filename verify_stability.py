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
    print(f"Connecting to {SERVER_IP} for stability check...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    
    commands = [
        "uptime",
        "free -h",
        "ps aux --sort=-%mem | head -n 10",
        "docker stats --no-stream watchtower browserless 2>/dev/null || echo 'Could not fetch docker stats'",
        "cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|Inactive\\(anon\\)'"
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd} ---")
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            print(stdout.read().decode('utf-8').strip())
            err = stderr.read().decode('utf-8').strip()
            if err: print("STDERR:", err)
        except Exception as ex:
            print(f"Timeout/Error: {ex}")
            
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
