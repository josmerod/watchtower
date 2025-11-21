"""Product Hunt ETL Module

This module fetches and processes product launches, trending products, and innovation data
from Product Hunt using their GraphQL API. It tracks startup innovations and product trends.

Usage:
    python src/etl/news/news_get_producthunt.py

Output:
    - JSON file: data/product_hunt/product_hunt_latest.json
    - CSV file: data/product_hunt/product_hunt_latest.csv
"""

import csv
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models.news import ProductHuntModel

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("ProductHuntETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (Product Innovation Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def get_graphql_query() -> str:
    """GraphQL query to fetch Product Hunt posts with comprehensive data.

    Returns:
        GraphQL query string
    """
    return """
    query GetPosts($cursor: String, $first: Int) {
        posts(first: $first, after: $cursor, order: VOTES) {
            edges {
                node {
                    id
                    name
                    tagline
                    description
                    url
                    slug
                    votesCount
                    commentsCount
                    featuredAt
                    createdAt
                    updatedAt
                    website
                    redirect
                    reviewsCount
                    reviewsRating
                    thumbnail {
                        url
                    }
                    gallery {
                        images {
                            url
                        }
                    }
                    topics {
                        edges {
                            node {
                                name
                                slug
                                description
                                followersCount
                                postsCount
                            }
                        }
                    }
                    makers {
                        edges {
                            node {
                                id
                                name
                                username
                                headline
                                profileImage
                                twitterUsername
                                website
                                followersCount
                                followingCount
                                postsCount
                                madeBadgeVisible
                                isFollowed
                                isMaker
                                isViewer
                            }
                        }
                    }
                    hunters {
                        edges {
                            node {
                                id
                                name
                                username
                                headline
                                profileImage
                                twitterUsername
                                website
                                followersCount
                                followingCount
                                postsCount
                            }
                        }
                    }
                    productLinks {
                        type
                        url
                    }
                    user {
                        id
                        name
                        username
                        headline
                        profileImage
                        twitterUsername
                        website
                        followersCount
                        followingCount
                        postsCount
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """


def fetch_product_hunt_data(
    session: requests.Session, max_products: int = 500
) -> list[dict[str, Any]]:
    """Fetch products from Product Hunt using GraphQL API.

    Args:
        session: Requests session with retry configuration
        max_products: Maximum number of products to fetch

    Returns:
        List of product dictionaries
    """
    graphql_url = "https://www.producthunt.com/frontend/graphql"

    # Note: Product Hunt requires authentication for full API access
    # For demonstration, we'll use web scraping as fallback
    logger.info(
        "Attempting to fetch Product Hunt data via web scraping (GraphQL requires auth)"
    )

    return scrape_product_hunt_data(session, max_products)


def scrape_product_hunt_data(
    session: requests.Session, max_products: int = 500
) -> list[dict[str, Any]]:
    """Scrape Product Hunt data from their public pages.

    Args:
        session: Requests session with retry configuration
        max_products: Maximum number of products to fetch

    Returns:
        List of product dictionaries
    """
    base_url = "https://www.producthunt.com"
    all_products = []
    seen_urls = set()

    # Popular topics to track
    topics = [
        "ai",
        "developer-tools",
        "saas",
        "productivity",
        "fintech",
        "health-fitness",
        "social-media",
        "e-commerce",
        "marketing",
        "design",
        "analytics",
        "automation",
        "blockchain",
        "cybersecurity",
        "education",
        "travel",
    ]

    try:
        # Scrape today's featured products
        logger.info("Scraping today's featured products")
        today_products = scrape_daily_products(session, base_url)
        for product in today_products:
            if product.get("url") not in seen_urls:
                seen_urls.add(product.get("url", ""))
                all_products.append(product)

        # Scrape topic-based products
        for topic in topics[:8]:  # Limit to avoid rate limiting
            if len(all_products) >= max_products:
                break

            logger.info(f"Scraping products for topic: {topic}")
            topic_products = scrape_topic_products(session, base_url, topic)

            for product in topic_products:
                if len(all_products) >= max_products:
                    break
                if product.get("url") not in seen_urls:
                    seen_urls.add(product.get("url", ""))
                    all_products.append(product)

            time.sleep(3)  # Rate limiting

        logger.info(f"Total products scraped: {len(all_products)}")
        return all_products

    except Exception as e:
        logger.error(f"Error scraping Product Hunt data: {e}")
        return []


def scrape_daily_products(
    session: requests.Session, base_url: str
) -> list[dict[str, Any]]:
    """Scrape today's featured products from Product Hunt.

    Args:
        session: Requests session
        base_url: Product Hunt base URL

    Returns:
        List of product dictionaries
    """
    try:
        response = session.get(base_url, timeout=30, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        products = []

        # Look for product containers with updated and more flexible selectors
        product_items = []
        
        # Try multiple selector strategies
        selectors_to_try = [
            # Modern Product Hunt selectors (2025)
            ("div", {"data-test": "homepage-section-item"}),
            ("div", {"data-test": "post-item"}),
            ("li", {"data-test": "post-item"}),
            ("article", None),
            
            # CSS class-based selectors (more flexible)
            ("div", lambda x: x and "styles_item" in x.lower()),
            ("div", lambda x: x and "post" in x.lower() and "item" in x.lower()),
            ("div", lambda x: x and "product" in x.lower()),
            ("li", lambda x: x and "item" in x.lower()),
            
            # General structure-based selectors
            ("div", lambda x: x and any(keyword in x.lower() for keyword in ["card", "tile", "item", "post"]) if x else False),
        ]
        
        for tag, selector in selectors_to_try:
            if selector is None:
                items = soup.find_all(tag)
            elif isinstance(selector, dict):
                items = soup.find_all(tag, selector)
            else:
                items = soup.find_all(tag, class_=selector)
            
            if items:
                product_items = items
                logger.info(f"Found {len(items)} potential product items using selector: {tag} with {type(selector).__name__}")
                break
        
        # If no structured items found, try finding any links that might be products
        if not product_items:
            logger.warning("No structured product items found, trying generic link extraction")
            all_links = soup.find_all("a", href=True)
            # Filter for product-like links
            product_links = []
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if (href.startswith("/posts/") or "product" in href.lower()) and text and len(text) > 5:
                    product_links.append(link.parent if link.parent else link)
            product_items = product_links[:20]  # Limit to prevent over-scraping
            
            if product_items:
                logger.info(f"Found {len(product_items)} product-like links as fallback")
            else:
                logger.warning("No product items found at all - website structure may have changed significantly")
                
                # Debug: Save HTML snippet for investigation (first 5000 chars)
                html_snippet = str(soup)[:5000]
                logger.debug(f"HTML structure sample: {html_snippet}")
                
                # Try to find any meaningful content
                all_divs = soup.find_all("div")[:50]  # First 50 divs
                logger.info(f"Found {len(all_divs)} div elements on page")
                
                # Look for any text that might indicate products
                page_text = soup.get_text()
                if any(word in page_text.lower() for word in ["product", "launch", "vote", "maker"]):
                    logger.info("Page contains product-related text, selectors might be the issue")
                else:
                    logger.warning("Page doesn't contain expected product-related content")

        for item in product_items[:20]:  # Limit to 20 products
            try:
                # Extract product name with more flexible selectors
                name_elem = (
                    item.find("h3")
                    or item.find("h2") 
                    or item.find("h4")
                    or item.find("h1")
                    or item.find("a", class_=lambda x: x and "name" in x.lower() if x else False)
                    or item.find("span", class_=lambda x: x and "name" in x.lower() if x else False)
                    or item.find("div", class_=lambda x: x and "title" in x.lower() if x else False)
                )
                
                # If no structured name element, try to get the most prominent text
                if not name_elem:
                    # Look for the first link with substantial text
                    links_with_text = [a for a in item.find_all("a", href=True) if len(a.get_text(strip=True)) > 5]
                    if links_with_text:
                        name_elem = links_with_text[0]
                    else:
                        # Get any significant text from the item
                        texts = [elem for elem in item.find_all(text=True) if len(elem.strip()) > 5]
                        name = texts[0].strip() if texts else "No Title"
                
                name = name_elem.get_text(strip=True) if name_elem and hasattr(name_elem, 'get_text') else (name_elem if isinstance(name_elem, str) else "No Title")

                # Extract link with better fallback logic
                link_elem = item.find("a", href=True)
                if not link_elem and hasattr(item, 'get'):
                    # If item itself is a link
                    link = item.get("href", "") if item.name == "a" else ""
                else:
                    link = link_elem["href"] if link_elem else ""
                
                if link and not link.startswith("http"):
                    link = base_url + link
                
                # If no direct link found, try to construct from product name
                if not link and name and name != "No Title":
                    # Try to find any link in the item that might lead to the product
                    all_links = item.find_all("a", href=True)
                    for potential_link in all_links:
                        href = potential_link.get("href", "")
                        if "/posts/" in href or "product" in href.lower():
                            link = base_url + href if not href.startswith("http") else href
                            break

                # Extract tagline/description
                desc_elem = item.find("p") or item.find(
                    "div", class_=lambda x: x and "tagline" in x.lower() if x else False
                )
                tagline = desc_elem.get_text(strip=True) if desc_elem else ""

                # Extract vote count
                vote_elem = item.find(
                    "span", class_=lambda x: x and "vote" in x.lower() if x else False
                ) or item.find(
                    "div", class_=lambda x: x and "vote" in x.lower() if x else False
                )
                votes = 0
                if vote_elem:
                    vote_text = vote_elem.get_text(strip=True)
                    try:
                        votes = int("".join(filter(str.isdigit, vote_text)))
                    except ValueError:
                        votes = 0

                if name and name != "No Title":
                    product = {
                        "id": f"ph_product_{len(products)}",
                        "name": name,
                        "tagline": tagline,
                        "description": tagline,
                        "url": link,
                        "website": link,
                        "slug": name.lower().replace(" ", "-"),
                        "votes_count": votes,
                        "comments_count": 0,
                        "reviews_count": 0,
                        "reviews_rating": 0.0,
                        "featured_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "thumbnail_url": "",
                        "gallery_images": [],
                        "topics": ["featured"],
                        "makers": [],
                        "hunters": [],
                        "product_links": (
                            [{"type": "website", "url": link}] if link else []
                        ),
                        "category": "featured",
                        "mock_data": False,
                    }
                    products.append(product)
            except Exception as e:
                logger.warning(f"Error parsing product item: {e}")
                continue

        logger.info(f"Scraped {len(products)} products from daily page")
        return products

    except Exception as e:
        logger.error(f"Error scraping daily products: {e}")
        return []


def scrape_topic_products(
    session: requests.Session, base_url: str, topic: str
) -> list[dict[str, Any]]:
    """Scrape products from a specific topic page.

    Args:
        session: Requests session
        base_url: Product Hunt base URL
        topic: Topic to scrape

    Returns:
        List of product dictionaries
    """
    try:
        topic_url = f"{base_url}/topics/{topic}"
        response = session.get(topic_url, timeout=30, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        products = []

        # Look for product containers in topic pages with flexible selectors
        product_items = []
        
        # Try multiple selector strategies for topic pages
        selectors_to_try = [
            # Topic-specific selectors
            ("div", {"data-test": "post-item"}),
            ("li", {"data-test": "post-item"}),
            ("article", None),
            
            # CSS class-based selectors
            ("div", lambda x: x and "styles_item" in x.lower()),
            ("div", lambda x: x and "post" in x.lower()),
            ("div", lambda x: x and "product" in x.lower()),
            ("li", lambda x: x and "item" in x.lower()),
            
            # General selectors
            ("div", lambda x: x and any(keyword in x.lower() for keyword in ["card", "tile", "item"]) if x else False),
        ]
        
        for tag, selector in selectors_to_try:
            if selector is None:
                items = soup.find_all(tag)
            elif isinstance(selector, dict):
                items = soup.find_all(tag, selector)
            else:
                items = soup.find_all(tag, class_=selector)
            
            if items:
                product_items = items
                logger.info(f"Found {len(items)} topic product items using selector: {tag}")
                break
        
        # Fallback for topic pages
        if not product_items:
            logger.warning(f"No structured items found for topic {topic}, trying link extraction")
            all_links = soup.find_all("a", href=True)
            product_links = []
            for link in all_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if (href.startswith("/posts/") or "product" in href.lower()) and text and len(text) > 5:
                    product_links.append(link.parent if link.parent else link)
            product_items = product_links[:15]
            
            if product_items:
                logger.info(f"Found {len(product_items)} product-like links for topic {topic}")
            else:
                logger.warning(f"No items found for topic {topic}")

        for item in product_items[:15]:  # Limit to 15 products per topic
            try:
                # Extract product name
                name_elem = (
                    item.find("h3")
                    or item.find("h2")
                    or item.find(
                        "a", class_=lambda x: x and "name" in x.lower() if x else False
                    )
                )
                name = name_elem.get_text(strip=True) if name_elem else "No Title"

                # Extract link
                link_elem = item.find("a", href=True)
                link = link_elem["href"] if link_elem else ""
                if link and not link.startswith("http"):
                    link = base_url + link

                # Extract tagline/description
                desc_elem = item.find("p") or item.find(
                    "div", class_=lambda x: x and "tagline" in x.lower() if x else False
                )
                tagline = desc_elem.get_text(strip=True) if desc_elem else ""

                # Extract vote count
                vote_elem = item.find(
                    "span", class_=lambda x: x and "vote" in x.lower() if x else False
                ) or item.find(
                    "div", class_=lambda x: x and "vote" in x.lower() if x else False
                )
                votes = 0
                if vote_elem:
                    vote_text = vote_elem.get_text(strip=True)
                    try:
                        votes = int("".join(filter(str.isdigit, vote_text)))
                    except ValueError:
                        votes = 0

                if name and name != "No Title":
                    product = {
                        "id": f"ph_topic_{topic}_{len(products)}",
                        "name": name,
                        "tagline": tagline,
                        "description": tagline,
                        "url": link,
                        "website": link,
                        "slug": name.lower().replace(" ", "-"),
                        "votes_count": votes,
                        "comments_count": 0,
                        "reviews_count": 0,
                        "reviews_rating": 0.0,
                        "featured_at": datetime.now(timezone.utc).isoformat(),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "thumbnail_url": "",
                        "gallery_images": [],
                        "topics": [topic],
                        "makers": [],
                        "hunters": [],
                        "product_links": (
                            [{"type": "website", "url": link}] if link else []
                        ),
                        "category": topic,
                        "mock_data": False,
                    }
                    products.append(product)
            except Exception as e:
                logger.warning(f"Error parsing product item: {e}")
                continue

        logger.info(f"Scraped {len(products)} products from topic {topic}")
        return products

    except Exception as e:
        logger.error(f"Error scraping topic {topic}: {e}")
        return []


# Mock data generation function removed - now using real scraping


def process_product_hunt_data(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and enrich Product Hunt data with additional metrics and categorization.

    Args:
        products: List of product dictionaries

    Returns:
        List of processed and enriched product data
    """
    current_time = datetime.now(timezone.utc)
    processed_products = []

    for product in products:
        try:
            # Parse created date
            created_at = product.get("created_at") or product.get("featured_at")
            if created_at:
                if isinstance(created_at, str):
                    created_date = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                else:
                    created_date = created_at
                days_since_launch = (
                    current_time.replace(tzinfo=created_date.tzinfo) - created_date
                ).days
            else:
                days_since_launch = 1  # Default fallback

            # Calculate engagement metrics
            votes = product.get("votes_count", 0)
            comments = product.get("comments_count", 0)
            reviews = product.get("reviews_count", 0)
            rating = product.get("reviews_rating", 0)

            # Engagement scoring
            engagement_score = votes * 1 + comments * 2 + reviews * 1.5

            # Launch success scoring (higher for more recent launches with good metrics)
            freshness_factor = (
                max(0, (7 - days_since_launch) / 7) if days_since_launch <= 7 else 0
            )
            launch_success = engagement_score * (1 + freshness_factor)

            # Product potential scoring
            potential_score = (
                votes * 0.4 + comments * 0.3 + reviews * 0.2 + rating * 20 * 0.1
            )

            # Categorize by popularity
            if votes >= 1000:
                popularity = "viral"
            elif votes >= 500:
                popularity = "high"
            elif votes >= 200:
                popularity = "medium"
            else:
                popularity = "low"

            # Launch timing analysis
            if days_since_launch <= 1:
                launch_phase = "launch_day"
            elif days_since_launch <= 7:
                launch_phase = "launch_week"
            elif days_since_launch <= 30:
                launch_phase = "post_launch"
            else:
                launch_phase = "established"

            # Topic analysis for categorization
            topics = product.get("topics", [])
            primary_category = topics[0] if topics else "general"

            # Innovation level estimation
            innovative_keywords = [
                "ai",
                "ml",
                "blockchain",
                "ar",
                "vr",
                "automation",
                "api",
            ]
            innovation_level = "standard"

            product_text = f"{product.get('name', '')} {product.get('tagline', '')} {product.get('description', '')}".lower()
            if any(keyword in product_text for keyword in innovative_keywords):
                innovation_level = "innovative"
            if "revolutionary" in product_text or "breakthrough" in product_text:
                innovation_level = "revolutionary"

            processed_product = {
                **product,
                "fetched_at": current_time.isoformat(),
                "days_since_launch": days_since_launch,
                "engagement_score": round(engagement_score, 2),
                "launch_success_score": round(launch_success, 2),
                "potential_score": round(potential_score, 2),
                "freshness_factor": round(freshness_factor, 2),
                "popularity_category": popularity,
                "launch_phase": launch_phase,
                "primary_category": primary_category,
                "innovation_level": innovation_level,
                "maker_count": len(product.get("makers", [])),
                "hunter_count": len(product.get("hunters", [])),
                "platform": "product_hunt",
                "data_source": "product_hunt_scrape",
            }

            # Soft validation against ProductHuntModel (title/link/published/summary/votes/source)
            try:
                _ = ProductHuntModel(
                    title=processed_product.get("name")
                    or processed_product.get("title", ""),
                    link=processed_product.get("url")
                    or processed_product.get("website", ""),
                    published=processed_product.get("featuredAt")
                    or processed_product.get("createdAt", ""),
                    summary=processed_product.get("tagline")
                    or processed_product.get("description", ""),
                    author=processed_product.get("user", {}).get("name", ""),
                    votes=int(processed_product.get("votesCount", 0)),
                )
            except Exception as e:
                logger.warning(f"Validation failed for Product Hunt item: {e}")

            processed_products.append(processed_product)

        except Exception as e:
            logger.warning(
                f"Error processing product {product.get('id', 'unknown')}: {e}"
            )
            continue

    # Sort by launch success score
    processed_products.sort(
        key=lambda x: x.get("launch_success_score", 0), reverse=True
    )

    logger.info(
        f"Successfully processed {len(processed_products)} Product Hunt products"
    )
    return processed_products


def save_data(data: list[dict[str, Any]], output_dir: str) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed products
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"product_hunt_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"product_hunt_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "product_hunt_latest.json")
    latest_csv = os.path.join(output_dir, "product_hunt_latest.csv")

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten nested data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}

            # Flatten makers and hunters
            makers = flat_item.pop("makers", [])
            hunters = flat_item.pop("hunters", [])
            product_links = flat_item.pop("product_links", [])

            flat_item["makers_info"] = ", ".join(
                [f"{m.get('name', '')} (@{m.get('username', '')})" for m in makers]
            )
            flat_item["hunters_info"] = ", ".join(
                [f"{h.get('name', '')} (@{h.get('username', '')})" for h in hunters]
            )
            flat_item["product_links_info"] = ", ".join(
                [
                    f"{link.get('type', '')}: {link.get('url', '')}"
                    for link in product_links
                ]
            )

            # Convert lists to strings
            if isinstance(flat_item.get("topics"), list):
                flat_item["topics"] = ", ".join(flat_item["topics"])
            if isinstance(flat_item.get("gallery_images"), list):
                flat_item["gallery_images"] = ", ".join(flat_item["gallery_images"])

            csv_data.append(flat_item)

        fieldnames = csv_data[0].keys() if csv_data else []

        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

    logger.info(f"Data saved to {json_file} and {csv_file}")

    return {
        "json_file": json_file,
        "csv_file": csv_file,
        "latest_json": latest_json,
        "latest_csv": latest_csv,
    }


def main():
    """Main function to run the Product Hunt ETL process."""
    logger.info("Starting Product Hunt ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "product_hunt")
        session = create_session()

        # Fetch data
        logger.info("Fetching products from Product Hunt")
        products = fetch_product_hunt_data(session)

        if not products:
            logger.warning("No products fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching data")
        processed_data = process_product_hunt_data(products)

        # Save data
        file_paths = save_data(processed_data, output_dir)

        # Summary
        total_products = len(processed_data)
        viral_products = len(
            [p for p in processed_data if p.get("popularity_category") == "viral"]
        )
        high_potential = len(
            [p for p in processed_data if p.get("potential_score", 0) >= 100]
        )

        logger.info("Product Hunt ETL completed successfully!")
        logger.info(f"Total products: {total_products}")
        logger.info(f"Viral products: {viral_products}")
        logger.info(f"High potential products: {high_potential}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print category distribution
        if processed_data:
            categories = [p.get("primary_category", "unknown") for p in processed_data]
            from collections import Counter

            top_categories = Counter(categories).most_common(10)
            logger.info(f"Top product categories: {top_categories}")

    except Exception as e:
        logger.error(f"Product Hunt ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
