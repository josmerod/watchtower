import requests
import json

url = "https://learn.microsoft.com/api/catalog/"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    # Check the keys
    keys = data.keys()
    print("Keys:", keys)
    if "modules" in data:
        print("Total modules:", len(data["modules"]))
    
    # We are looking for something like 'appliedSkills' or 'credentials' or similar
    
    # Let's inspect all items in 'appliedSkills' if it exists
    if "appliedSkills" in data:
        with open("test_skills.json", "w", encoding="utf-8") as f:
            json.dump(data["appliedSkills"][:5], f, indent=2)
        print(f"Saved {len(data['appliedSkills'])} skills. Wrote top 5 to test_skills.json")
else:
    print(f"Error: {response.status_code}")
