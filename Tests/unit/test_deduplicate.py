"""
Test script to deduplicate courses from JSON files.

import os
import sys
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def deduplicate_courses(input_file, output_file=None, key_field="url"):
    """Deduplicate courses from a JSON file based on URL or title."""
    if output_file is None:
        output_file = input_file
        
    # Create backup
    backup_file = f"{input_file}.bak"
    try:
        import shutil
        shutil.copy2(input_file, backup_file)
        logging.info(f"Created backup at {backup_file}")
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return False
    
    # Read courses
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            courses = json.load(f)
        
        if not isinstance(courses, list):
            return False
            
        logging.info(f"Read {len(courses)} courses from {input_file}")
        
        # Track unique courses
        unique_courses = {}
        duplicate_count = 0
        
        # Process each course
        for course in courses:
            if key_field not in course:
                continue
                
            key = course[key_field]
            if key.strip().lower() in unique_courses:
                duplicate_count += 1
                continue
            
            # Add to unique courses
            unique_courses[key.strip().lower()] = course
        
        deduplicated_courses = list(unique_courses.values())
        
        # Save deduplicated courses
        with open(output_file, 'w', encoding='utf-8') as f:
            
        return True
        
    except Exception as e:
        return False

if __name__ == "__main__":
    # Simple argument parsing
    if len(sys.argv) < 2:
        print("Usage: python test_deduplicate.py INPUT_FILE [KEY_FIELD]")
        sys.exit(1)
        
    input_file = sys.argv[1]
    key_field = sys.argv[2] if len(sys.argv) > 2 else "url"
    
    if deduplicate_courses(input_file, key_field=key_field):
    else:
        logging.error("Deduplication failed")
        sys.exit(1) 