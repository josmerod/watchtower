"""
Simple test script to verify courses loading fix.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
from src.web.fullstreamlit.utils.data_service import DataService
from src.utils.logging import get_logger

def main():
    """Test courses functionality"""
    print("🎓 Testing Courses Fix")
    print("=" * 50)
    
    # Initialize components
    logger = get_logger("CoursesFixTest")
    data_service = DataService(logger)
    
    print("\n📁 Checking file existence...")
    
    # Check Udemy file
    udemy_file = data_service.data_dir / "udemy" / "udemy_courses.json"
    print(f"Udemy file: {udemy_file}")
    print(f"Exists: {udemy_file.exists()}")
    if udemy_file.exists():
        size = udemy_file.stat().st_size
        print(f"Size: {size // 1024} KB")
    
    # Check Coursera file
    coursera_file = data_service.data_dir / "classcentral" / "coursera_courses.json"
    print(f"\nCoursera file: {coursera_file}")
    print(f"Exists: {coursera_file.exists()}")
    if coursera_file.exists():
        size = coursera_file.stat().st_size
        print(f"Size: {size // 1024} KB")
    
    print("\n📚 Testing DataService...")
    
    try:
        # Load courses data using DataService
        courses_data = data_service.get_courses_data()
        
        if courses_data:
            print("✅ Courses loaded successfully!")
            
            for platform, df in courses_data.items():
                print(f"\n{platform.title()}:")
                print(f"  - Count: {len(df)} courses")
                
                if not df.empty:
                    print(f"  - Columns: {list(df.columns)}")
                    
                    # Check first few courses
                    if 'title' in df.columns:
                        print("  - First 3 courses:")
                        for i, row in df.head(3).iterrows():
                            title = row.get('title', 'No title')[:60]
                            print(f"    {i+1}. {title}")
                    
                    # Check ordering
                    if 'scraped_at' in df.columns:
                        dates = df['scraped_at'].dropna()
                        if len(dates) > 1:
                            first_date = str(dates.iloc[0])[:10]
                            last_date = str(dates.iloc[-1])[:10]
                            print(f"  - Date range: {first_date} to {last_date}")
        else:
            print("❌ No courses data loaded")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 