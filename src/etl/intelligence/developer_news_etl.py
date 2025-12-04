import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from src.etl.intelligence.base_intelligence_etl import BaseIntelligenceETL
from src.models.developer_news import SmartNewsItem, NewsCategory, ExpertComment
from src.utils.logging import get_logger

logger = get_logger("DeveloperNewsETL")

class DeveloperNewsIntelligenceETL(BaseIntelligenceETL):
    """ETL for aggregating and enhancing developer news."""
    
    def __init__(self):
        super().__init__(name="developer_news")
        self.output_dir = Path("data/developer_news/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Mapping of source keywords to categories
        self.category_keywords = {
            NewsCategory.AI_ML: ["ai", "machine learning", "llm", "gpt", "neural", "deep learning", "openai", "anthropic"],
            NewsCategory.WEB_DEV: ["react", "vue", "angular", "css", "html", "javascript", "typescript", "frontend", "backend", "web"],
            NewsCategory.DEVOPS: ["docker", "kubernetes", "aws", "azure", "cloud", "ci/cd", "terraform", "linux"],
            NewsCategory.MOBILE: ["ios", "android", "swift", "kotlin", "flutter", "react native", "mobile"],
            NewsCategory.SECURITY: ["security", "vulnerability", "hack", "exploit", "cve", "malware", "ransomware"],
            NewsCategory.CAREER: ["career", "salary", "interview", "hiring", "remote", "job", "productivity", "burnout"],
            NewsCategory.STARTUPS: ["startup", "funding", "vc", "ipo", "acquisition", "revenue", "growth"],
        }

    def extract(self) -> List[Dict]:
        """Aggregate data from existing news ETL outputs."""
        aggregated_items = []
        
        # List of source files to aggregate from
        # Using relative paths from project root
        source_files = [
            "data/hackernews/hackernews.json",
            "data/news/techcrunch_latest.json",
            "data/news/venturebeat_latest.json",
            "data/news/google_ai_blog_latest.json",
            "data/news/freecodecamp_latest.json",
            "data/news/lobsters_latest.json"
        ]
        
        project_root = Path.cwd()
        
        for file_path in source_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Handle different structures (list vs dict with 'articles' key)
                        items = []
                        if isinstance(data, list):
                            items = data
                        elif isinstance(data, dict):
                            items = data.get('articles', []) or data.get('items', [])
                            
                        # Add source metadata if missing
                        source_name = file_path.split('/')[-1].split('_')[0].replace('.json', '')
                        for item in items:
                            if 'source' not in item:
                                item['source'] = source_name
                        
                        aggregated_items.extend(items)
                        logger.info(f"Loaded {len(items)} items from {file_path}")
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
            else:
                logger.warning(f"Source file not found: {file_path}")
                
        return aggregated_items

    def transform(self, data: List[Dict]) -> List[SmartNewsItem]:
        """Transform raw items into SmartNewsItems with intelligence."""
        smart_items = []
        seen_urls = set()
        
        for item in data:
            try:
                # Basic fields
                url = item.get('url') or item.get('link')
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                title = item.get('title') or "No Title"
                
                # Parse date
                published_at = self._parse_date(item.get('published_at') or item.get('published') or item.get('created_at'))
                
                # Intelligence processing
                category = self._categorize_item(title, item.get('description', ''))
                summary = self._generate_summary(title, item.get('description', ''))
                key_points = self._extract_key_points(item.get('description', ''))
                trend_score = self._calculate_trend_score(item)
                expert_comment = self._extract_expert_comment(item)
                
                smart_item = SmartNewsItem(
                    id=item.get('id') or str(hash(url)),
                    title=title,
                    url=url,
                    source=item.get('source', 'unknown'),
                    published_at=published_at,
                    category=category,
                    summary=summary,
                    key_points=key_points,
                    trend_score=trend_score,
                    expert_commentary=expert_comment,
                    original_data=item
                )
                smart_items.append(smart_item)
                
            except Exception as e:
                logger.warning(f"Error transforming item {item.get('title', 'unknown')}: {e}")
                continue
                
        # Sort by trend score and date
        smart_items.sort(key=lambda x: (x.trend_score, x.published_at), reverse=True)
        return smart_items

    def load(self, data: List[SmartNewsItem]):
        """Save transformed data to JSON."""
        output_file = self.output_dir / "smart_news.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([item.model_dump(mode='json') for item in data], f, indent=2)
        logger.info(f"Saved {len(data)} smart news items to {output_file}")

    def _categorize_item(self, title: str, description: str) -> NewsCategory:
        """Heuristic categorization based on keywords."""
        text = (title + " " + str(description)).lower()
        
        for category, keywords in self.category_keywords.items():
            if any(k in text for k in keywords):
                return category
        
        return NewsCategory.GENERAL

    def _generate_summary(self, title: str, description: str) -> str:
        """Generate a heuristic summary."""
        # In a real system, this would use an LLM.
        # Here we clean up the description or use the title.
        if not description:
            return f"News update: {title}"
            
        # Simple cleanup: remove HTML tags if any (basic regex), truncate
        clean_desc = re.sub(r'<[^>]+>', '', str(description))
        sentences = clean_desc.split('.')
        if len(sentences) > 2:
            return '. '.join(sentences[:2]) + '.'
        return clean_desc[:200] + "..." if len(clean_desc) > 200 else clean_desc

    def _extract_key_points(self, description: str) -> List[str]:
        """Extract key points from description."""
        if not description:
            return []
            
        clean_desc = re.sub(r'<[^>]+>', '', str(description))
        sentences = [s.strip() for s in clean_desc.split('.') if s.strip()]
        
        # Heuristic: longer sentences often contain more info
        sorted_sentences = sorted(sentences, key=len, reverse=True)
        return sorted_sentences[:3]

    def _calculate_trend_score(self, item: Dict) -> float:
        """Calculate trend score based on available metrics."""
        score = 0.5 # Base score
        
        # Boost for engagement metrics if available (e.g. HackerNews points)
        points = item.get('points') or item.get('score')
        comments = item.get('comments_count') or item.get('num_comments')
        
        if points:
            try:
                p = int(points)
                if p > 500: score += 0.4
                elif p > 100: score += 0.2
            except: pass
            
        if comments:
            try:
                c = int(comments)
                if c > 100: score += 0.1
            except: pass
            
        return min(1.0, score)

    def _extract_expert_comment(self, item: Dict) -> Optional[ExpertComment]:
        """Simulate extracting expert commentary."""
        # For HackerNews, we might have top comment in original data (if we scraped it)
        # For now, we'll simulate it for high-scoring items
        points = item.get('points') or item.get('score')
        if points and int(points) > 200:
            return ExpertComment(
                author="Community Expert",
                content="This is a highly discussed topic in the developer community, indicating significant interest.",
                source="Community Discussion",
                sentiment="Positive"
            )
        return None

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string to datetime."""
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            # Try ISO format first
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        except:
            # Fallback to current time if parsing fails (simplified for this ETL)
            return datetime.now(timezone.utc)

if __name__ == "__main__":
    etl = DeveloperNewsIntelligenceETL()
    etl.run()
