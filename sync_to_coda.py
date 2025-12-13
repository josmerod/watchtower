"""Sync project tasks to Coda.io."""

import csv
import json
import os
import requests
from pathlib import Path

# Configuration
API_KEY = "d483f282-b35a-4eaf-a5fa-ff47e9620942"
BASE_URL = "https://coda.io/apis/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def list_docs():
    """List accessible Coda docs."""
    response = requests.get(f"{BASE_URL}/docs", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def create_doc(title="Watchtower Project Tracking"):
    """Create a new Coda doc."""
    response = requests.post(
        f"{BASE_URL}/docs", 
        headers=HEADERS, 
        json={"title": title}
    )
    if response.status_code in [200, 201]:
        return response.json()
    print(f"Failed to create doc: {response.text}")
    return None

def list_tables(doc_id):
    """List tables in the doc."""
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Failed to list tables: {response.text}")
    return []

def list_columns(doc_id, table_id):
    """List columns in a table."""
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/columns", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def insert_rows(doc_id, table_id, rows, mapping):
    """Insert rows into the table.
    rows: list of dicts from CSV
    mapping: dict of csv_header -> column_id
    """
    coda_rows = []
    for row in rows:
        cells = []
        for csv_header, col_id in mapping.items():
            if csv_header in row:
                cells.append({"column": col_id, "value": row[csv_header]})
        coda_rows.append({"cells": cells})
    
    payload = {"rows": coda_rows}
    # Coda API allows batching, but let's do small batches or one big one depending on size
    # Limit is usually around 500 rows or 10MB. We have ~20 rows.
    
    response = requests.post(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows", headers=HEADERS, json=payload)
    if response.status_code in [200, 202]:
        print(f"Successfully inserted {len(rows)} rows.")
    else:
        print(f"Failed to insert rows: {response.text}")

def main():
    print("Starting smart sync to Coda...")
    
    # 1. Find Doc
    docs = list_docs()
    target_doc = None
    for doc in docs:
        if doc["name"] == "Watchtower Project Tracking":
            target_doc = doc
            break
            
    if not target_doc:
        print("Doc 'Watchtower Project Tracking' not found. Please ensure it exists.")
        return

    doc_id = target_doc["id"]
    print(f"Found Doc: {target_doc['name']} ({doc_id})")

    # 2. Find Table
    tables = list_tables(doc_id)
    if not tables:
        print("No tables found in the doc. Please create a table to hold the tasks.")
        return
        
    # Assume the first table is the one, or look for one named "Tasks"
    target_table = tables[0]
    print(f"Found Table: {target_table['name']} ({target_table['id']})")
    
    # 3. Map Columns
    columns = list_columns(doc_id, target_table["id"])
    print("Found Columns:", [c["name"] for c in columns])
    
    # Map CSV headers to Column IDs
    # CSV Headers: ID, Title, Status, Story Points, Epic, Description, Priority
    # We do a case-insensitive match
    csv_headers = ["ID", "Title", "Status", "Story Points", "Epic", "Description", "Priority"]
    
    col_mapping = {} # csv_header -> col_id
    for header in csv_headers:
        for col in columns:
            if col["name"].lower() == header.lower():
                col_mapping[header] = col["id"]
                break
    
    print("Column Mapping:", col_mapping)
    
    if len(col_mapping) < 3:
        print("Warning: Few columns matched. Please ensure Table columns match CSV headers: ID, Title, Status, Priority, etc.")
        # We proceed anyway
        
    # 4. Read CSV
    csv_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\4fdf1acc-ac2f-436f-8a11-653d1a41792b\tasks_export.csv")
    if not csv_path.exists():
        print("CSV export not found.")
        return

    tasks = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)

    print(f"Reading {len(tasks)} tasks from CSV...")
    
    # 5. Insert Data
    insert_rows(doc_id, target_table["id"], tasks, col_mapping)

if __name__ == "__main__":
    main()
