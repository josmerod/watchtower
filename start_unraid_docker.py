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
    print(f"Connecting to {SERVER_IP} to start docker...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    
    print("Starting Unraid Docker service...")
    stdin, stdout, stderr = ssh.exec_command("/etc/rc.d/rc.docker start", timeout=300)
    print("STDOUT:")
    print(stdout.read().decode('utf-8'))
    print("STDERR:")
    print(stderr.read().decode('utf-8'))
    
    print("Checking docker info...")
    stdin, stdout, stderr = ssh.exec_command("docker info > /dev/null 2>&1")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 0:
        print("Docker is successfully started.")
    else:
        print("Docker is still not running. Exit code:", exit_code)

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
