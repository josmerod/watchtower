
import json
import requests
import sys
from collections import defaultdict

# Configuration from sync_to_coda.py
API_KEY = "d483f282-b35a-4eaf-a5fa-ff47e9620942"
BASE_URL = "https://coda.io/apis/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

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

def get_columns(doc_id, table_id):
    response = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/columns", headers=HEADERS)
    if response.status_code != 200:
        return []
    return response.json().get("items", [])

def list_rows(doc_id, table_id, limit=2000):
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    params = {"limit": limit}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    print(f"Error listing rows: {response.text}")
    return []

def delete_rows(doc_id, table_id, row_ids):
    if not row_ids:
        return
    url = f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows"
    payload = {"rowIds": row_ids}
    print(f"Deleting {len(row_ids)} duplicate rows...")
    response = requests.delete(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 202]:
        print("Deletion successful.")
    else:
        print(f"Failed to delete rows: {response.text}")

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
    
    # Get columns to map ID, Title, Status
    columns = get_columns(target_doc["id"], target_table["id"])
    col_map = {c["name"]: c["id"] for c in columns}
    
    id_col = col_map.get("ID")
    title_col = col_map.get("Title") or col_map.get("Task Name") or col_map.get("Name")
    status_col = col_map.get("Status")
    priority_col = col_map.get("Priority")

    if not id_col:
        print("Could not find 'ID' column. Cannot deduplicate.")
        return

    print("Fetching rows...")
    rows = list_rows(target_doc["id"], target_table["id"])
    print(f"Fetched {len(rows)} rows.")

    # Group by ID
    tasks_by_id = defaultdict(list)
    for row in rows:
        values = row.get("values", {})
        task_id_val = values.get(id_col)
        
        # Capture task details for display
        task_data = {
            "row_id": row["id"],
            "id": task_id_val,
            "title": values.get(title_col, "Unknown Title"),
            "status": values.get(status_col, "Unknown Status"),
            "priority": values.get(priority_col, "Unknown Priority"),
            "index": row["index"] # Keep track of order/recency if available
        }
        
        if task_id_val: # Only group if ID exists
             tasks_by_id[str(task_id_val)].append(task_data)

    # Identify duplicates
    duplicates_to_delete = []
    unique_tasks = []

    for t_id, task_list in tasks_by_id.items():
        if len(task_list) > 1:
            # Sort by row index (or creation) - assuming higher index/later content is better?
            # Or just keep the first one found?
            # Let's keep the one with the most complete info?
            # For now, let's keep the one with the highest 'index' (usually latest added) or lowest (original)?
            # Coda API 'index' might not be reliable for recency. 
            # Let's keep the first one and delete the rest.
            
            # Actually, standard behavior is usually "keep latest", but sometimes duplicates are partial.
            # I'll keep the first one in the list returned by API unless I have reason not to.
            # Let's arbitrary keep the one with the LOWEST index (top of table) or HIGHEST?
            # Let's simply keep the first one in the list (index 0) and delete others (index 1+)
            
            keep = task_list[0]
            for dupe in task_list[1:]:
                duplicates_to_delete.append(dupe["row_id"])
            
            unique_tasks.append(keep)
        else:
            unique_tasks.append(task_list[0])

    if duplicates_to_delete:
        print(f"Found {len(duplicates_to_delete)} duplicate rows.")
        delete_rows(target_doc["id"], target_table["id"], duplicates_to_delete)
        # Re-fetch or just modify local list?
        # We can just rely on unique_tasks.
    else:
        print("No duplicates found.")

    with open("tasks_output.txt", "w", encoding="utf-8") as f:
        f.write("--- Available Tasks ---\n")
        # Sort by ID
        unique_tasks.sort(key=lambda x: str(x["id"]))
        
        for t in unique_tasks:
            line = f"[{t['id']}] {t['title']} (Status: {t['status']}, Priority: {t['priority']})"
            print(line)
            f.write(line + "\n")

if __name__ == "__main__":
    main()
