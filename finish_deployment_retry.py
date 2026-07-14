import os
import sys
import time

import paramiko
from dotenv import load_dotenv

load_dotenv()
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print(f"Connecting to {SERVER_IP} to finalize deploy...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)

    REMOTE_DIR = "/tmp/watchtower_deploy"
    DOCKER_IMAGE = "watchtower"

    print("Waiting for Docker to be ready...")
    for i in range(30):
        stdin, stdout, stderr = ssh.exec_command("docker info > /dev/null 2>&1")
        if stdout.channel.recv_exit_status() == 0:
            print("Docker is ready!")
            break
        time.sleep(2)
    else:
        print("Docker failed to become ready.")
        sys.exit(1)

    print("Running docker build...")
    cmd = f"cd {REMOTE_DIR} && docker build -t {DOCKER_IMAGE} -f deployment/Dockerfile ."
    stdin, stdout, stderr = ssh.exec_command(cmd)

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"Build failed with {exit_status}")
        print(stderr.read().decode())
        sys.exit(1)

    print("Build succeeded. Starting container...")
    start_cmd = (
        f"docker rm -f {DOCKER_IMAGE} || true && "
        f"docker run -d --name {DOCKER_IMAGE} --restart unless-stopped "
        f"-p 7777:7780 -p 45714:45714 "
        f"-v /mnt/user/appdata/watchtower/data:/app/data "
        f"-v /mnt/user/appdata/watchtower/logs:/app/logs "
        f"-e TZ=Europe/Madrid -e BROWSERLESS_ENDPOINT=ws://REDACTED_LAN_IP:3000 {DOCKER_IMAGE}"
    )
    stdin, stdout, stderr = ssh.exec_command(start_cmd)
    if stdout.channel.recv_exit_status() == 0:
        print("Container started successfully!")
    else:
        print(f"Failed to start container: {stderr.read().decode()}")

except Exception:
    import traceback

    traceback.print_exc()
finally:
    ssh.close()
