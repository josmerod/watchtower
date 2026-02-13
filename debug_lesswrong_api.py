
import requests
import json
from datetime import datetime

def query_lesswrong():
    url = "https://www.lesswrong.com/graphql"
    query = """
    {
      posts(input: { terms: { view: "new", limit: 10 } }) {
        results {
          _id
          title
          pageUrl
          postedAt
          baseScore
          commentCount
          author
          tags {
            name
            slug
          }
          htmlBody
        }
      }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Watchtower/1.0"
    }
    
    try:
        response = requests.post(url, json={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Pretty print results
        if "data" in data and "posts" in data["data"]:
            posts = data["data"]["posts"]["results"]
            print(f"Successfully fetched {len(posts)} posts")
            print("-" * 50)
            for post in posts[:3]:
                print(f"Title: {post.get('title')}")
                print(f"Score: {post.get('baseScore')} | Comments: {post.get('commentCount')}")
                print(f"URL: https://www.lesswrong.com{post.get('pageUrl')}")
                print(f"Date: {post.get('postedAt')}")
                print("-" * 50)
            return True
        else:
            print("Unexpected response structure:")
            print(json.dumps(data, indent=2))
            return False
            
    except Exception as e:
        print(f"Error querying GraphQL: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response content: {e.response.text}")
        return False

if __name__ == "__main__":
    query_lesswrong()
