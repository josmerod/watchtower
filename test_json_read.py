import json
import os

# Test multiple paths
paths_to_try = [
    "data/classcentral/coursera_courses.json",
    "./data/classcentral/coursera_courses.json",
    "../data/classcentral/coursera_courses.json",
    "../../data/classcentral/coursera_courses.json",
    "../../../data/classcentral/coursera_courses.json",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/classcentral/coursera_courses.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/classcentral/coursera_courses.json"),
    "C:/Users/josem/watchtower/data/classcentral/coursera_courses.json"
]

print("Current working directory:", os.getcwd())

for path in paths_to_try:
    print(f"\nTrying path: {path}")
    try:
        exists = os.path.exists(path)
        print(f"File exists: {exists}")
        
        if exists:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"Successfully loaded JSON data!")
            print(f"Number of records: {len(data)}")
            
            # Show first record
            if data:
                print("\nFirst record:")
                first_record = data[0]
                for k, v in list(first_record.items())[:5]:  # Show first 5 fields
                    print(f"  {k}: {v}")
                print("  ...")
        
    except Exception as e:
        print(f"Error: {str(e)}") 