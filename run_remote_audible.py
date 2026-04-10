import os
import paramiko
from dotenv import load_dotenv

load_dotenv()
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

if not SERVER_IP or not PASSWORD:
    print("Cannot find UNRAID credentials.")
    exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)

print("Connected to Unraid. Running Audible ETL inside Watchtower container...")
stdin, stdout, stderr = ssh.exec_command("docker exec watchtower uv run python src/etl/goldigging/audible_releases_etl.py")

for line in stdout:
    print(line.strip())
for line in stderr:
    print(line.strip())

ssh.close()
print("Done!")
