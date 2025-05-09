import json
import os
from collections import Counter

def analyze_bundles():
    """Analyze the Humble Bundle data from the JSON file."""
    try:
        # Load the JSON data
        with open('data/games/humblebundles.json', 'r', encoding='utf-8') as f:
            bundles = json.load(f)
        
        print(f"Total bundles found: {len(bundles)}")
        
        # Count bundle types
        bundle_types = Counter(bundle.get('type', 'unknown') for bundle in bundles)
        print("\nBundle types:")
        for bundle_type, count in bundle_types.items():
            print(f"- {bundle_type}: {count}")
        
        # Check for title issues
        generic_titles = sum(1 for bundle in bundles if bundle.get('title') == 'Pay What You Want')
        if generic_titles > 0:
            print(f"\nWarning: {generic_titles} bundles have generic 'Pay What You Want' titles")
        
        # Print first 5 bundles
        print("\nSample of bundles (first 5):")
        for i, bundle in enumerate(bundles[:5]):
            print(f"\n{i+1}. {bundle.get('title', 'No Title')}")
            print(f"   Type: {bundle.get('type', 'unknown')}")
            print(f"   Link: {bundle.get('link', 'No Link')}")
            print(f"   Price: {bundle.get('price', 'Unknown')}")
            games = bundle.get('games', [])
            if games:
                print(f"   Games: {len(games)} games")
                for game in games[:3]:
                    print(f"     - {game}")
                if len(games) > 3:
                    print(f"     - ... and {len(games) - 3} more")
            else:
                print("   Games: None found")
        
        return True
    
    except Exception as e:
        print(f"Error analyzing bundles: {e}")
        return False

if __name__ == "__main__":
    analyze_bundles() 