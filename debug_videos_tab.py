#!/usr/bin/env python3
"""
Debug script to test video tab functionality directly
"""
import os
import sys
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_manual_video_loading():
    """Test loading video data manually without the complex import chain"""
    print("Manual Video Data Test")
    print("=" * 50)
    
    data_path = os.path.join(os.getcwd(), "data", "youtube")
    print(f"Looking for data in: {data_path}")
    
    if not os.path.exists(data_path):
        print(f"Data directory not found: {data_path}")
        return False
        
    # List all channels
    channels = [d for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]
    print(f"Found {len(channels)} channels: {channels}")
    
    if not channels:
        print("No channel directories found")
        return False
        
    # Test loading one channel
    test_channel = channels[0]
    channel_path = os.path.join(data_path, test_channel)
    json_file = os.path.join(channel_path, "youtube_videos.json")
    
    print(f"\nTesting channel: {test_channel}")
    print(f"JSON file path: {json_file}")
    
    if not os.path.exists(json_file):
        print(f"JSON file not found: {json_file}")
        return False
        
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            videos = json.load(f)
            
        print(f"Loaded {len(videos)} videos from {test_channel}")
        
        if videos:
            sample_video = videos[0]
            print(f"\nSample video:")
            print(f"  Title: {sample_video.get('title', 'N/A')}")
            print(f"  URL: {sample_video.get('url', 'N/A')}")
            print(f"  Thumbnail: {sample_video.get('thumbnail', 'N/A')}")
            print(f"  Channel: {sample_video.get('channel', 'N/A')}")
            print(f"  Published: {sample_video.get('published_at', 'N/A')}")
            
            # Test thumbnail URL
            thumbnail_url = sample_video.get('thumbnail', '')
            if thumbnail_url:
                print(f"  Thumbnail URL present: {thumbnail_url[:80]}...")
            else:
                print(f"  No thumbnail URL found")
                
            return True
        else:
            print("No videos in JSON file")
            return False
            
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return False

def test_simple_dash_video_card():
    """Test creating a simple video card without complex imports"""
    print("\nSimple Dash Card Test")
    print("=" * 50)
    
    try:
        import dash
        from dash import html
        import dash_bootstrap_components as dbc
        
        # Create a simple video card structure
        sample_video = {
            'title': 'Test Video Title',
            'url': 'https://www.youtube.com/watch?v=test',
            'thumbnail_url': 'https://i.ytimg.com/vi/VLRqbFU4IdE/maxresdefault.jpg',
            'channel_name': 'Test Channel',
            'published_date': '2024-01-01',
        }
        
        # Create a simple card structure similar to our component
        card = dbc.Card([
            html.Img(
                src=sample_video['thumbnail_url'],
                style={
                    "maxHeight": "180px", 
                    "width": "100%", 
                    "objectFit": "cover"
                },
                className="card-img-top"
            ),
            dbc.CardBody([
                html.H5(sample_video['title'], className="card-title"),
                html.P(sample_video['channel_name'], className="card-text text-muted"),
                html.P(sample_video['published_date'], className="card-text text-muted"),
            ])
        ], className="video-card")
        
        print("Video card created successfully")
        print(f"  Card type: {type(card)}")
        print(f"  Card children: {len(card.children) if hasattr(card, 'children') else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"Error creating video card: {e}")
        return False

if __name__ == "__main__":
    print("Video Tab Debug Script")
    print("=" * 70)
    
    # Test manual loading
    data_success = test_manual_video_loading()
    
    # Test simple card creation
    card_success = test_simple_dash_video_card()
    
    print("\n" + "=" * 70)
    print("Results Summary:")
    print(f"  Data Loading: {'Success' if data_success else 'Failed'}")
    print(f"  Card Creation: {'Success' if card_success else 'Failed'}")
    
    if data_success and card_success:
        print("\nAll tests passed! The issue might be in the callback or rendering logic.")
    else:
        print("\nSome tests failed. Check the specific errors above.")