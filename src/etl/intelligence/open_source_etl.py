"""Open Source Intelligence ETL.

Aggregates trending repositories from GitHub using Playwright.
"""

import time
import re
from datetime import datetime, timezone
from typing import Any, List, Dict

from playwright.sync_api import sync_playwright

from src.etl.base import BaseETL
from src.models.github import GitHubRepositoryModel, RepositoryLanguage, TrendingPeriod


class GitHubTrendingScraper:
    """Scraper for GitHub Trending pages."""

    BASE_URL = "https://github.com/trending"

    def __init__(self, logger):
        self.logger = logger
        self.repositories = []
        self.seen_urls = set()

    def scrape(self, languages: List[str] = None, period: str = "daily") -> List[Dict[str, Any]]:
        """Scrape trending repos for specific languages."""
        if not languages:
            languages = [""] # Empty string = "All languages"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            for lang in languages:
                try:
                    self._scrape_language(context, lang, period)
                except Exception as e:
                    self.logger.error(f"Failed to scrape language '{lang}': {e}")
            
            browser.close()
            
        return self.repositories

    def _scrape_language(self, context, language: str, period: str):
        """Scrape a specific language page."""
        url = f"{self.BASE_URL}/{language}?since={period}" if language else f"{self.BASE_URL}?since={period}"
        self.logger.info(f"Navigating to {url}")
        
        page = context.new_page()
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(2) # Allow for any dynamic hydration
        
        repos = page.evaluate("""() => {
            const items = [];
            const rows = document.querySelectorAll('article.Box-row');
            
            rows.forEach(row => {
                const titleLink = row.querySelector('h2 a');
                if (!titleLink) return;
                
                const href = titleLink.getAttribute('href');
                const fullName = titleLink.innerText.replace(/\\s+/g, '').trim(); 
                const descriptionEl = row.querySelector('p');
                const description = descriptionEl ? descriptionEl.innerText.trim() : "";
                
                // Stats
                const starsLink = row.querySelector('a[href$="/stargazers"]');
                const forksLink = row.querySelector('a[href$="/forks"]');
                
                const starsText = starsLink ? starsLink.innerText.trim().replace(/,/g, '') : "0";
                const forksText = forksLink ? forksLink.innerText.trim().replace(/,/g, '') : "0";
                
                const stars = parseInt(starsText) || 0;
                const forks = parseInt(forksText) || 0;
                
                // Language
                const langEl = row.querySelector('[itemprop="programmingLanguage"]');
                const language = langEl ? langEl.innerText.trim() : null;
                
                // Today/Period stars
                const periodStarsEl = row.querySelector('.float-sm-right');
                let periodStars = 0;
                if (periodStarsEl) {
                    const match = periodStarsEl.innerText.match(/(\\d+)\\s+stars/);
                    if (match) periodStars = parseInt(match[1]);
                }
                
                items.push({
                    name: fullName.split('/')[1] || fullName,
                    full_name: fullName,
                    url: "https://github.com" + href,
                    description: description,
                    language: language,
                    stars: stars,
                    forks: forks,
                    period_stars: periodStars
                });
            });
            return items;
        }""")
        
        self.logger.info(f"Examples found for {language or 'All'}: {len(repos)}")
        
        for r in repos:
            if r["url"] not in self.seen_urls:
                r["trending_language"] = language if language else "all"
                r["trending_period"] = period
                self.repositories.append(r)
                self.seen_urls.add(r["url"])
                
        page.close()


class OpenSourceIntelligenceETL(BaseETL[Dict[str, Any], GitHubRepositoryModel]):
    """ETL for Open Source Intelligence (GitHub Trending)."""

    def __init__(self):
        super().__init__(
            name="open_source_intelligence",
            description="Aggregates trending open source repositories",
            enable_enrichment=True,
            title_similarity_threshold=0.9
        )
        self.scraper = None

    def extract(self) -> List[Dict[str, Any]]:
        self.logger.info("Starting GitHub Trending scrape...")
        self.scraper = GitHubTrendingScraper(self.logger)
        
        # Scrape top languages + general
        languages = ["", "python", "javascript", "typescript", "go", "rust", "java", "c++"]
        return self.scraper.scrape(languages=languages, period="daily")

    def transform(self, data: List[Dict[str, Any]]) -> List[GitHubRepositoryModel]:
        transformed = []
        for item in data:
            try:
                # Map scraped data to model
                model = GitHubRepositoryModel(
                    name=item["name"],
                    full_name=item["full_name"],
                    html_url=item["url"],
                    description=item["description"],
                    language=item["language"],
                    stars_count=item["stars"],
                    forks_count=item["forks"],
                    trending_period=TrendingPeriod.DAILY, # Currently hardcoded to daily
                    trending_language=RepositoryLanguage.from_github_language(item["trending_language"] if item["trending_language"] != "all" else None),
                    repository_created_at=datetime.now(timezone.utc), # Placeholder as scrape doesn't give create date
                    repository_updated_at=datetime.now(timezone.utc),
                    source="github_trending"
                )
                transformed.append(model)
            except Exception as e:
                self.logger.warning(f"Failed to transform {item.get('full_name')}: {e}")
                
        return transformed

    def load(self, data: List[GitHubRepositoryModel]) -> None:
        """Save data."""
        # Save enrichment
        import json
        output_file = self.output_dir / f"open_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        latest_file = self.output_dir / "latest.json"
        
        data_dicts = [item.model_dump(mode='json') for item in data]
        
        output_file.write_text(json.dumps(data_dicts, indent=2, ensure_ascii=False), encoding="utf-8")
        latest_file.write_text(json.dumps(data_dicts, indent=2, ensure_ascii=False), encoding="utf-8")
        
        self.logger.info(f"Saved {len(data)} repositories to {latest_file}")

if __name__ == "__main__":
    etl = OpenSourceIntelligenceETL()
    etl.run()
