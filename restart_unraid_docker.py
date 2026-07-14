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
    print(f"Connecting to {SERVER_IP} to restart Docker...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)

    # 1. Kill any chromium/chrome processes just in case
    ssh.exec_command("pkill -9 -f chrome")
    ssh.exec_command("pkill -9 -f chromium")
    ssh.exec_command("pkill -9 -f playwright")

    # 2. Restart docker service
    print("Restarting Unraid Docker service...")
    stdin, stdout, stderr = ssh.exec_command("/etc/rc.d/rc.docker restart", timeout=120)
    print(stdout.read().decode("utf-8").strip())
    err = stderr.read().decode("utf-8").strip()
    if err:
        print("STDERR:", err)

    # Wait a bit for it to come back up
    import time

    time.sleep(5)

    # 3. Check memory
    print("Checking memory after Docker restart...")
    stdin, stdout, stderr = ssh.exec_command("free -h", timeout=10)
    print(stdout.read().decode("utf-8").strip())

except Exception:
    import traceback

    traceback.print_exc()
finally:
    ssh.close()
