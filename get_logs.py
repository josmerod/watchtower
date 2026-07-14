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
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)

    commands = ["free -m", "docker stats --no-stream watchtower"]

    with open("remote_logs.txt", "w") as f:
        for cmd in commands:
            f.write(f"--- {cmd} ---\n")
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
            out = stdout.read().decode("utf-8")
            err = stderr.read().decode("utf-8")
            f.write(out + "\n")
            if err:
                f.write("STDERR: " + err + "\n")
    print("Done")
except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
