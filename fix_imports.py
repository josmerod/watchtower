#!/usr/bin/env python3
"""
This script will:
2. Remove these statements
3. Clean up any resulting empty lines
4. Report on changes made
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_sys_path_files() -> List[Path]:
    python_files = []
    project_root = Path(".")
    
    # Patterns to search for Python files
    patterns = ["**/*.py"]
    
    for pattern in patterns:
        python_files.extend(project_root.glob(pattern))
    
    files_with_sys_path = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                    files_with_sys_path.append(file_path)
        except UnicodeDecodeError:
            # Skip binary files
            continue
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            continue
    
    return files_with_sys_path


def remove_sys_path_insert(file_path: Path) -> Tuple[bool, int]:
    """
    Returns:
        Tuple of (was_modified, lines_removed)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_line_count = len(lines)
        modified_lines = []
        lines_removed = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
                lines_removed += 1
                # Skip this line and any empty lines that follow
                i += 1
                while i < len(lines) and lines[i].strip() == '':
                    lines_removed += 1
                    i += 1
            else:
                modified_lines.append(line)
                i += 1
        
        # Write back if changes were made
        if lines_removed > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
            return True, lines_removed
        
        return False, 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Main function to fix imports across the project."""
    print("🔧 Watchtower Import Cleanup")
    print("=" * 50)
    
    files_with_sys_path = find_sys_path_files()
    
    if not files_with_sys_path:
        return
    
    total_files_modified = 0
    total_lines_removed = 0
    
    for file_path in files_with_sys_path:
        was_modified, lines_removed = remove_sys_path_insert(file_path)
        
        if was_modified:
            total_files_modified += 1
            total_lines_removed += lines_removed
            status = f"✅ Modified (removed {lines_removed} lines)"
        else:
            status = "⚠️ No changes made"
        
        print(f"  {file_path}: {status}")
    
    print("\n" + "=" * 50)
    print(f"🎉 Cleanup completed!")
    print(f"Files modified: {total_files_modified}")
    print(f"Lines removed: {total_lines_removed}")
    
    if total_files_modified > 0:
        print("\nNext steps:")
        print("1. Run 'python install_dev.py' to install the package in development mode")
        print("2. Test that imports work correctly: python -c 'from src.config.settings import get_settings; print(\"✅ Imports working!\")'")
        print("3. Run your tests to ensure everything still works")
        print("4. Start the Streamlit app: streamlit run src/web/fullstreamlit/app.py")
    
    print("\nNote: After running install_dev.py, you should be able to use normal imports")
    print("like: from src.config.settings import get_settings")


if __name__ == "__main__":
    main() 