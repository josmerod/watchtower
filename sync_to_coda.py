"""Sync project tasks to Coda.io (Live Update with Deduplication)."""

import json
import requests
import sys

# Configuration
API_KEY = "d483f282-b35a-4eaf-a5fa-ff47e9620942"
BASE_URL = "https://coda.io/apis/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TASKS_TO_UPDATE = [
    {
        "ID": "8.10",
        "Title": "Epic 8.10: Startup Intelligence",
        "Status": "Done",
        "Story Points": "8",
        "Epic": "Epic 8",
        "Description": "Comprehensive startup tracking including TechCrunch, Product Hunt, and AI analysis.",
        "Priority": "High"
    },
    {
        "ID": "8.10.1", 
        "Title": "Startup Intelligence ETL", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Implemented StartupIntelligenceETL with TechCrunch and Product Hunt scrapers.",
        "Priority": "High"
    },
    {
        "ID": "8.10.2", 
        "Title": "Startup Intelligence Tab", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Created dashboard tab for Startups with AI-enriched analysis and filtering.",
        "Priority": "High"
    },
    {
        "ID": "8.10.3", 
        "Title": "Startup AI Enrichment", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Integrated Gemini Flash 2.0 for categorizing and scoring startup news.",
        "Priority": "Medium"
    },
    {
        "ID": "8.11", 
        "Title": "Epic 8.11: Open Source Intelligence", 
        "Status": "Done", 
        "Story Points": "8",
        "Epic": "Epic 8",
        "Description": "GitHub Trending aggregation across key languages with AI insights.",
        "Priority": "High"
    },
    {
        "ID": "8.11.1", 
        "Title": "Open Source ETL (Playwright)", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Implemented Playwright scraper for GitHub Trending (Daily/Weekly).",
        "Priority": "High"
    },
    {
        "ID": "8.11.2", 
        "Title": "Open Source Dashboard Tab", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Created dashboard tab with language filtering and star sorting.",
        "Priority": "High"
    },
    {
        "ID": "8.11.3", 
        "Title": "Open Source AI Enrichment", 
        "Status": "Done", 
        "Story Points": "2",
        "Epic": "Epic 8",
        "Description": "Automated categorization and summary generation for repos.",
        "Priority": "Medium"
    },
    {
        "ID": "8.9.1", 
        "Title": "Product Hunt ETL (Playwright)", 
        "Status": "Done", 
        "Story Points": "3",
        "Epic": "Epic 8",
        "Description": "Implemented Playwright scraper for Product Hunt to bypass 403 errors.",
        "Priority": "High"
    },
    {
        "ID": "8.9.2", 
        "Title": "Reddit ETL Quality Filters", 
        "Status": "Done", 
        "Story Points": "2",
        "Epic": "Epic 8",
        "Description": "Added score (>=10) and stickied filters to Reddit ETL.",
        "Priority": "Medium"
    },
    {
        "ID": "8.9.3", 
        "Title": "Developer News Dashboard Tab", 
        "Status": "Done", 
        "Story Points": "5",
        "Epic": "Epic 8",
        "Description": "Implemented dedicated tab for developer news (Product Hunt, Reddit, etc.) with search.",
        "Priority": "High"
    },
    {
        "ID": "8.9.4", 
        "Title": "UI Cleanup", 
        "Status": "Done", 
        "Story Points": "1",
        "Epic": "Epic 8",
        "Description": "Removed unused tabs (Intelligence, AI Research) to declutter UI.",
        "Priority": "Low"
    },
     {
        "ID": "8.9.5", 
        "Title": "Arxiv Watcher Fix", 
        "Status": "Done", 
        "Story Points": "2",
        "Epic": "Epic 8",
        "Description": "Fixed Arxiv API query errors by removing submittedDate filter.",
        "Priority": "High"
    }
]

def list_docs():
    response = requests.get(f"{BASE_URL}/docs", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Error listing docs: {response.text}")
    return []

def list_tables(doc_id):
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables", headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Error listing tables: {response.text}")
    return []

def find_column_mapping(doc_id, table_id, keys):
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/columns", headers=HEADERS)
    if response.status_code != 200:
        return {}
    
    columns = response.json().get("items", [])
    mapping = {}
    for key in keys:
        for col in columns:
            if col["name"].lower() == key.lower():
                mapping[key] = col["id"]
                break
    return mapping

def list_rows(doc_id, table_id, limit=500):
    """List rows from the table."""
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    params = {"limit": limit} # Adjust if more rows needed
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Error listing rows: {response.text}")
    return []

def delete_rows(doc_id, table_id, row_ids):
    """Delete rows by ID."""
    if not row_ids:
        return
    
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    payload = {"rowIds": row_ids}
    
    print(f"Deleting {len(row_ids)} rows...")
    response = requests.delete(url, headers=HEADERS, json=payload)
    
    if response.status_code in [200, 202]:
        print("Deletion successful.")
    else:
        print(f"Failed to delete rows: {response.text}")

def upsert_rows(doc_id, table_id, rows, mapping, key_columns):
    """Upsert rows manually (insert)."""
    coda_rows = []
    for row in rows:
        cells = []
        for key, value in row.items():
            if key in mapping:
                cells.append({"column": mapping[key], "value": value})
        coda_rows.append({"cells": cells})
        
    payload = {"rows": coda_rows}
    
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    print(f"Inserting {len(rows)} rows to {url}...")
    
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 202]:
        print("Success!")
    else:
        print(f"Failed: {response.text}")

def clean_and_sync(doc_id, table_id, tasks, mapping):
    """Delete existing entries for these tasks, then insert fresh."""
    
    # 1. Get existing rows
    print("Fetching existing rows to check for duplicates...")
    existing_rows = list_rows(doc_id, table_id)
    
    # 2. Find column ID for "ID"
    id_col_id = mapping.get("ID")
    if not id_col_id:
        print("Could not find 'ID' column. Cannot deduplicate safely.")
        return

    # 3. Identify rows to delete
    # We delete ALL instances matching our current task IDs to ensure clean state
    task_ids_to_reset = {t["ID"] for t in tasks}
    rows_to_delete = []
    
    for row in existing_rows:
        # Find the value of the ID column in this row
        row_task_id = None
        if "values" in row:
             row_task_id = row["values"].get(id_col_id)
        
        # Checking if the row's ID matches one of our target IDs
        if row_task_id and str(row_task_id) in task_ids_to_reset:
            rows_to_delete.append(row["id"])
            
    if rows_to_delete:
        print(f"Found {len(rows_to_delete)} older/duplicate instances of these tasks.")
        delete_rows(doc_id, table_id, rows_to_delete)
    else:
        print("No duplicates found to delete.")
        
    # 4. Insert Fresh
    upsert_rows(doc_id, table_id, tasks, mapping, ["ID"])

def main():
    print("Connecting to Coda...")
    docs = list_docs()
    target_doc = next((d for d in docs if "Watchtower" in d["name"]), None)
    
    if not target_doc:
        target_doc = next((d for d in docs if "Project" in d["name"]), None)
        
    if not target_doc:
        print("Could not find Watchtower Project Doc.")
        return

    print(f"Using Doc: {target_doc['name']}")
    
    tables = list_tables(target_doc["id"])
    target_table = next((t for t in tables if "Tasks" in t["name"] or "Stories" in t["name"]), None)
    
    if not target_table:
        if tables:
            target_table = tables[0]
            print(f"Defaulting to first table: {target_table['name']}")
        else:
            print("No tables found.")
            return

    print(f"Using Table: {target_table['name']}")
    
    mapping = find_column_mapping(target_doc["id"], target_table["id"], TASKS_TO_UPDATE[0].keys())
    print(f"Mapped columns: {list(mapping.keys())}")
    
    clean_and_sync(target_doc["id"], target_table["id"], TASKS_TO_UPDATE, mapping)

if __name__ == "__main__":
    main()
