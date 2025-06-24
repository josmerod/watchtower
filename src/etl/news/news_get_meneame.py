"""Menéame Spanish Tech News ETL Module - Browser Automation Approach

This module fetches and processes news posts from Menéame,
a Spanish Reddit-like platform focused on technology and tech news.
Uses Playwright browser automation to handle dynamic content and anti-bot measures.

Usage:
    python src/etl/news/news_get_meneame.py

Output:
- JSON file: data/meneame/meneame_general_latest.json  
- CSV file: data/meneame/meneame_general_latest.csv
- JSON file: data/meneame/meneame_tecnologia_latest.json  
- CSV file: data/meneame/meneame_tecnologia_latest.csv
"""

import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import time
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from utils.logging import get_logger
from config.settings import get_settings

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()

# Constants
MENEAME_BASE_URL = "https://www.meneame.net"
MENEAME_TECH_URL = "https://www.meneame.net/m/tecnologia"
BASE_OUTPUT_DIR = "data/meneame"
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "debug")


class MeneameScraper:
    """Scraper for retrieving Menéame posts using browser automation.

    This class uses Playwright to scrape Menéame and handle dynamic content
    and anti-bot measures that block traditional HTTP requests.
    """

    def __init__(self, max_posts: int = 50) -> None:
        """Initialize the MeneameScraper.

        Args:
            max_posts: Maximum number of posts to scrape per section.
        """
        # Ensure base output directory exists
        project_root = settings.project_root or os.getcwd()
        self.output_dir = os.path.join(project_root, BASE_OUTPUT_DIR)
        os.makedirs(self.output_dir, exist_ok=True)

        # Ensure debug directory exists
        self.debug_dir = os.path.join(self.output_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

        # Define output files for both sections
        self.general_posts_file = os.path.join(self.output_dir, "meneame_general_latest.json")
        self.general_csv_file = os.path.join(self.output_dir, "meneame_general_latest.csv")
        
        self.tech_posts_file = os.path.join(self.output_dir, "meneame_tecnologia_latest.json")
        self.tech_csv_file = os.path.join(self.output_dir, "meneame_tecnologia_latest.csv")
        
        self.last_run_file = os.path.join(self.output_dir, "last_run_info.json")

        # Configuration
        self.max_posts = max_posts

    async def scrape_posts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape posts from both general and technology sections."""
        from bs4 import BeautifulSoup
        from playwright.async_api import async_playwright

        sections_data = {
            "general": [],
            "tecnologia": []
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                )
                # Stealth: mask automation to bypass detection
                await context.add_init_script(
                    "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
                )
                page = await context.new_page()

                # Visit the main site first to establish cookies
                logger.info("Visiting main site to establish cookies")
                await page.goto(MENEAME_BASE_URL, timeout=60000)
                await page.wait_for_timeout(3000)

                # Define sections to scrape
                sections_to_scrape = [
                    (MENEAME_BASE_URL, "general"),
                    (MENEAME_TECH_URL, "tecnologia"),
                ]

                for url, section_name in sections_to_scrape:
                    logger.info(f"Fetching {section_name} section: {url}")

                    try:
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(random.randint(3000, 6000))

                        # Save debug info for the first page
                        if section_name == "general":
                            debug_file = os.path.join(self.debug_dir, f"meneame_{section_name}.html")
                            debug_screenshot = os.path.join(self.debug_dir, f"meneame_{section_name}.png")
                            content = await page.content()
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            await page.screenshot(path=debug_screenshot)
                            logger.info(f"Saved debug info to {debug_file} and {debug_screenshot}")

                        # Extract page content
                        content = await page.content()
                        
                        # Parse content
                        soup = BeautifulSoup(content, "html.parser")

                        # Extract posts from this page
                        section_posts = self.extract_posts_from_page(soup, section_name)
                        logger.info(f"Found {len(section_posts)} posts in {section_name} section")
                        
                        # Limit posts per section
                        limited_posts = section_posts[:self.max_posts]
                        sections_data[section_name] = limited_posts

                    except Exception as e:
                        logger.error(f"Error processing {section_name} section: {e}")
                        continue

                await browser.close()

        except Exception as e:
            logger.error(f"Error in scrape_posts: {e}")

        # Remove duplicates within each section
        for section_name in sections_data:
            sections_data[section_name] = self.deduplicate_posts(sections_data[section_name])
        
        logger.info(f"Scraped {len(sections_data['general'])} general posts and {len(sections_data['tecnologia'])} technology posts")
        return sections_data

    def extract_posts_from_page(self, soup: BeautifulSoup, section: str) -> List[Dict[str, Any]]:
        """Extract posts from a Menéame page."""
        posts = []
        
        try:
            # Look for proper story containers - Menéame uses specific structure
            story_containers = []
            
            # Primary approach: Look for story containers with h2 titles
            stories_with_h2 = soup.find_all('div', class_=re.compile(r'story|news-item|item', re.I))
            
            for story in stories_with_h2:
                if hasattr(story, 'find'):
                    h2_title = story.find('h2')
                    if h2_title:
                        story_containers.append(story)
            
            logger.info(f"Found {len(story_containers)} stories with h2 titles")
            
            # Fallback: Look for direct h2 elements that might be story titles
            if len(story_containers) < 5:
                h2_elements = soup.find_all('h2')
                for h2 in h2_elements:
                    if hasattr(h2, 'find_parent'):
                        # Find the parent container that likely contains the full story
                        parent = h2.find_parent(['div', 'article', 'li'])
                        if parent and parent not in story_containers:
                            story_containers.append(parent)
                
                logger.info(f"Added {len(h2_elements)} h2-based containers")
            
            # Last resort: Look for links that look like story titles
            if len(story_containers) < 5:
                story_links = soup.find_all('a', href=True)
                for link in story_links:
                    if hasattr(link, 'get_text') and hasattr(link, 'get'):
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        # Filter for substantial titles
                        if (len(text) > 15 and len(text) < 200 and 
                            not any(skip in text.lower() for skip in [
                                'comentar', 'votar', 'usuario', 'login', 'menéame', 
                                'compartir', 'facebook', 'twitter', 'whatsapp'
                            ]) and
                            isinstance(href, str) and href.startswith(('http', '/'))):
                            
                            # Find parent container
                            if hasattr(link, 'find_parent'):
                                parent = link.find_parent(['div', 'article', 'li'])
                                if parent and parent not in story_containers:
                                    story_containers.append(parent)
                
                logger.info(f"Total story containers found: {len(story_containers)}")

            # Process each container to extract clean post data
            processed_count = 0
            for container in story_containers:
                if processed_count >= self.max_posts:
                    break
                    
                post_data = self.extract_post_data(container, section)
                if post_data and self.is_valid_post(post_data):
                    posts.append(post_data)
                    processed_count += 1

        except Exception as e:
            logger.error(f"Error extracting posts from {section} page: {e}")

        return posts
    
    def is_valid_post(self, post_data: Dict[str, Any]) -> bool:
        """Validate if a post has the minimum required data quality."""
        title = post_data.get('title', '')
        
        # Must have a reasonable title
        if not title or len(title) < 10 or len(title) > 300:
            return False
            
        # Filter out navigation/UI elements
        invalid_patterns = [
            'meneos', 'menéalo', 'clics', 'compartir', 'facebook', 'twitter',
            'publicado:', 'hace ', 'min', 'actualidad', 'cultura', 'politica',
            'user/', 'history'
        ]
        
        title_lower = title.lower()
        if any(pattern in title_lower for pattern in invalid_patterns):
            return False
            
        # Must not be just numbers and symbols
        if re.match(r'^[\d\s\-_.,;:!?]*$', title):
            return False
            
        return True

    def extract_post_data(self, container, section: str) -> Optional[Dict[str, Any]]:
        """Extract post data from a container element."""
        try:
            post_data = {}
            
            # Extract title and URL
            title_element = None
            url = None
            
            # Look for title in various ways
            if hasattr(container, 'find'):
                # Try h1, h2, h3 tags first
                for tag in ['h1', 'h2', 'h3']:
                    title_element = container.find(tag)
                    if title_element:
                        # Look for link inside the header tag
                        if hasattr(title_element, 'find'):
                            link_in_header = title_element.find('a', href=True)
                            if link_in_header and hasattr(link_in_header, 'get'):
                                url = link_in_header.get('href')
                                title_element = link_in_header  # Use the link as title element
                        break
                
                # Try links with substantial text and specific Menéame patterns
                if not title_element:
                    # Look for links with Menéame-specific classes (l:xxxxx pattern)
                    story_links = container.find_all('a', {'class': re.compile(r'l:\d+'), 'href': True})
                    if story_links:
                        title_element = story_links[0]
                        if hasattr(title_element, 'get'):
                            url = title_element.get('href')
                    else:
                        # Fallback to any substantial links
                        links = container.find_all('a', href=True)
                        for link in links:
                            if hasattr(link, 'get_text') and hasattr(link, 'get'):
                                text = link.get_text(strip=True)
                                href = link.get('href', '')
                                # Filter for story links (not navigation/UI)
                                if (len(text) > 15 and len(text) < 300 and 
                                    not any(skip in text.lower() for skip in [
                                        'comentar', 'votar', 'usuario', 'login', 'menéame', 
                                        'compartir', 'facebook', 'twitter', 'whatsapp',
                                        'meneos', 'clics', 'karma', 'publicado'
                                    ]) and
                                    isinstance(href, str) and 
                                    (href.startswith('http') or href.startswith('/story/'))):
                                    title_element = link
                                    url = href
                                    break
            
            # If container is a link itself
            if not title_element and hasattr(container, 'get_text'):
                text = container.get_text(strip=True)
                if len(text) > 10:
                    title_element = container
                    if hasattr(container, 'get') and container.get('href'):
                        url = container.get('href')
            
            if not title_element:
                return None
            
            # Extract title
            title = title_element.get_text(strip=True)
            if not title or len(title) < 5:
                return None
            
            post_data['title'] = title
            
            # Extract URL - improved logic
            if not url and hasattr(title_element, 'get'):
                url = title_element.get('href')
            
            # Look for parent/child links if still no URL
            if not url and hasattr(title_element, 'find_parent'):
                parent_link = title_element.find_parent('a')
                if parent_link and parent_link.get('href'):
                    url = parent_link.get('href')
            
            if not url and hasattr(title_element, 'find'):
                child_link = title_element.find('a', href=True)
                if child_link:
                    url = child_link.get('href')
            
            # Look in the broader container for story links
            if not url and hasattr(container, 'find_all'):
                # Try to find the actual source link (not Menéame internal links)
                all_links = container.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if href and not href.startswith('/') and href.startswith('http'):
                        # This looks like an external source URL
                        url = href
                        break
                
                # If still no external URL, look for Menéame story links
                if not url:
                    for link in all_links:
                        href = link.get('href', '')
                        if href.startswith('/story/'):
                            url = urljoin(MENEAME_BASE_URL, href)
                            break
            
            if url:
                if url.startswith('/'):
                    url = urljoin(MENEAME_BASE_URL, url)
                post_data['url'] = url
            
            # Extract description/summary
            if hasattr(container, 'find'):
                # Look for description in various places
                desc_element = None
                
                # Try news-content class (common in Menéame)
                desc_element = container.find(['div', 'p'], class_=re.compile(r'content|summary|description', re.I))
                
                if not desc_element:
                    # Try any paragraph
                    desc_element = container.find('p')
                
                if desc_element:
                    description = desc_element.get_text(strip=True)
                    if description and len(description) > 20:
                        post_data['description'] = description[:500]
            
            # Extract metadata
            post_data['source'] = 'meneame'
            post_data['section'] = section
            post_data['scraped_at'] = datetime.now().isoformat()
            
            # Try to extract votes/karma if available
            if hasattr(container, 'find'):
                # Look for vote elements
                vote_element = container.find(string=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ['votos', 'karma', 'puntos', 'meneos']
                ))
                if vote_element:
                    vote_text = str(vote_element).strip()
                    vote_match = re.search(r'(\d+)', vote_text)
                    if vote_match:
                        post_data['votes'] = int(vote_match.group(1))
                
                # Also try looking for specific vote classes
                vote_div = container.find(['div', 'span'], class_=re.compile(r'vote|karma|meneos', re.I))
                if vote_div and not post_data.get('votes'):
                    vote_text = vote_div.get_text(strip=True)
                    vote_match = re.search(r'(\d+)', vote_text)
                    if vote_match:
                        post_data['votes'] = int(vote_match.group(1))
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None

    def deduplicate_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate posts based on title similarity."""
        unique_posts = []
        seen_titles = set()
        
        for post in posts:
            title = post.get('title', '').lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_posts.append(post)
        
        return unique_posts

    def save_posts(self, sections_data: Dict[str, List[Dict[str, Any]]]) -> None:
        """Save scraped posts to JSON and CSV files."""
        if not sections_data:
            logger.warning("No sections data to save")
            return

        try:
            total_posts = 0
            
            # Save posts for each section
            for section_name, posts in sections_data.items():
                if not posts:
                    logger.warning(f"No posts to save for {section_name} section")
                    continue
                    
                posts_file = self.general_posts_file if section_name == "general" else self.tech_posts_file
                csv_file = self.general_csv_file if section_name == "general" else self.tech_csv_file
                
                # Save as JSON
                with open(posts_file, "w", encoding="utf-8") as f:
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved {len(posts)} posts to {posts_file}")
                
                # Save as CSV
                try:
                    import pandas as pd
                    
                    df = pd.DataFrame(posts)
                    df.to_csv(csv_file, index=False)
                    logger.info(f"Also saved posts to CSV: {csv_file}")
                except Exception as e:
                    logger.warning(f"Could not save {section_name} posts to CSV: {e}")
                
                total_posts += len(posts)

            # Update last run information
            last_run_info = {
                "timestamp": datetime.now().isoformat(),
                "general_posts_count": len(sections_data.get("general", [])),
                "tecnologia_posts_count": len(sections_data.get("tecnologia", [])),
                "total_posts_count": total_posts,
                "status": "success"
            }

            with open(self.last_run_file, "w", encoding="utf-8") as f:
                json.dump(last_run_info, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error saving posts: {e}")

    async def run(self) -> None:
        """Run the scraper asynchronously."""
        logger.info("Starting Menéame post scraper")
        sections_data = await self.scrape_posts()
        self.save_posts(sections_data)
        logger.info("Menéame post scraping completed")


async def main_async(max_posts: int = 50) -> None:
    """Asynchronous main entry point for the script."""
    logger.info("Starting Menéame post scraping process")

    try:
        scraper = MeneameScraper(max_posts=max_posts)
        await scraper.run()
        logger.info("Menéame post scraping completed successfully")
    except Exception as e:
        logger.error(f"Error during Menéame post scraping: {e}", exc_info=True)


def main(max_posts: int = 50) -> None:
    """Synchronous main entry point for the script."""
    try:
        # On Windows, use the ProactorEventLoop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main_async(max_posts=max_posts))
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Menéame posts using browser automation"
    )
    parser.add_argument(
        "--max-posts", type=int, help="Maximum number of posts to scrape", default=50
    )
    args = parser.parse_args()

    main(max_posts=args.max_posts)
    logger.info("Menéame scraper script completed")


 