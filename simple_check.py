import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER")
PASSWORD = os.getenv("UNRAID_PASSWORD")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)

# Check BROWSERLESS_ENDPOINT
cmd = "docker exec watchtower env | grep BROWSERLESS_ENDPOINT"
print(f"--- Executing: {cmd} ---")
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

ssh.close()
