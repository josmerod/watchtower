import json
from pathlib import Path

file_path = Path(r"c:\Users\josem\watchtower\data\shortcuts\predefined_shortcuts.json")


def load_data():
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


new_shortcuts = {
    "Development Tools": [
        {"name": "Ray.so", "url": "https://ray.so/", "icon": "📸", "description": "Create beautiful code images"},
        {"name": "JSON Hero", "url": "https://jsonhero.io/", "icon": "🦸", "description": "JSON viewer and explorer"},
    ],
    "Documentation & References": [{"name": "DevDocs", "url": "https://devdocs.io/", "icon": "📚", "description": "Combined API documentation"}],
    "AI & Machine Learning": [
        {"name": "ArXiv Sanity", "url": "http://www.arxiv-sanity.com/", "icon": "🧠", "description": "Curated ArXiv papers"},
        {"name": "FutureTools", "url": "https://www.futuretools.io/", "icon": "🛠️", "description": "Directory of AI tools"},
        {"name": "Hugging Face Spaces", "url": "https://huggingface.co/spaces", "icon": "🤗", "description": "Host and demo ML apps"},
    ],
    "Development Communities": [{"name": "TLDR Newsletter", "url": "https://tldr.tech/", "icon": "📧", "description": "Daily tech news summary"}],
    "Design & UI/UX": [{"name": "Excalidraw", "url": "https://excalidraw.com/", "icon": "✏️", "description": "Virtual whiteboard"}],
    "Productivity": [
        {"name": "Notion", "url": "https://www.notion.so/", "icon": "📓", "description": "All-in-one workspace"},
        {"name": "Toggl Track", "url": "https://toggl.com/track/", "icon": "⏱️", "description": "Time tracking tool"},
        {"name": "TinyWow", "url": "https://tinywow.com/", "icon": "🛠️", "description": "Free PDF, video, image tools"},
    ],
    "Valencia Tech": [
        {"name": "Startup Valencia", "url": "https://startupvalencia.org/", "icon": "🚀", "description": "Local startup ecosystem"},
        {"name": "VLCTechHub Slack", "url": "https://vlctechhub.org/slack/", "icon": "💬", "description": "Local tech community chat"},
    ],
}

data = load_data()

# Merge Logic
for category, items in new_shortcuts.items():
    if category not in data:
        data[category] = []

    existing_urls = {item["url"] for item in data[category]}

    for item in items:
        if item["url"] not in existing_urls:
            print(f"Adding {item['name']} to {category}")
            data[category].append(item)
        else:
            print(f"Skipping {item['name']} (already exists)")

save_data(data)
print("Done updating shortcuts.")
