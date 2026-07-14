"""Verify REST API Endpoints."""

import json
import sys
import time

import requests

BASE_URL = "http://localhost:7777/api"
API_KEY = "watchtower-dev-key"


def print_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name} {details}")
    if not passed:
        sys.exit(1)


def wait_for_server():
    print("Waiting for server...")
    for _ in range(10):
        try:
            requests.get(f"{BASE_URL}/status")
            return True
        except:
            time.sleep(2)
    return False


def verify_api():
    if not wait_for_server():
        print("Server not up. Please ensure dashboard is running.")
        sys.exit(1)

    # 1. Health Check
    try:
        r = requests.get(f"{BASE_URL}/status")
        print_result("Health Check", r.status_code == 200, r.text)
    except Exception as e:
        print_result("Health Check", False, str(e))

    # 2. Auth Fail (No Key)
    try:
        r = requests.get(f"{BASE_URL}/sources")
        print_result("Auth Enforced (No Key)", r.status_code == 401, f"Got {r.status_code}")
    except Exception as e:
        print_result("Auth Enforced", False, str(e))

    # 3. Auth Fail (Bad Key)
    try:
        r = requests.get(f"{BASE_URL}/sources", headers={"X-API-Key": "wrong-key"})
        print_result("Auth Enforced (Bad Key)", r.status_code == 401, f"Got {r.status_code}")
    except Exception as e:
        print_result("Auth Enforced", False, str(e))

    # 4. List Sources (Success)
    try:
        r = requests.get(f"{BASE_URL}/sources", headers={"X-API-Key": API_KEY})
        data = r.json()
        print_result("List Sources", r.status_code == 200 and "sources" in data, f"Found {data.get('count', 0)} sources")
    except Exception as e:
        print_result("List Sources", False, str(e))

    # 5. Get Data (Success)
    # Using 'language_trends' as it was just created
    source = "language_trends"
    try:
        r = requests.get(f"{BASE_URL}/data/{source}", headers={"X-API-Key": API_KEY})
        if r.status_code == 404:
            print(f"⚠️ Source {source} not found, trying job_market")
            source = "job_market"
            r = requests.get(f"{BASE_URL}/data/{source}", headers={"X-API-Key": API_KEY})

        data = r.json()
        print_result(f"Get Data ({source})", r.status_code == 200 and "data" in data, f"Timestamp: {data.get('timestamp')}")
    except Exception as e:
        print_result("Get Data", False, str(e))


if __name__ == "__main__":
    verify_api()
