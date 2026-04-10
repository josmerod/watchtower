import os
import paramiko
from dotenv import load_dotenv

load_dotenv()
SERVER_IP = os.getenv('UNRAID_HOST')
USERNAME = os.getenv('UNRAID_USER', 'root')
PASSWORD = os.getenv('UNRAID_PASSWORD')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD)

print('Restarting watchtower container...')
stdin, stdout, stderr = ssh.exec_command('docker restart watchtower')
print(f"STDOUT: {stdout.read().decode()}")
print(f"STDERR: {stderr.read().decode()}")

ssh.close()
