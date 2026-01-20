import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("DEBUG: Starting import test")
try:
    from src.web.dashboard.components import courses_tab
    print("DEBUG: Import successful")
    print(f"DEBUG: ALL_COURSES_DATA keys: {courses_tab.ALL_COURSES_DATA.keys()}")
    udemy_df = courses_tab.ALL_COURSES_DATA.get("udemy")
    if udemy_df is not None and not udemy_df.empty:
         print(f"DEBUG: Udemy Data loaded. Shape: {udemy_df.shape}")
         print(udemy_df.head(1).to_dict())
    else:
         print("DEBUG: Udemy Data is empty or None")
         print(f"DEBUG: COURSES_DATA_LOADED: {courses_tab.COURSES_DATA_LOADED}")

except Exception as e:
    print(f"DEBUG: Import failed: {e}")
    import traceback
    traceback.print_exc()
