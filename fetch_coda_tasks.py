
import requests
import json
import os

# Configuration
API_KEY = "d483f282-b35a-4eaf-a5fa-ff47e9620942"
BASE_URL = "https://coda.io/apis/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def list_docs():
    response = requests.get(f"{BASE_URL}/docs", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def list_tables(doc_id):
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def list_rows(doc_id, table_id):
    rows = []
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    while url:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            rows.extend(data.get("items", []))
            if data.get("nextPageToken"):
                url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows?pageToken={data['nextPageToken']}"
            else:
                url = None
        else:
            print(f"Error fetching rows: {response.text}")
            break
    return rows

def main():
    print("Fetching tasks from Coda...")
    docs = list_docs()
    target_doc = next((d for d in docs if d["name"] == "Watchtower Project Tracking"), None)
    
    if not target_doc:
        print("Doc 'Watchtower Project Tracking' not found.")
        return

    print(f"Found Doc: {target_doc['name']}")
    
    tables = list_tables(target_doc["id"])
    target_table = tables[0] if tables else None
    
    if not target_table:
        print("No tables found.")
        return
        
    print(f"Found Table: {target_table['name']}")
    
    rows = list_rows(target_doc["id"], target_table["id"])
    print(f"Found {len(rows)} rows.")
    
    for row in rows:
        # Pring row values
        values = row.get("values", {})
        print(f"Row: {row['name']} - {values}")

if __name__ == "__main__":
    main()
