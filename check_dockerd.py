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
    print(f"Connecting to {SERVER_IP} to check docker...")
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    
    stdin, stdout, stderr = ssh.exec_command("docker info")
    print("STDOUT:")
    print(stdout.read().decode('utf-8'))
    print("STDERR:")
    print(stderr.read().decode('utf-8'))
    print("EXIT CODE:", stdout.channel.recv_exit_status())
    
    stdin, stdout, stderr = ssh.exec_command("/etc/rc.d/rc.docker status")
    print("STATUS STDOUT:")
    print(stdout.read().decode('utf-8'))

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    ssh.close()
