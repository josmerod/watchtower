import socket
import sys

TARGET = "REDACTED_LAN_IP"
PORTS = [80, 443, 5000, 22222]

print(f"Diagnostics for {TARGET}:")
for port in PORTS:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex((TARGET, port))
    status = "OPEN" if result == 0 else f"CLOSED/FILTERED (Err: {result})"
    print(f"  Port {port}: {status}")
    s.close()
