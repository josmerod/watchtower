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
    print(f"Connecting to {SERVER_IP} to verify Docker and Memory...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    
    commands = [
        "free -h",
        "docker info > /dev/null 2>&1 && echo 'Docker is running' || echo 'Docker is down'",
        "docker ps | grep watchtower || echo 'Watchtower not running'"
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd} ---")
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            print(stdout.read().decode('utf-8').strip())
        except Exception as ex:
            print(f"Timeout/Error: {ex}")
            
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
