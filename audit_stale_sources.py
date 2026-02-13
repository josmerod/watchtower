import os
import datetime
from pathlib import Path

def get_stale_sources(data_dir: str, days_threshold: int = 2):
    data_path = Path(data_dir)
    if not data_path.exists():
        with open("stale_sources_report.txt", "w") as f:
            f.write(f"Data directory not found: {data_dir}\n")
        return

    report_lines = []
    report_lines.append(f"{'Source':<35} | {'Last Updated':<20} | {'Days Since':<10} | {'Status'}")
    report_lines.append("-" * 85)

    now = datetime.datetime.now()
    
    stale_sources = []
    never_run_sources = []

    # Get all items and sort them by name for consistent output
    items = sorted([item for item in data_path.iterdir() if item.is_dir()], key=lambda x: x.name)

    for item in items:
        # Find the latest file in this directory (recursive)
        latest_time = 0
        latest_file = None
        
        for file_path in item.rglob("*"):
            if file_path.is_file():
                mtime = file_path.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = file_path
        
        if latest_time > 0:
            last_updated = datetime.datetime.fromtimestamp(latest_time)
            delta = now - last_updated
            days_since = delta.days
            
            status = "OK"
            if days_since >= days_threshold:
                status = "STALE"
                stale_sources.append((item.name, last_updated, days_since))
            
            report_lines.append(f"{item.name:<35} | {last_updated.strftime('%Y-%m-%d %H:%M')} | {days_since:<10} | {status}")
        else:
            report_lines.append(f"{item.name:<35} | {'NEVER':<20} | {'-':<10} | EMPTY")
            never_run_sources.append(item.name)
    
    report_lines.append("-" * 85)
    report_lines.append(f"Summary: {len(stale_sources)} stale, {len(never_run_sources)} empty/never run, {len(items) - len(stale_sources) - len(never_run_sources)} OK.")
    
    # Write to file
    with open("stale_sources_report.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print("Report written to stale_sources_report.txt")

if __name__ == "__main__":
    project_root = r"c:\Users\josem\watchtower"
    data_dir = os.path.join(project_root, "data")
    get_stale_sources(data_dir, days_threshold=2)
