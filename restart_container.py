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
    print(f"Connecting to {SERVER_IP} with 30s timeout...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=30)
    
    print("Connected. Stopping/removing watchtower container to free resources...")
    # Stop container forcefully if needed
    cmd = "docker rm -f watchtower"
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:", out.strip())
    print("STDERR:", err.strip())
    
    print("Starting watchtower container...")
    start_cmd = (
        "docker run -d --name watchtower --restart unless-stopped "
        "-p 7777:7780 -p 45714:45714 "
        "-v /mnt/user/appdata/watchtower/data:/app/data "
        "-v /mnt/user/appdata/watchtower/logs:/app/logs "
        "-e TZ=Europe/Madrid -e BROWSERLESS_ENDPOINT=ws://192.168.31.126:3000 watchtower"
    )
    stdin, stdout, stderr = ssh.exec_command(start_cmd, timeout=60)
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:", out.strip())
    print("STDERR:", err.strip())
    
    print("Done")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
