#!/usr/bin/env python3
"""
Quick test script to verify video card creation and data loading
"""
import os
import sys
import json
import pandas as pd

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from web.dashboard.components.videos_tab import load_videos_data, ALL_VIDEOS_DATA, create_video_card

def test_video_data_loading():
    """Test if video data loads correctly"""
    print("Testing video data loading...")
    
    # Load video data
    load_videos_data()
    
    print(f"Number of channels loaded: {len(ALL_VIDEOS_DATA)}")
    
    if not ALL_VIDEOS_DATA:
        print("❌ No video data loaded!")
        return False
        
    print("✅ Video data loaded successfully!")
    
    # Test each channel
    for channel_name, df in ALL_VIDEOS_DATA.items():
        print(f"  - {channel_name}: {len(df)} videos")
        
        if not df.empty:
            # Show sample video data
            sample_video = df.iloc[0]
            print(f"    Sample video: {sample_video.get('title', 'N/A')}")
            print(f"    Thumbnail URL: {sample_video.get('thumbnail_url', 'N/A')}")
            print(f"    Published: {sample_video.get('published_date', 'N/A')}")
            
            # Test video card creation
            try:
                video_card = create_video_card(sample_video)
                print(f"    ✅ Video card created successfully for {channel_name}")
            except Exception as e:
                print(f"    ❌ Error creating video card for {channel_name}: {e}")
                
            print()  # Empty line for readability
            
    return True

def test_sample_video_json():
    """Test loading a sample video JSON file directly"""
    print("\nTesting direct JSON file loading...")
    
    sample_path = "data/youtube/aa-dev/youtube_videos.json"
    if os.path.exists(sample_path):
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                videos = json.load(f)
                
            print(f"✅ Successfully loaded {len(videos)} videos from {sample_path}")
            
            if videos:
                sample = videos[0]
                print(f"Sample video data structure:")
                for key, value in sample.items():
                    if key == 'description':
                        print(f"  {key}: {str(value)[:100]}...")  # Truncate long descriptions
                    else:
                        print(f"  {key}: {value}")
                        
                # Test if thumbnail URL is accessible
                thumbnail_url = sample.get('thumbnail', '')
                if thumbnail_url:
                    print(f"\nThumbnail URL: {thumbnail_url}")
                    # We could test accessibility here, but let's keep it simple
                    
        except Exception as e:
            print(f"❌ Error loading {sample_path}: {e}")
    else:
        print(f"❌ Sample file not found: {sample_path}")

if __name__ == "__main__":
    print("🎬 Video Cards Test Script")
    print("=" * 50)
    
    # Test data loading
    success = test_video_data_loading()
    
    # Test direct JSON loading
    test_sample_video_json()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Video data loading test completed!")
    else:
        print("❌ Video data loading failed!")