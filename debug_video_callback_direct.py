#!/usr/bin/env python3
"""
Test video callback behavior directly
"""
import os
import sys
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import components
from src.web.dashboard.components.videos_tab import (
    ALL_VIDEOS_DATA, 
    VIDEO_DATA_LOADED,
    create_video_card,
    update_video_display
)

def test_callback_directly():
    print("Testing video callback directly...")
    print(f"VIDEO_DATA_LOADED: {VIDEO_DATA_LOADED}")
    print(f"Number of channels: {len(ALL_VIDEOS_DATA)}")
    
    if not ALL_VIDEOS_DATA:
        print("ERROR: No video data available!")
        return
    
    # Test the callback with default parameters (no channel selected)
    try:
        # These are the default values when the page loads
        selected_channel = None  # No channel selected = show all
        search_term = None      # No search
        date_filter_value = 'all'  # All dates
        current_page = 1        # First page
        page_size = 12         # Default page size
        
        print(f"\nCalling callback with:")
        print(f"  selected_channel: {selected_channel}")
        print(f"  search_term: {search_term}")
        print(f"  date_filter_value: {date_filter_value}")
        print(f"  current_page: {current_page}")
        print(f"  page_size: {page_size}")
        
        # This simulates what happens when the videos tab loads
        if not VIDEO_DATA_LOADED or not ALL_VIDEOS_DATA:
            print("ERROR: Data check failed in callback")
            return
            
        # Combine all channels (this is what happens when no channel is selected)
        df_filtered = pd.concat(ALL_VIDEOS_DATA.values(), ignore_index=True)
        df_filtered.sort_values(by='published_date', ascending=False, inplace=True)
        print(f"Combined dataframe: {len(df_filtered)} total videos")
        
        # Apply pagination
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        df_paginated = df_filtered.iloc[start_idx:end_idx]
        print(f"Paginated: {len(df_paginated)} videos for page {current_page}")
        
        if df_paginated.empty:
            print("ERROR: No videos after pagination!")
            return
            
        # Test creating video cards
        print(f"\nTesting video card creation...")
        video_cards = []
        for idx, row in df_paginated.iterrows():
            try:
                card = create_video_card(row)
                video_cards.append(card)
                if len(video_cards) <= 3:  # Show details for first 3
                    print(f"  Card {len(video_cards)}: {row.get('title', 'N/A')[:50]}...")
                    print(f"    Thumbnail: {row.get('thumbnail_url', 'N/A')[:80]}...")
            except Exception as e:
                print(f"  ERROR creating card for video {idx}: {e}")
                
        print(f"Successfully created {len(video_cards)} video cards")
        
        if video_cards:
            print("SUCCESS: Video cards should be displayable!")
        else:
            print("ERROR: No video cards created!")
            
    except Exception as e:
        print(f"ERROR in callback test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_callback_directly()