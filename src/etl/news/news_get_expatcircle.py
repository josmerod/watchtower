"""ExpatCircle News ETL Module

This module fetches and processes news posts from ExpatCircle News,
which is a news aggregation site similar to Hacker News focused on expat community content.

Usage:
    python src/etl/news/news_get_expatcircle.py

Output:
    - JSON file: data/expatcircle/posts.json
    - CSV file: data/expatcircle/posts.csv
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("ExpatCircleETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers to mimic a real browser
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://news.expatcircle.com/",
        }
    )

    return session


def fetch_expatcircle_posts(
    session: requests.Session, max_posts: int = 50
) -> List[Dict[str, Any]]:
    """Fetch posts from ExpatCircle News main page.

    Args:
        session: Requests session with retry configuration
        max_posts: Maximum number of posts to fetch

    Returns:
        List of post dictionaries
    """
    base_url = "https://news.expatcircle.com"
    posts = []

    try:
        logger.info("Fetching posts from ExpatCircle News")
        response = session.get(f"{base_url}/en/", timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all post entries - based on the structure observed
        post_elements = soup.find_all('tr')  # Posts appear to be in table rows
        
        posts_found = 0
        
        for element in post_elements:
            if posts_found >= max_posts:
                break
                
            try:
                # Extract post data from table row
                post_data = parse_post_element(element, base_url)
                if post_data:
                    posts.append(post_data)
                    posts_found += 1

            except Exception as e:
                logger.warning(f"Error parsing post element: {e}")
                continue

        logger.info(f"Found {len(posts)} posts from ExpatCircle News")
        return posts

    except Exception as e:
        logger.error(f"Error fetching ExpatCircle posts: {e}")
        return []


def parse_post_element(element, base_url: str) -> Dict[str, Any]:
    """Parse a post element from the ExpatCircle News page.
    
    Args:
        element: BeautifulSoup element representing a post
        base_url: Base URL for resolving relative URLs
        
    Returns:
        Post dictionary or None if parsing fails
    """
    try:
        # Look for links in the element
        links = element.find_all('a')
        if not links:
            return None
            
        # Find the main article link (usually the first meaningful one)
        main_link = None
        title = ""
        post_url = ""
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip empty links or navigation links
            if not text or not href:
                continue
                
            # Skip certain types of links
            if any(skip in href.lower() for skip in ['/en/profile/', '/en/site/', 'delete', 'edit']):
                continue
                
            # This looks like a main article link
            if text and len(text) > 10:  # Reasonable title length
                main_link = link
                title = text
                post_url = urljoin(base_url, href) if not href.startswith('http') else href
                break
        
        if not main_link or not title:
            return None
            
        # Extract additional metadata from the row
        points = 0
        comments_count = 0
        author = ""
        site_domain = ""
        
        # Look for points/votes pattern
        text_content = element.get_text()
        points_match = re.search(r'(\d+)\s*point', text_content)
        if points_match:
            points = int(points_match.group(1))
        
        # Look for "by" pattern for author
        by_match = re.search(r'by\s+([^\s]+)', text_content)
        if by_match:
            author = by_match.group(1)
            
        # Look for "discuss" or comments pattern
        discuss_links = element.find_all('a', href=re.compile(r'/en/post/\d+/'))
        discuss_url = ""
        if discuss_links:
            discuss_url = urljoin(base_url, discuss_links[0].get('href', ''))
            
        # Extract site domain if it's an external link
        if post_url.startswith('http'):
            parsed_url = urlparse(post_url)
            site_domain = parsed_url.netloc
            
        # Extract timestamp if available
        time_elements = element.find_all(string=re.compile(r'\d+\s+(day|hour|minute)s?\s+ago'))
        posted_time = ""
        if time_elements:
            posted_time = time_elements[0].strip()

        return {
            "id": hash(title + post_url) % 1000000,  # Generate a simple ID
            "title": title,
            "url": post_url,
            "author": author,
            "points": points,
            "comments_count": comments_count,
            "discuss_url": discuss_url,
            "site_domain": site_domain,
            "posted_time": posted_time,
            "fetched_at": datetime.now().isoformat(),
            "platform": "expatcircle"
        }

    except Exception as e:
        logger.warning(f"Error parsing post element: {e}")
        return None


def process_expatcircle_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and enrich ExpatCircle posts with additional metrics and categorization.

    Args:
        posts: List of raw post dictionaries

    Returns:
        List of processed and enriched post data
    """
    logger.info(f"Processing {len(posts)} ExpatCircle posts")

    processed_posts = []
    current_time = datetime.now()

    for post in posts:
        try:
            # Calculate engagement score
            points = post.get("points", 0)
            comments_count = post.get("comments_count", 0)
            engagement_score = points + (comments_count * 1.5)

            # Categorize the post based on title and domain
            title = post.get("title", "").lower()
            domain = post.get("site_domain", "").lower()
            
            category = categorize_post(title, domain)
            
            # Determine content type
            content_type = "external_link" if post.get("site_domain") else "discussion"
            
            # Calculate priority score based on multiple factors
            priority_score = calculate_priority_score(
                points, comments_count, category, content_type
            )

            processed_post = {
                **post,
                "engagement_score": engagement_score,
                "category": category,
                "content_type": content_type,
                "priority_score": round(priority_score, 2),
                "is_trending": engagement_score >= 20,  # Lower threshold than HN
                "is_discussion": content_type == "discussion",
                "processed_at": datetime.now().isoformat(),
            }

            processed_posts.append(processed_post)

        except Exception as e:
            logger.warning(f"Error processing post {post.get('id', 'unknown')}: {e}")
            continue

    # Sort by priority score
    processed_posts.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_posts)} ExpatCircle posts")
    return processed_posts


def categorize_post(title: str, domain: str) -> str:
    """Categorize a post based on its title and domain.
    
    Args:
        title: Post title
        domain: Site domain
        
    Returns:
        Category string
    """
    title_lower = title.lower()
    
    # Expat and living abroad categories
    if any(keyword in title_lower for keyword in [
        'expat', 'expatriate', 'abroad', 'immigration', 'visa', 'relocat', 'moving'
    ]):
        return 'expat_life'
    
    # Travel and destinations
    if any(keyword in title_lower for keyword in [
        'travel', 'destination', 'country', 'city', 'vacation', 'tourism'
    ]):
        return 'travel'
    
    # Work and career
    if any(keyword in title_lower for keyword in [
        'job', 'work', 'career', 'employment', 'salary', 'remote work'
    ]):
        return 'career'
    
    # Finance and economics
    if any(keyword in title_lower for keyword in [
        'economy', 'finance', 'money', 'bank', 'tax', 'invest', 'cost of living'
    ]):
        return 'finance'
    
    # Culture and society
    if any(keyword in title_lower for keyword in [
        'culture', 'society', 'language', 'local', 'community', 'tradition'
    ]):
        return 'culture'
    
    # Technology and digital nomad
    if any(keyword in title_lower for keyword in [
        'tech', 'digital', 'nomad', 'internet', 'online', 'startup'
    ]):
        return 'technology'
    
    # Health and lifestyle
    if any(keyword in title_lower for keyword in [
        'health', 'lifestyle', 'insurance', 'medical', 'wellbeing'
    ]):
        return 'health_lifestyle'
    
    # Politics and news
    if any(keyword in title_lower for keyword in [
        'politic', 'government', 'policy', 'election', 'news', 'war'
    ]):
        return 'politics_news'
    
    return 'general'


def calculate_priority_score(
    points: int, comments_count: int, category: str, content_type: str
) -> float:
    """Calculate priority score for a post.
    
    Args:
        points: Number of points/votes
        comments_count: Number of comments
        category: Post category
        content_type: Type of content
        
    Returns:
        Priority score
    """
    base_score = points * 2 + comments_count * 3
    
    # Category multipliers
    category_multipliers = {
        'expat_life': 1.3,
        'travel': 1.2,
        'career': 1.2,
        'technology': 1.1,
        'finance': 1.1,
        'general': 1.0,
        'politics_news': 0.9,
    }
    
    category_multiplier = category_multipliers.get(category, 1.0)
    
    # Content type multiplier
    content_multiplier = 1.1 if content_type == "discussion" else 1.0
    
    return base_score * category_multiplier * content_multiplier


def save_data(data: List[Dict[str, Any]], output_dir: str) -> Dict[str, str]:
    """Save processed data to JSON and CSV files.
    
    Args:
        data: Processed post data
        output_dir: Output directory path
        
    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])
    
    file_paths = {}
    
    # Save as JSON
    json_file = os.path.join(output_dir, "expatcircle_posts.json")
    with open(json_file, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    file_paths["json"] = json_file
    logger.info(f"Saved JSON data to {json_file}")
    
    # Save as CSV
    try:
        import pandas as pd
        csv_file = os.path.join(output_dir, "expatcircle_posts.csv")
        
        # Flatten the data for CSV
        df_data = []
        for post in data:
            flat_post = {k: v for k, v in post.items() if not isinstance(v, (dict, list))}
            df_data.append(flat_post)
        
        df = pd.DataFrame(df_data)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        file_paths["csv"] = csv_file
        logger.info(f"Saved CSV data to {csv_file}")
        
    except ImportError:
        logger.warning("pandas not available, skipping CSV export")
    except Exception as e:
        logger.error(f"Error saving CSV: {e}")
    
    return file_paths


def main():
    """Main function to run the ExpatCircle News ETL process."""
    logger.info("Starting ExpatCircle News ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "expatcircle")
        session = create_session()

        # Fetch data
        logger.info("Fetching ExpatCircle News posts")
        posts = fetch_expatcircle_posts(session, max_posts=50)

        if not posts:
            logger.warning("No posts fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching ExpatCircle data")
        processed_data = process_expatcircle_posts(posts)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_posts = len(processed_data)
        trending_posts = len([p for p in processed_data if p.get("is_trending", False)])
        discussion_posts = len([p for p in processed_data if p.get("is_discussion", False)])

        logger.info("ExpatCircle News ETL completed successfully!")
        logger.info(f"Total posts: {total_posts}")
        logger.info(f"Trending posts: {trending_posts}")
        logger.info(f"Discussion posts: {discussion_posts}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print category distribution
        if processed_data:
            categories = [p.get("category", "Unknown") for p in processed_data]
            from collections import Counter
            top_categories = Counter(categories).most_common(5)
            logger.info(f"Top categories: {top_categories}")

    except Exception as e:
        logger.error(f"ExpatCircle News ETL failed: {e}")
        raise


if __name__ == "__main__":
    main() 