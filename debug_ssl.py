import requests
import certifi
import ssl
import sys

print(f"Python version: {sys.version}")
print(f"Certifi location: {certifi.where()}")
print(f"Default verify location: {ssl.get_default_verify_paths()}")

try:
    print("Testing connection to google.com...")
    requests.get("https://google.com")
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("Testing connection to mshibanami.github.io (GitHub Trending)...")
    requests.get("https://mshibanami.github.io")
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
