#!/usr/bin/env python3
"""Simple test to see what the videos tab is actually rendering"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import the new videos tab
from src.web.dashboard.components.videos_tab import (
    LOADED,
    VIDEO_DATA,
    render_videos_tab,
)


def test_render():
    print("Testing videos tab render...")
    print(f"LOADED: {LOADED}")
    print(f"VIDEO_DATA keys: {list(VIDEO_DATA.keys())}")

    if VIDEO_DATA:
        sample_channel = list(VIDEO_DATA.keys())[0]
        sample_df = VIDEO_DATA[sample_channel]
        print(f"Sample channel '{sample_channel}' has {len(sample_df)} videos")

        if not sample_df.empty:
            sample_video = sample_df.iloc[0]
            print(f"Sample video: {sample_video['title']}")
            print(f"Thumbnail: {sample_video['thumbnail']}")

    # Try to render the tab
    try:
        layout = render_videos_tab()
        print("Layout rendered successfully")
        print(f"Layout type: {type(layout)}")

        # Check if it has the expected components
        if hasattr(layout, "children"):
            print(f"Layout has {len(layout.children)} children")
            for i, child in enumerate(layout.children):
                print(f"  Child {i}: {type(child)}")

        return True
    except Exception as e:
        print(f"Error rendering layout: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_render()
    print(f"\nResult: {'Success' if success else 'Failed'}")
