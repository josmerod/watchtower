"""Example implementation of an enhanced watcher for demonstration."""

import re
from typing import Any

from bs4 import BeautifulSoup

from src.watchers.enhanced_watcher import EnhancedWatcher, WatcherConfig


class HackerNewsWatcher(EnhancedWatcher):
    """Example watcher that monitors Hacker News front page for story count."""
    
    async def extract_value(self, html_content: str) -> Any:
        """Extract the number of stories on the front page.
        
        Args:
            html_content: HTML content of Hacker News front page.
            
        Returns:
            Number of stories found.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Count story items (they have class 'titleline' in modern HN)
            stories = soup.find_all('span', class_='titleline')
            story_count = len(stories)
            
            self.logger.debug(f"Found {story_count} stories on Hacker News front page")
            return story_count
            
        except Exception as e:
            self.logger.error(f"Error parsing Hacker News HTML: {e}")
            raise
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Check if story count has changed significantly.
        
        Args:
            old_value: Previous story count.
            new_value: Current story count.
            
        Returns:
            True if change is significant (more than 5 stories difference).
        """
        try:
            old_count = int(old_value) if old_value is not None else 0
            new_count = int(new_value) if new_value is not None else 0
            
            # Alert if difference is more than 5 stories
            difference = abs(new_count - old_count)
            return difference > 5
            
        except (ValueError, TypeError):
            # If we can't convert to int, consider it a change
            return True


class RedditWatcher(EnhancedWatcher):
    """Example watcher that monitors Reddit subreddit for post titles."""
    
    async def extract_value(self, html_content: str) -> Any:
        """Extract the title of the top post.
        
        Args:
            html_content: HTML content of Reddit page.
            
        Returns:
            Title of the top post.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for post titles (Reddit's structure varies, this is a simple approach)
            title_element = soup.find('h3', class_=re.compile('.*title.*', re.I))
            
            if title_element:
                title = title_element.get_text(strip=True)
                self.logger.debug(f"Found top post title: {title[:50]}...")
                return title
            else:
                # Fallback: look for any h3 tag
                h3_tags = soup.find_all('h3')
                if h3_tags:
                    title = h3_tags[0].get_text(strip=True)
                    self.logger.debug(f"Found title via fallback: {title[:50]}...")
                    return title
                
            self.logger.warning("No post title found")
            return "No title found"
            
        except Exception as e:
            self.logger.error(f"Error parsing Reddit HTML: {e}")
            raise
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Check if the top post title has changed.
        
        Args:
            old_value: Previous title.
            new_value: Current title.
            
        Returns:
            True if titles are different.
        """
        old_title = str(old_value) if old_value is not None else ""
        new_title = str(new_value) if new_value is not None else ""
        
        return old_title != new_title


def create_example_watchers():
    """Create example watcher configurations for testing.
    
    Returns:
        List of configured watcher instances.
    """
    # HackerNews watcher configuration
    hn_config = WatcherConfig(
        name="hackernews_front_page",
        url="https://news.ycombinator.com",
        check_interval=1800,  # 30 minutes
        max_retries=3,
        retry_delay=10,
        timeout=30,
        enabled=True,
        alert_threshold=3  # Alert after 3 consecutive failures
    )
    
    # Reddit Python watcher configuration
    reddit_config = WatcherConfig(
        name="reddit_python",
        url="https://www.reddit.com/r/Python/",
        check_interval=3600,  # 1 hour
        max_retries=3,
        retry_delay=5,
        timeout=45,
        enabled=True,
        alert_threshold=5
    )
    
    # Create watcher instances
    watchers = [
        HackerNewsWatcher(hn_config),
        RedditWatcher(reddit_config),
    ]
    
    return watchers


async def run_example_watchers():
    """Run example watchers for demonstration."""
    import asyncio
    
    watchers = create_example_watchers()
    
    print("Starting example watchers...")
    print(f"Created {len(watchers)} watchers:")
    
    for watcher in watchers:
        status = watcher.get_status()
        print(f"  - {status['name']}: {status['url']}")
    
    # Run each watcher once
    print("\nRunning single checks...")
    for watcher in watchers:
        print(f"\nTesting {watcher.config.name}...")
        try:
            success = await watcher.run_once()
            status = watcher.get_status()
            print(f"  Success: {success}")
            print(f"  Last value: {status['last_value']}")
            print(f"  Check count: {status['check_count']}")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example_watchers()) 