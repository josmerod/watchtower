import json
import os
import sys
import uuid

import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration — read CODA_API_KEY from .env (see .env.example).
API_KEY = os.getenv("CODA_API_KEY")
if not API_KEY:
    print("Error: CODA_API_KEY must be set in .env file")
    sys.exit(1)
DOC_ID = "1k2j3l4m5n"  # Placeholder, will need to fetch if not known, or search by name
BASE_URL = "https://coda.io/apis/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def get_doc_id(doc_name="Watchtower Project Tracking"):
    """Find the doc ID by name."""
    response = requests.get(f"{BASE_URL}/docs", headers=HEADERS)
    if response.status_code == 200:
        docs = response.json().get("items", [])
        for doc in docs:
            if doc["name"] == doc_name:
                return doc["id"]
    print("Could not find doc.")
    return None


def get_table_info(doc_id, table_name_keyword="Tasks"):
    """Find the table and column mapping."""
    # List tables
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables", headers=HEADERS)
    target_table = None
    if response.status_code == 200:
        tables = response.json().get("items", [])
        if tables:
            # Try to find one with "Task" in name, or just take first
            for t in tables:
                if table_name_keyword.lower() in t["name"].lower():
                    target_table = t
                    break
            if not target_table:
                target_table = tables[0]

    if not target_table:
        print("No table found.")
        return None, None

    # List columns
    cols_resp = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{target_table['id']}/columns", headers=HEADERS)
    col_mapping = {}
    if cols_resp.status_code == 200:
        columns = cols_resp.json().get("items", [])
        # Simple mapping: Name -> ID
        # Targeted headers: Title, Description, Priority, Status, Epic
        desired_headers = ["Title", "Description", "Priority", "Status", "Epic"]
        for h in desired_headers:
            for col in columns:
                if col["name"].lower() == h.lower():
                    col_mapping[h] = col["id"]
                    break

    return target_table["id"], col_mapping


def add_tasks(doc_id, table_id, col_mapping, tasks):
    """Add tasks to Coda."""
    rows = []
    for task in tasks:
        cells = []
        for key, value in task.items():
            if key in col_mapping:
                cells.append({"column": col_mapping[key], "value": value})
        rows.append({"cells": cells})

    payload = {"rows": rows}
    response = requests.post(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows", headers=HEADERS, json=payload)
    if response.status_code in [200, 202]:
        print(f"✅ Successfully added {len(tasks)} tasks to Coda.")
    else:
        print(f"❌ Failed to add tasks: {response.text}")


def main():
    print("🔍 Connecting to Coda...")
    doc_id = get_doc_id()
    if not doc_id:
        return

    print(f"📄 Found Doc ID: {doc_id}")
    table_id, col_mapping = get_table_info(doc_id)

    if not table_id:
        return

    print(f"📊 Found Table ID: {table_id}")
    print(f"🗺️ Column Mapping: {col_mapping}")

    # Define the new tasks based on analysis
    new_tasks = [
        {
            "Title": "Implement Real Scraping for BookDealsETL",
            "Description": "The current BookDealsETL is a stub returning 12 hardcoded items. Implement actual extraction logic for Kindle, Gutenberg, and other configured sources.",
            "Priority": "High",
            "Status": "To Do",
            "Epic": "Epic 8",
        },
        {
            "Title": "Fix AI Research Intelligence ETL Failure",
            "Description": "The AI Research Intelligence ETL failed with 0 records. Debug `src/etl/intelligence/ai_research_etl.py` (or correct file) to fix extraction logic.",
            "Priority": "High",
            "Status": "To Do",
            "Epic": "Epic 8",
        },
        {
            "Title": "Audit Deals ETLs for Stubs",
            "Description": "Verify if other Deals ETLs (music_deals, travel_deals, etc.) are also stubs like BookDealsETL and implement real scraping if needed.",
            "Priority": "Medium",
            "Status": "To Do",
            "Epic": "Epic 7",
        },
        {"Title": "Enrich Developer News with Tags", "Description": "Add heuristic or LLM-based tagging to Developer News items for better filtering.", "Priority": "Low", "Status": "To Do", "Epic": "Epic 8"},
    ]

    add_tasks(doc_id, table_id, col_mapping, new_tasks)


if __name__ == "__main__":
    main()
