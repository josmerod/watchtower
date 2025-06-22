"""Menéame Spanish Tech News ETL Module

This module fetches and processes news posts from Menéame,
a Spanish Reddit-like platform focused on technology and tech news.

Usage:
    python src/etl/news/news_get_meneame.py

Output:
- JSON file: data/meneame/posts.json  
- CSV file: data/meneame/posts.csv
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import re
from urllib.parse import urljoin, urlparse

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from utils.logging import get_logger
from config.settings import get_settings

# Initialize logger and settings
logger = get_logger("MeneameETL")
settings = get_settings()

# Menéame configuration
MENEAME_BASE_URL = "https://www.meneame.net"
MENEAME_TECH_URL = f"{MENEAME_BASE_URL}/queue/tecnologia"

# Request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.meneame.net/",
}


def fetch_meneame_posts(
    session: requests.Session,
    max_posts: int = 50,
    max_pages: int = 3
) -> List[Dict[str, Any]]:
    """Fetch tech posts from Menéame."""
    posts = []
    
    try:
        logger.info("Fetching posts from Menéame Tech section")
        
        for page in range(1, max_pages + 1):
            if len(posts) >= max_posts:
                break
                
            url = f"{MENEAME_TECH_URL}?page={page}" if page > 1 else MENEAME_TECH_URL
            
            logger.info(f"Scraping page {page}: {url}")
            
            response = session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find story containers
            story_containers = soup.find_all(['div', 'article'], class_=re.compile(r'story|item|news'))
            
            logger.info(f"Found {len(story_containers)} stories on page {page}")
            
            for container in story_containers:
                if len(posts) >= max_posts:
                    break
                
                post_data = parse_meneame_post(container, MENEAME_BASE_URL)
                if post_data:
                    posts.append(post_data)
            
            time.sleep(1)  # Rate limiting
        
        logger.info(f"Collected {len(posts)} posts from Menéame")
        return posts
        
    except Exception as e:
        logger.error(f"Error fetching Menéame posts: {e}")
        return posts


def parse_meneame_post(container, base_url: str) -> Optional[Dict[str, Any]]:
    """Parse a Menéame post container."""
    try:
        post_data = {}
        
        # Title and URL
        title_elem = container.find('h2') or container.find('h3') or container.find('a', class_=re.compile(r'title'))
        if title_elem:
            title_link = title_elem.find('a') if title_elem.name != 'a' else title_elem
            if title_link:
                post_data['title'] = title_link.get_text(strip=True)
                post_data['url'] = urljoin(base_url, title_link.get('href', ''))
            else:
                post_data['title'] = title_elem.get_text(strip=True)
                post_data['url'] = base_url
        else:
            return None
        
        # Description/summary
        desc_elem = container.find(['p', 'div'], class_=re.compile(r'summary|description|content'))
        if desc_elem:
            post_data['description'] = desc_elem.get_text(strip=True)[:400]
        else:
            post_data['description'] = ""
        
        # Votes (meneos)
        votes_elem = container.find(['span', 'div'], class_=re.compile(r'votes|meneos|karma'))
        if votes_elem:
            votes_text = votes_elem.get_text(strip=True)
            votes_match = re.search(r'(\d+)', votes_text)
            post_data['votes'] = int(votes_match.group(1)) if votes_match else 0
        else:
            post_data['votes'] = 0
        
        # Comments
        comments_elem = container.find(['a', 'span'], href=re.compile(r'comment')) or \
                       container.find(text=re.compile(r'\d+\s*comentario', re.I))
        if comments_elem:
            if hasattr(comments_elem, 'get_text'):
                comments_text = comments_elem.get_text()
            else:
                comments_text = str(comments_elem)
            
            comments_match = re.search(r'(\d+)', comments_text)
            post_data['comments_count'] = int(comments_match.group(1)) if comments_match else 0
        else:
            post_data['comments_count'] = 0
        
        # Author
        author_elem = container.find(['a', 'span'], class_=re.compile(r'user|author'))
        if author_elem:
            post_data['author'] = author_elem.get_text(strip=True)
        else:
            post_data['author'] = "Unknown"
        
        # Category/Tags
        tag_elem = container.find(['span', 'a'], class_=re.compile(r'tag|category'))
        if tag_elem:
            post_data['category'] = tag_elem.get_text(strip=True)
        else:
            post_data['category'] = "Tecnología"
        
        # Publication date
        date_elem = container.find(['time', 'span'], attrs={'datetime': True}) or \
                   container.find(['span', 'div'], class_=re.compile(r'date|time'))
        
        if date_elem:
            if date_elem.get('datetime'):
                date_str = date_elem.get('datetime')
            else:
                date_str = date_elem.get_text(strip=True)
            
            post_data['published_date'] = parse_spanish_date(date_str)
        else:
            post_data['published_date'] = datetime.now().isoformat()
        
        # Source domain
        if post_data.get('url'):
            try:
                parsed_url = urlparse(post_data['url'])
                post_data['source_domain'] = parsed_url.netloc
            except:
                post_data['source_domain'] = "meneame.net"
        else:
            post_data['source_domain'] = "meneame.net"
        
        # Add metadata
        post_data.update({
            "source": "meneame",
            "platform": "meneame",
            "language": "es"
        })
        
        return post_data
        
    except Exception as e:
        logger.error(f"Error parsing Menéame post: {e}")
        return None


def parse_spanish_date(date_str: str) -> str:
    """Parse Spanish date formats."""
    if not date_str:
        return datetime.now().isoformat()
    
    # Spanish month names
    spanish_months = {
        'enero': 'January', 'febrero': 'February', 'marzo': 'March',
        'abril': 'April', 'mayo': 'May', 'junio': 'June',
        'julio': 'July', 'agosto': 'August', 'septiembre': 'September',
        'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
    }
    
    # Replace Spanish months with English
    date_str_en = date_str.lower()
    for es_month, en_month in spanish_months.items():
        date_str_en = date_str_en.replace(es_month, en_month)
    
    # Common patterns
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d de %B de %Y",
        "%d %B %Y"
    ]
    
    for pattern in patterns:
        try:
            if 'de' in date_str_en:
                date_str_en = re.sub(r'\s+de\s+', ' ', date_str_en)
            
            parsed_date = datetime.strptime(date_str_en, pattern)
            return parsed_date.isoformat()
        except ValueError:
            continue
    
    return datetime.now().isoformat()


def process_meneame_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and enrich Menéame posts."""
    if not posts:
        return []
    
    logger.info(f"Processing {len(posts)} Menéame posts")
    
    # Tech keywords for better categorization
    tech_keywords = {
        'ai': ['ia', 'inteligencia artificial', 'machine learning', 'deep learning'],
        'programming': ['programación', 'código', 'desarrollo', 'software'],
        'web': ['web', 'internet', 'navegador', 'html', 'css', 'javascript'],
        'mobile': ['móvil', 'android', 'ios', 'app', 'aplicación'],
        'security': ['seguridad', 'hack', 'ciberseguridad', 'privacidad'],
        'hardware': ['hardware', 'procesador', 'gpu', 'memoria'],
        'social': ['redes sociales', 'facebook', 'twitter', 'instagram'],
        'gaming': ['videojuegos', 'gaming', 'consola', 'pc gaming'],
        'startup': ['startup', 'empresa', 'tecnológica', 'innovación']
    }
    
    processed_posts = []
    
    for post in posts:
        try:
            processed_post = post.copy()
            
            # Enhanced categorization
            title_lower = post.get('title', '').lower()
            desc_lower = post.get('description', '').lower()
            content = f"{title_lower} {desc_lower}"
            
            category_scores = {}
            for category, keywords in tech_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content)
                if score > 0:
                    category_scores[category] = score
            
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                processed_post['tech_category'] = best_category
            else:
                processed_post['tech_category'] = 'general'
            
            # Engagement score
            votes = post.get('votes', 0)
            comments = post.get('comments_count', 0)
            
            engagement_score = votes * 1.5 + comments * 2
            
            # Quality bonuses
            title_len = len(post.get('title', ''))
            if 20 <= title_len <= 100:
                engagement_score += 2
            
            if post.get('description') and len(post['description']) > 50:
                engagement_score += 3
            
            processed_post['engagement_score'] = round(engagement_score, 1)
            
            # Trending detection (high votes relative to comments)
            if votes > 20 and comments > 5:
                processed_post['trending'] = True
            else:
                processed_post['trending'] = False
            
            # Content quality score
            quality_score = 0
            
            if votes > 10:
                quality_score += 2
            if comments > 3:
                quality_score += 2
            if post.get('source_domain') and 'meneame' not in post['source_domain']:
                quality_score += 1  # External link bonus
            
            processed_post['quality_score'] = quality_score
            processed_post['processed_at'] = datetime.now().isoformat()
            
            processed_posts.append(processed_post)
            
        except Exception as e:
            logger.error(f"Error processing post {post.get('title', 'Unknown')}: {e}")
            processed_posts.append(post)
    
    logger.info(f"Successfully processed {len(processed_posts)} Menéame posts")
    return processed_posts


def save_meneame_data(data: List[Dict[str, Any]], output_dir: str):
    """Save Menéame data to files."""
    if not data:
        logger.warning("No data to save")
        return
    
    try:
        # JSON
        json_file = os.path.join(output_dir, "meneame_posts.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {len(data)} posts to {json_file}")
        
        # CSV
        csv_file = os.path.join(output_dir, "meneame_posts.csv")
        if data:
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"Saved {len(data)} posts to {csv_file}")
            
    except Exception as e:
        logger.error(f"Error saving data: {e}")


def main():
    """Main ETL process for Menéame."""
    logger.info("Starting Menéame ETL process")
    
    try:
        # Setup
        project_root = Path(__file__).parent.parent.parent.parent
        output_dir = os.path.join(project_root, "data", "meneame")
        os.makedirs(output_dir, exist_ok=True)
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Fetch posts
        posts = fetch_meneame_posts(session, max_posts=40)
        
        if not posts:
            logger.warning("No posts fetched from Menéame")
            return
        
        # Process
        processed_data = process_meneame_posts(posts)
        
        # Save
        save_meneame_data(processed_data, output_dir)
        
        # Summary
        logger.info(f"Menéame ETL completed! Processed {len(processed_data)} posts")
        
        if processed_data:
            avg_votes = sum(p.get('votes', 0) for p in processed_data) / len(processed_data)
            total_comments = sum(p.get('comments_count', 0) for p in processed_data)
            
            logger.info(f"Average votes: {avg_votes:.1f}")
            logger.info(f"Total comments: {total_comments}")
            
            # Category breakdown
            categories = {}
            for post in processed_data:
                cat = post.get('tech_category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            logger.info("Tech categories:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"  {cat}: {count} posts")
    
    except Exception as e:
        logger.error(f"Menéame ETL failed: {e}")
        raise


 