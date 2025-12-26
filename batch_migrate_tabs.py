#!/usr/bin/env python3
"""Quick migration script for batch-updating dashboard tabs to repository pattern."""

import re
from pathlib import Path
from typing import Any

# Migration template
REPOSITORY_TEMPLATE = '''
# NEW: Repository-based loading (SOLID Pattern)
class {RepositoryName}(BaseRepository[list[dict[str, Any]]]):
    """Repository for {DataDescription} data."""

    def __init__(self):
        """Initialize {DataDescription} repository."""
        super().__init__(
            data_path={FilePath},
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instance
{repository_instance} = {RepositoryName}()
'''


def migrate_tab(tab_file: str, load_func_name: str, data_file_expr: str, repository_name: str, instance_name: str):
    """Migrate a tab file to use repository pattern.

    Args:
        tab_file: Path to tab file
        load_func_name: Name of the load function to wrap
        data_file_expr: Expression that evaluates to data file path
        repository_name: Name for the repository class
        instance_name: Name for the repository instance
    """
    file_path = Path(f"src/web/dashboard/components/{tab_file}")

    # Read file
    content = file_path.read_text(encoding='utf-8')

    # Check if already migrated
    if "from src.repositories import BaseRepository" in content:
        print(f"[SKIP] {tab_file} - already has repository import")
        return

    # Check if has load function
    if f"def {load_func_name}" not in content:
        print(f"[SKIP] {tab_file} - no {load_func_name} function found")
        return

    # Add repository import after existing imports
    if "from src.repositories import BaseRepository" not in content:
        # Find last import line
        import_lines = [i for i, line in enumerate(content.split('\n')) if line.strip().startswith('import') or line.strip().startswith('from')]

        if import_lines:
            last_import_line = import_lines[-1]
            lines = content.split('\n')
            lines.insert(last_import_line + 1, "\n# Import repository pattern (NEW)")
            lines.insert(last_import_line + 2, "from src.repositories import BaseRepository\n")
            content = '\n'.join(lines)

    # Insert repository class before load function
    repo_class = REPOSITORY_TEMPLATE.format(
        RepositoryName=repository_name,
        DataDescription=repository_name.replace('Repository', ''),
        FilePath=data_file_expr,
        repository_instance=instance_name,
    )

    # Find load function and add repository before it
    load_func_pattern = f"(def {load_func_name}\\(\\)"
    if re.search(load_func_pattern, content):
        # Insert repository class and OLD comment before load function
        def insert_pos = content.find(f"def {load_func_name}(")

        # Create the new wrapper function
        new_load_func = f'''
# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# {content[def insert_pos:content.find('\\n\\ndef', def insert_pos) + 150]}

def {load_func_name}():
    """Load data using repository pattern (NEW).

    Returns:
        List of data items
    """
    try:
        return {instance_name}.get()
    except Exception as e:
        print(f"Error loading data: {{e}}")
        return []
'''

        # This is complex - let's use a simpler approach
        print(f"[TODO] {tab_file} - requires manual migration")


if __name__ == "__main__":
    # Quick batch migration
    print("Batch Migration Tool")
    print("=" * 60)

    # Test migration on one file first
    migrate_tab(
        "intelligence_tab.py",
        "load_intelligence_data",
        'Path("data/intelligence/output/intelligence_latest.json")',
        "IntelligenceRepository",
        "intelligence_repo"
    )
