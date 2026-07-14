"""Meta Search Engine
Aggregates search results from multiple intelligence domains (Videos, News, Papers).
"""

import logging

from src.web.dashboard.components.arxiv_research_tab import ALL_ARXIV_DATA, load_arxiv_data
from src.web.dashboard.components.news_tab import format_article_date, get_all_news_data
from src.web.dashboard.components.videos_tab import video_manager
from src.web.dashboard.search_utils import filter_content

logger = logging.getLogger(__name__)


class MetaSearchEngine:
    """Unified search engine across all Watchtower domains."""

    def __init__(self):
        pass

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Search across all domains and return ranked results.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of standardized result dicts:
            {
                "id": str,
                "type": "video" | "news" | "paper",
                "title": str,
                "summary": str,
                "source": str,
                "date": datetime,
                "date_display": str,
                "url": str,
                "image": str (optional),
                "score": float (relevance score)
            }
        """
        if not query:
            return []

        results = []

        # 1. Search Videos
        try:
            # video_manager.get_videos handles its own loading check
            videos = video_manager.get_videos(search_term=query, limit=limit)
            for v in videos:
                results.append(
                    {
                        "id": f"vid_{v.get('url')}",
                        "type": "video",
                        "title": v.get("title"),
                        "summary": v.get("description", "")[:200] + "...",
                        "source": f"YouTube ({v.get('channel')})",
                        "date": v.get("published_date"),
                        "date_display": str(v.get("published_at", "")[:10]),
                        "url": v.get("url"),
                        "image": v.get("thumbnail"),
                        "score": 1.0,  # Placeholder for now
                    }
                )
        except Exception as e:
            logger.error(f"MetaSearch video error: {e}")

        # 2. Search News
        try:
            all_news = get_all_news_data()
            # Flatten news dict to list
            news_items = []
            for source, items in all_news.items():
                for item in items:
                    item["_source_key"] = source  # Temp marker
                    news_items.append(item)

            # Use shared filter_content utility
            filtered_news = filter_content(query, news_items)

            for item in filtered_news[:limit]:
                # Parse date using news_tab utility if available, or generic
                date_display = format_article_date(item)

                results.append(
                    {
                        "id": f"news_{item.get('url') or item.get('link')}",
                        "type": "news",
                        "title": item.get("title"),
                        "summary": item.get("summary", "")[:200] + "...",
                        "source": item.get("source_display_name", "News"),
                        "date": None,  # Complex to parse uniformly here, sorting relies on display for now? No, need comparable date.
                        "date_display": date_display,
                        "url": item.get("url") or item.get("link"),
                        "image": None,
                        "score": 1.0,
                    }
                )
        except Exception as e:
            logger.error(f"MetaSearch news error: {e}")

        # 3. Search Papers
        try:
            # Ensure data loaded
            if ALL_ARXIV_DATA.empty:
                load_arxiv_data()

            # Need to access Global if load_arxiv_data doesn't return it
            # Re-import to get latest state if module-level variable changes?
            # In Python, from module import VAR imports the value at time of import if immutable, but DataFrame is mutable object ref?
            # Actually ALL_ARXIV_DATA is reassigned in load_arxiv_data (ALL_ARXIV_DATA = df).
            # This means 'from ... import ALL_ARXIV_DATA' will hold the OLD None/Empty DF.
            # I must import the MODULE and access module.ALL_ARXIV_DATA.

            from src.web.dashboard.components import arxiv_research_tab

            if arxiv_research_tab.ALL_ARXIV_DATA.empty:
                arxiv_research_tab.load_arxiv_data()

            df = arxiv_research_tab.ALL_ARXIV_DATA

            if not df.empty:
                # Simple string match
                search_lower = query.lower()
                mask = df["display_title"].str.lower().str.contains(search_lower, na=False) | df["display_summary"].str.lower().str.contains(search_lower, na=False)

                filtered_papers = df[mask].head(limit)

                for _, p in filtered_papers.iterrows():
                    results.append(
                        {
                            "id": f"paper_{p.get('link')}",
                            "type": "paper",
                            "title": p.get("display_title"),
                            "summary": p.get("display_summary", "")[:200] + "...",
                            "source": f"ArXiv ({p.get('primary_category_display')})",
                            "date": p.get("published_date"),
                            "date_display": p.get("published_display"),
                            "url": p.get("link"),
                            "image": None,
                            "score": 1.0,
                        }
                    )

        except Exception as e:
            logger.error(f"MetaSearch paper error: {e}")

        # Sort combined results by date (descending), handling Nones
        # We need a unified date field.
        # For News, we skipped parsing. Let's try to be resilient.

        results.sort(key=lambda x: str(x.get("date_display") or ""), reverse=True)

        return results


# Singleton instance
meta_search_engine = MetaSearchEngine()
