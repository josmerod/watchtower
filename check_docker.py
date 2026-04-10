import os
import paramiko
import sys
from dotenv import load_dotenv

load_dotenv()
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)
commands = [
    "echo '\\n--- DOCKER STATS ---'",
    "docker stats --no-stream watchtower",
    "echo '\\n--- SYSTEM TOP ---'",
    "top -b -n 1 | head -n 20",
]
stdin, stdout, stderr = ssh.exec_command(" && ".join(commands))
exit_status = stdout.channel.recv_exit_status()

with open("remote_logs.txt", "w", encoding="utf-8") as f:
    f.write("STDOUT:\n")
    f.write(stdout.read().decode())
    f.write("\nSTDERR:\n")
    f.write(stderr.read().decode())
ssh.close()
