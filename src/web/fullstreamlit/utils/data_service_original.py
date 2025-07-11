"""
Centralized data service for the Watchtower Streamlit application.
Handles all data loading with performance optimizations and caching.
"""

import streamlit as st
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class DataService:
    """Centralized data service for loading and caching application data"""
    
    def __init__(self, logger=None):
        """Initialize the DataService.

        Args:
            logger: Optional logger instance. If None, logging will be handled
                    by the _log method's default behavior or be silent.
        """
        self.logger = logger
        # Fix path resolution to work from any location
        current_dir = Path(__file__).parent
        # Navigate to project root, then to data directory
        self.data_dir = current_dir.parent.parent.parent.parent / "data"
        self._log(f"Data directory resolved to: {self.data_dir}")
        
    def _log(self, message: str, level: str = "info"):
        """Helper method for logging"""
        if self.logger:
            getattr(self.logger, level)(message)
    
    def _safe_load_json(self, file_path: Path, description: str = "data") -> List[Dict]:
        """Safely load JSON file with error handling"""
        try:
            if file_path.exists():
                self._log(f"Loading {description} from {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._log(f"Successfully loaded {len(data) if isinstance(data, list) else 'unknown'} items from {file_path}")
                return data if isinstance(data, list) else []
            else:
                self._log(f"File not found: {file_path}", "warning")
                return []
        except Exception as e:
            self._log(f"Error loading {description} from {file_path}: {str(e)}", "error")
            return []
    
    @st.cache_data(ttl=3600)
    def get_games_data(_self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load all games data (deals, bundles, giveaways)"""
        _self._log("Loading games data")
        
        games_dir = _self.data_dir / "games"
        deals_df = pd.DataFrame()
        bundles_df = pd.DataFrame()
        giveaways_df = pd.DataFrame()
        
        try:
            # Load deals
            deals_file = games_dir / "deals.json"
            deals = _self._safe_load_json(deals_file, "game deals")
            if deals:
                deals_df = pd.DataFrame(deals)
                if "published_date" in deals_df.columns:
                    deals_df["published_date"] = pd.to_datetime(deals_df["published_date"], errors="coerce").dt.date
                if "price" in deals_df.columns:
                    deals_df["price"] = pd.to_numeric(
                        deals_df["price"].replace({None: np.nan, "": np.nan}), errors="coerce"
                    )
                _self._log(f"Loaded {len(deals_df)} game deals")
            
            # Load bundles (combining regular and humble bundles)
            bundles_data = []
            
            # Regular bundles
            bundles_file = games_dir / "bundles.json"
            regular_bundles = _self._safe_load_json(bundles_file, "regular bundles")
            if regular_bundles:
                for bundle in regular_bundles:
                    bundle["store"] = bundle.get("store", "Unknown")
                bundles_data.extend(regular_bundles)
            
            # Humble bundles
            humble_file = games_dir / "humblebundles.json"
            humble_bundles = _self._safe_load_json(humble_file, "humble bundles")
            if humble_bundles:
                for bundle in humble_bundles:
                    bundle["store"] = "Humble Bundle"
                    if "end_date" in bundle:
                        bundle["published_date"] = bundle.pop("end_date")
                    if "games" in bundle:
                        bundle["game_count"] = len(bundle["games"])
                bundles_data.extend(humble_bundles)
            
            if bundles_data:
                bundles_df = pd.DataFrame(bundles_data)
                if "published_date" in bundles_df.columns:
                    bundles_df["published_date"] = pd.to_datetime(bundles_df["published_date"], errors="coerce").dt.date
                _self._log(f"Loaded {len(bundles_df)} game bundles")
            
            # Load giveaways
            giveaways_file = games_dir / "giveaways.json"
            giveaways = _self._safe_load_json(giveaways_file, "game giveaways")
            if giveaways:
                giveaways_df = pd.DataFrame(giveaways)
                if "published_date" in giveaways_df.columns:
                    giveaways_df["published_date"] = pd.to_datetime(giveaways_df["published_date"], errors="coerce").dt.date
                if "expires_date" in giveaways_df.columns:
                    giveaways_df["expires_date"] = pd.to_datetime(giveaways_df["expires_date"], errors="coerce").dt.date
                _self._log(f"Loaded {len(giveaways_df)} game giveaways")
                    
        except Exception as e:
            _self._log(f"Error loading games data: {str(e)}", "error")
        
        return deals_df, bundles_df, giveaways_df
    
    @st.cache_data(ttl=3600)
    def get_courses_data(_self) -> Dict[str, pd.DataFrame]:
        """Load courses data from all platforms"""
        _self._log("Loading courses data")
        
        courses_data = {}
        
        try:
            # Coursera courses
            coursera_file = _self.data_dir / "classcentral" / "coursera_courses.json"
            coursera_data = _self._safe_load_json(coursera_file, "Coursera courses")
            if coursera_data:
                courses_data["coursera"] = pd.DataFrame(coursera_data)
                _self._log(f"Loaded {len(courses_data['coursera'])} Coursera courses")
            
            # Check for other course platforms
            udemy_file = _self.data_dir / "udemy" / "udemy_courses.json"
            if udemy_file.exists():
                udemy_data = _self._safe_load_json(udemy_file, "Udemy courses")
                if udemy_data:
                    courses_data["udemy"] = pd.DataFrame(udemy_data)
                    _self._log(f"Loaded {len(courses_data['udemy'])} Udemy courses")
            
        except Exception as e:
            _self._log(f"Error loading courses data: {str(e)}", "error")
        
        return courses_data
    
    @st.cache_data(ttl=1800)  # Shorter TTL for news data
    def get_news_data(_self) -> Dict[str, pd.DataFrame]:
        """Load news data from all sources"""
        _self._log("Loading news data")
        
        news_data = {}
        
        try:
            # HackerNews - check multiple possible file names
            hn_dir = _self.data_dir / "hackernews"
            hn_files = ["stories.json", "hackernews.json", "hackernews_simple.json"]
            
            for filename in hn_files:
                hn_file = hn_dir / filename
                if hn_file.exists():
                    hn_data = _self._safe_load_json(hn_file, f"HackerNews stories from {filename}")
                    if hn_data:
                        news_data["hackernews"] = pd.DataFrame(hn_data)
                        if "published_date" in news_data["hackernews"].columns:
                            news_data["hackernews"]["published_date"] = pd.to_datetime(
                                news_data["hackernews"]["published_date"], errors="coerce"
                            ).dt.date
                        _self._log(f"Loaded {len(news_data['hackernews'])} HackerNews stories")
                    break
            
            # FutureTools - check multiple possible file names
            ft_dir = _self.data_dir / "futuretools"
            ft_files = ["news.json", "futuretoolsnews.json"]
            
            for filename in ft_files:
                ft_file = ft_dir / filename
                if ft_file.exists():
                    ft_data = _self._safe_load_json(ft_file, f"FutureTools news from {filename}")
                    if ft_data:
                        news_data["futuretools"] = pd.DataFrame(ft_data)
                        _self._log(f"Loaded {len(news_data['futuretools'])} FutureTools articles")
                    break
            
            # Medium GenAI
            medium_file = _self.data_dir / "medium_genai" / "articles.json"
            medium_data = _self._safe_load_json(medium_file, "Medium GenAI articles")
            if medium_data:
                news_data["medium"] = pd.DataFrame(medium_data)
                _self._log(f"Loaded {len(news_data['medium'])} Medium articles")
            
            # General news directory
            news_dir = _self.data_dir / "news"
            if news_dir.exists():
                for news_file in news_dir.glob("*.json"):
                    news_source_data = _self._safe_load_json(news_file, f"news from {news_file.name}")
                    if news_source_data:
                        source_name = news_file.stem
                        news_data[source_name] = pd.DataFrame(news_source_data)
                        _self._log(f"Loaded {len(news_data[source_name])} articles from {source_name}")
                        
        except Exception as e:
            _self._log(f"Error loading news data: {str(e)}", "error")
        
        return news_data
    
    @st.cache_data(ttl=1800)  # Shorter TTL for video data
    def get_videos_data(_self) -> Dict[str, pd.DataFrame]:
        """Load YouTube videos data"""
        _self._log("Loading videos data")
        
        videos_data = {}
        youtube_dir = _self.data_dir / "youtube"
        
        try:
            if youtube_dir.exists():
                for channel_dir in youtube_dir.iterdir():
                    if channel_dir.is_dir():
                        # Check multiple possible video file names
                        video_files = ["videos.json", "youtube_videos.json"]
                        
                        for filename in video_files:
                            videos_file = channel_dir / filename
                            if videos_file.exists():
                                channel_data = _self._safe_load_json(videos_file, f"videos from {channel_dir.name}")
                                if channel_data:
                                    df = pd.DataFrame(channel_data)
                                    
                                    # Optimize data processing
                                    if not df.empty:
                                        # Normalize date columns
                                        if "published_at" in df.columns:
                                            df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce")
                                        elif "published_date" in df.columns:
                                            df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
                                        
                                        # Ensure required columns exist
                                        if "channel" in df.columns and "channel_name" not in df.columns:
                                            df["channel_name"] = df["channel"]
                                        if "thumbnail_url" in df.columns and "thumbnail" not in df.columns:
                                            df["thumbnail"] = df["thumbnail_url"]
                                        
                                        # Pre-sort by date for better performance
                                        if "published_date" in df.columns:
                                            df = df.sort_values("published_date", ascending=False)
                                        
                                        videos_data[channel_dir.name] = df
                                        _self._log(f"Loaded {len(df)} videos from {channel_dir.name}")
                                break
                                
        except Exception as e:
            _self._log(f"Error loading videos data: {str(e)}", "error")
        
        return videos_data
    
    @st.cache_data(ttl=3600)
    def get_video_categories(_self) -> Dict[str, str]:
        """Get video categories with display names"""
        _self._log("Loading video categories")
        
        categories = {}
        youtube_dir = _self.data_dir / "youtube"
        
        try:
            if youtube_dir.exists():
                for channel_dir in youtube_dir.iterdir():
                    if channel_dir.is_dir():
                        # Format display name
                        display_name = channel_dir.name.replace('_', ' ').replace('-', ' ').title()
                        # Remove common prefixes for cleaner names
                        for prefix in ['aa-', 'z-', 'zz-', 'zzz-']:
                            if display_name.lower().startswith(prefix):
                                display_name = display_name[len(prefix):].strip()
                                break
                        
                        categories[channel_dir.name] = display_name
                        
        except Exception as e:
            _self._log(f"Error loading video categories: {str(e)}", "error")
        
        return categories
    
    @st.cache_data(ttl=3600)
    def get_arxiv_data(_self) -> pd.DataFrame:
        """Load ArXiv papers data"""
        _self._log("Loading ArXiv data")
        
        try:
            # Try CSV first
            arxiv_file = _self.data_dir / "arxiv" / "processed" / "csv" / "papers.csv"
            if arxiv_file.exists():
                arxiv_df = pd.read_csv(arxiv_file)
                _self._log(f"Loaded {len(arxiv_df)} ArXiv papers from CSV")
                return arxiv_df
            
            # Try JSON format
            arxiv_json = _self.data_dir / "arxiv" / "processed" / "json" / "papers.json"
            arxiv_data = _self._safe_load_json(arxiv_json, "ArXiv papers")
            if arxiv_data:
                arxiv_df = pd.DataFrame(arxiv_data)
                _self._log(f"Loaded {len(arxiv_df)} ArXiv papers from JSON")
                return arxiv_df
            
            # Try other possible locations
            arxiv_alt_locations = [
                _self.data_dir / "arxiv" / "papers.json",
                _self.data_dir / "arxiv" / "papers.csv"
            ]
            
            for alt_file in arxiv_alt_locations:
                if alt_file.exists():
                    if alt_file.suffix == '.csv':
                        arxiv_df = pd.read_csv(alt_file)
                        _self._log(f"Loaded {len(arxiv_df)} ArXiv papers from {alt_file}")
                        return arxiv_df
                    else:
                        arxiv_data = _self._safe_load_json(alt_file, f"ArXiv papers from {alt_file}")
                        if arxiv_data:
                            arxiv_df = pd.DataFrame(arxiv_data)
                            _self._log(f"Loaded {len(arxiv_df)} ArXiv papers from {alt_file}")
                            return arxiv_df
                        
        except Exception as e:
            _self._log(f"Error loading ArXiv data: {str(e)}", "error")
        
        return pd.DataFrame()
    
    @st.cache_data(ttl=3600)
    def get_events_data(_self) -> pd.DataFrame:
        """Load Valencia events data"""
        _self._log("Loading events data")
        
        try:
            events_file = _self.data_dir / "valencia_events" / "events.json"
            events_data = _self._safe_load_json(events_file, "Valencia events")
            if events_data:
                events_df = pd.DataFrame(events_data)
                _self._log(f"Loaded {len(events_df)} Valencia events")
                return events_df
                    
        except Exception as e:
            _self._log(f"Error loading events data: {str(e)}", "error")
        
        return pd.DataFrame()
    
    def get_data_summary(self) -> Dict[str, Dict]:
        """Get a summary of all data for the dashboard"""
        self._log("Generating data summary")
        
        summary = {}
        
        try:
            # Games summary
            deals_df, bundles_df, giveaways_df = self.get_games_data()
            summary["games"] = {
                "deals": len(deals_df),
                "bundles": len(bundles_df),
                "giveaways": len(giveaways_df),
                "latest_deal": deals_df.iloc[0]["title"] if not deals_df.empty and "title" in deals_df.columns else None,
                "latest_bundle": bundles_df.iloc[0]["title"] if not bundles_df.empty and "title" in bundles_df.columns else None
            }
            
            # Courses summary
            courses_data = self.get_courses_data()
            total_courses = sum(len(df) for df in courses_data.values())
            summary["courses"] = {
                "total": total_courses,
                "platforms": list(courses_data.keys()),
                "by_platform": {k: len(v) for k, v in courses_data.items()}
            }
            
            # News summary
            news_data = self.get_news_data()
            total_news = sum(len(df) for df in news_data.values())
            summary["news"] = {
                "total": total_news,
                "sources": list(news_data.keys()),
                "by_source": {k: len(v) for k, v in news_data.items()}
            }
            
            # Videos summary
            videos_data = self.get_videos_data()
            total_videos = sum(len(df) for df in videos_data.values())
            summary["videos"] = {
                "total": total_videos,
                "channels": len(videos_data),
                "by_channel": {k: len(v) for k, v in videos_data.items()}
            }
            
            # ArXiv summary
            arxiv_df = self.get_arxiv_data()
            recent_count = 0
            if not arxiv_df.empty and "published_date" in arxiv_df.columns:
                try:
                    recent_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                    recent_count = len(arxiv_df[arxiv_df["published_date"] >= recent_date])
                except:
                    recent_count = 0
            
            summary["arxiv"] = {
                "total": len(arxiv_df),
                "recent": recent_count
            }
            
            # Events summary
            events_df = self.get_events_data()
            upcoming_count = 0
            if not events_df.empty and "date" in events_df.columns:
                try:
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    upcoming_count = len(events_df[events_df["date"] >= current_date])
                except:
                    upcoming_count = 0
            
            summary["events"] = {
                "total": len(events_df),
                "upcoming": upcoming_count
            }
            
            self._log(f"Generated summary: {summary}")
            return summary
            
        except Exception as e:
            self._log(f"Error generating data summary: {str(e)}", "error")
            # Return a safe default summary
            return {
                "games": {"deals": 0, "bundles": 0, "giveaways": 0, "latest_deal": None, "latest_bundle": None},
                "courses": {"total": 0, "platforms": [], "by_platform": {}},
                "news": {"total": 0, "sources": [], "by_source": {}},
                "videos": {"total": 0, "channels": 0, "by_channel": {}},
                "arxiv": {"total": 0, "recent": 0},
                "events": {"total": 0, "upcoming": 0}
            } 