import os
import sys
import tarfile
import time
from datetime import datetime

import paramiko
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SERVER_IP = os.getenv("UNRAID_HOST")
USERNAME = os.getenv("UNRAID_USER", "root")
PASSWORD = os.getenv("UNRAID_PASSWORD")
REMOTE_DIR = "/tmp/watchtower_deploy"
TAR_FILENAME = "watchtower_src.tar.gz"
DOCKER_IMAGE = "watchtower"
# Host port (Unraid) -> Container port (Dash app)
HOST_PORT = "7777"
CONTAINER_PORT = "7780"

if not SERVER_IP:
    print("Error: UNRAID_HOST must be set in .env file")
    sys.exit(1)


def create_archive(output_filename):
    print(f"[{datetime.now()}] Creating source archive: {output_filename}")

    # List of files/folders to include
    include_paths = ["src", "deployment", "config", "utils", "Tests", "pyproject.toml", "uv.lock", "run_all_etl.sh", "run_watchtower_dashboard.py", "README.md", "GEMINI.md", "run_all_etl_orchestrator.py"]

    # Files/folders to exclude explicitly if encountered (though include_paths is safer)

    with tarfile.open(output_filename, "w:gz") as tar:
        for path in include_paths:
            if os.path.exists(path):
                print(f"  Adding {path}...")
                tar.add(path, arcname=path, recursive=True)
            else:
                print(f"  Warning: {path} not found.")


def deploy():
    local_tar_path = os.path.join(os.environ.get("TEMP", "/tmp"), TAR_FILENAME)

    try:
        # 1. Create Archive
        create_archive(local_tar_path)

        # Connect via SSH key auth (or password if set)
        print(f"[{datetime.now()}] Connecting to {SERVER_IP}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {"username": USERNAME, "timeout": 30}
        if PASSWORD:
            connect_kwargs["password"] = PASSWORD
        else:
            connect_kwargs["key_filename"] = os.path.expanduser("~/.ssh/id_ed25519")
        ssh.connect(SERVER_IP, **connect_kwargs)

        # 3. Upload
        print(f"[{datetime.now()}] Uploading archive...")
        sftp = ssh.open_sftp()
        sftp.put(local_tar_path, f"/tmp/{TAR_FILENAME}")
        sftp.close()

        # 4. Execute Remote Build
        commands = [
            f"rm -rf {REMOTE_DIR}",
            f"mkdir -p {REMOTE_DIR}",
            f"tar -xzf /tmp/{TAR_FILENAME} -C {REMOTE_DIR}",
            # Populate data volume if needed (no-clobber to preserve existing data)
            "mkdir -p /mnt/user/appdata/watchtower/data",
            f"if [ -d {REMOTE_DIR}/data ]; then echo 'Seeding data volume...'; cp -rn {REMOTE_DIR}/data/* /mnt/user/appdata/watchtower/data/ || true; fi",
            f"cd {REMOTE_DIR} && docker build -t {DOCKER_IMAGE} -f deployment/Dockerfile .",
            # Force remove to ensure clean slate even if running/stuck
            f"docker rm -f {DOCKER_IMAGE} || true",
            f"docker run -d --name {DOCKER_IMAGE} --restart unless-stopped -p {HOST_PORT}:{CONTAINER_PORT} -p 45714:45714 -v /mnt/user/appdata/watchtower/data:/app/data -v /mnt/user/appdata/watchtower/logs:/app/logs -e TZ=Europe/Madrid -e BROWSERLESS_ENDPOINT=ws://REDACTED_LAN_IP:3000 {DOCKER_IMAGE}",
            f"rm -rf {REMOTE_DIR} /tmp/{TAR_FILENAME}",
        ]

        print(f"[{datetime.now()}] Executing remote commands...")
        full_command = " && ".join(commands)

        _stdin, stdout, stderr = ssh.exec_command(full_command)

        # Stream output
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            print(f"[{datetime.now()}] Deployment Successful!")
            print(stdout.read().decode())
        else:
            print(f"[{datetime.now()}] Deployment FAILED with status {exit_status}")
            print("STDOUT:", stdout.read().decode())
            print("STDERR:", stderr.read().decode())
            sys.exit(1)

        ssh.close()

        # Cleanup local
        if os.path.exists(local_tar_path):
            os.remove(local_tar_path)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    deploy()
