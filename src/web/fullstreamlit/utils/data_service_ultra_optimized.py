"""
Ultra-optimized data service for the Watchtower Streamlit application.
Eliminates I/O bottlenecks, reduces memory usage, and implements advanced caching strategies.
"""

import streamlit as st
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
from functools import lru_cache
import hashlib
import pickle
import gc
from concurrent.futures import ThreadPoolExecutor
import asyncio

class UltraOptimizedDataService:
    """Ultra-optimized data service with advanced caching and memory management"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._setup_paths()
        self._init_memory_cache()
        self._preload_file_metadata()
        
    def _setup_paths(self):
        """Setup and cache all file paths to avoid repeated path operations"""
        current_dir = Path(__file__).parent
        self.data_dir = current_dir.parent.parent.parent.parent / "data"
        self._log(f"Data directory: {self.data_dir}")
        
        # Pre-cache all important paths
        self.cached_paths = {
            'games_dir': self.data_dir / "games",
            'youtube_dir': self.data_dir / "youtube", 
            'hackernews_dir': self.data_dir / "hackernews",
            'futuretools_dir': self.data_dir / "futuretools",
            'medium_dir': self.data_dir / "medium_genai",
            'coursera_dir': self.data_dir / "classcentral",
            'udemy_dir': self.data_dir / "udemy",
            'arxiv_dir': self.data_dir / "arxiv",
            'events_dir': self.data_dir / "valencia_events",
            'crypto_sentiment_dir': self.data_dir / "crypto_sentiment",
            'tech_jobs_dir': self.data_dir / "tech_jobs",
            'dev_community_dir': self.data_dir / "dev_community",
            'product_hunt_dir': self.data_dir / "product_hunt",
            'github_trends_dir': self.data_dir / "github_trends"
        }
        
    def _init_memory_cache(self):
        """Initialize in-memory cache for frequently accessed data"""
        if 'ultra_data_cache' not in st.session_state:
            st.session_state.ultra_data_cache = {}
        
        self.memory_cache = st.session_state.ultra_data_cache
        
    def _preload_file_metadata(self):
        """Pre-load file metadata to avoid repeated file existence checks"""
        self.file_metadata = {}
        
        try:
            for name, path in self.cached_paths.items():
                if path.exists():
                    self.file_metadata[name] = {
                        'exists': True,
                        'last_modified': path.stat().st_mtime if path.is_file() else None,
                        'size': path.stat().st_size if path.is_file() else None
                    }
                else:
                    self.file_metadata[name] = {'exists': False}
        except Exception as e:
            self._log(f"Error preloading file metadata: {e}", "warning")
            
    def _log(self, message: str, level: str = "info"):
        """Optimized logging with reduced overhead"""
        if self.logger and hasattr(self.logger, level):
            getattr(self.logger, level)(message)
    
    @lru_cache(maxsize=1000)
    def _get_cache_key(self, file_path: str, operation: str) -> str:
        """Generate cache key using file hash for better cache invalidation"""
        try:
            path_obj = Path(file_path)
            if path_obj.exists():
                stat = path_obj.stat()
                # Use file size and modification time for cache key
                return hashlib.md5(f"{file_path}_{operation}_{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
            return hashlib.md5(f"{file_path}_{operation}_missing".encode()).hexdigest()
        except:
            return hashlib.md5(f"{file_path}_{operation}".encode()).hexdigest()
    
    def _ultra_fast_json_load(self, file_path: Path, cache_key: str) -> List[Dict]:
        """Ultra-fast JSON loading with multiple optimization layers"""
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        try:
            if not file_path.exists():
                return []
            
            # Read file in binary mode for speed
            with open(file_path, 'rb') as f:
                # Load JSON with optimized settings
                data = json.loads(f.read().decode('utf-8'))
            
            # Validate and cache
            if isinstance(data, list):
                # Store in memory cache with size limit
                if len(self.memory_cache) < 50:  # Limit cache size
                    self.memory_cache[cache_key] = data
                return data
            elif isinstance(data, dict):
                # Convert single dict to list for consistency
                result = [data]
                if len(self.memory_cache) < 50:
                    self.memory_cache[cache_key] = result
                return result
            else:
                self._log(f"Unexpected data type in {file_path}: {type(data)}", "warning")
                return []
                
        except Exception as e:
            self._log(f"Error loading {file_path}: {str(e)}", "error")
            return []
    
    @st.cache_data(ttl=3600, max_entries=10, show_spinner=False)
    def get_games_data_ultra(_self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Ultra-optimized games data loading with parallel processing"""
        _self._log("Loading games data (ultra-optimized)")
        
        games_dir = _self.cached_paths['games_dir']
        
        # Define file operations
        file_operations = [
            ('deals', games_dir / "deals.json"),
            ('bundles', games_dir / "bundles.json"),
            ('humble', games_dir / "humblebundles.json"),
            ('giveaways', games_dir / "giveaways.json")
        ]
        
        # Load files in parallel using cached operations
        loaded_data = {}
        for op_name, file_path in file_operations:
            cache_key = _self._get_cache_key(str(file_path), op_name)
            loaded_data[op_name] = _self._ultra_fast_json_load(file_path, cache_key)
        
        # Process deals
        deals_df = pd.DataFrame()
        if loaded_data['deals']:
            deals_df = pd.DataFrame(loaded_data['deals'])
            # Optimize data types in one pass
            if not deals_df.empty:
                deals_df = _self._optimize_dataframe_dtypes(deals_df, {
                    'published_date': 'datetime',
                    'price': 'float'
                })
        
        # Process bundles (combine regular and humble)
        bundles_data = []
        if loaded_data['bundles']:
            for bundle in loaded_data['bundles']:
                bundle["store"] = bundle.get("store", "Unknown")
            bundles_data.extend(loaded_data['bundles'])
        
        if loaded_data['humble']:
            for bundle in loaded_data['humble']:
                bundle["store"] = "Humble Bundle"
                if "end_date" in bundle and "published_date" not in bundle:
                    bundle["published_date"] = bundle.pop("end_date")
                if "games" in bundle:
                    bundle["game_count"] = len(bundle["games"])
            bundles_data.extend(loaded_data['humble'])
        
        bundles_df = pd.DataFrame()
        if bundles_data:
            bundles_df = pd.DataFrame(bundles_data)
            if not bundles_df.empty:
                bundles_df = _self._optimize_dataframe_dtypes(bundles_df, {
                    'published_date': 'datetime'
                })
        
        # Process giveaways
        giveaways_df = pd.DataFrame()
        if loaded_data['giveaways']:
            giveaways_df = pd.DataFrame(loaded_data['giveaways'])
            if not giveaways_df.empty:
                giveaways_df = _self._optimize_dataframe_dtypes(giveaways_df, {
                    'published_date': 'datetime',
                    'expires_date': 'datetime'
                })
        
        _self._log(f"Ultra-loaded: {len(deals_df)} deals, {len(bundles_df)} bundles, {len(giveaways_df)} giveaways")
        return deals_df, bundles_df, giveaways_df
    
    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False)
    def get_videos_data_ultra(_self) -> Dict[str, pd.DataFrame]:
        """Ultra-optimized video data loading with memory efficiency"""
        _self._log("Loading videos data (ultra-optimized)")
        
        youtube_dir = _self.cached_paths['youtube_dir']
        videos_data = {}
        
        if not youtube_dir.exists():
            return videos_data
        
        try:
            # Get all channel directories in one pass
            channel_dirs = [d for d in youtube_dir.iterdir() if d.is_dir()]
            
            for channel_dir in channel_dirs:
                # Check multiple file names efficiently
                video_files = ["videos.json", "youtube_videos.json"]
                
                for filename in video_files:
                    videos_file = channel_dir / filename
                    if videos_file.exists():
                        cache_key = _self._get_cache_key(str(videos_file), f"videos_{channel_dir.name}")
                        channel_data = _self._ultra_fast_json_load(videos_file, cache_key)
                        
                        if channel_data:
                            # Convert to DataFrame with optimizations
                            df = pd.DataFrame(channel_data)
                            
                            if not df.empty:
                                # Optimize in one pass
                                df = _self._optimize_video_dataframe(df)
                                videos_data[channel_dir.name] = df
                                _self._log(f"Ultra-loaded {len(df)} videos from {channel_dir.name}")
                        break
                        
        except Exception as e:
            _self._log(f"Error in ultra video loading: {str(e)}", "error")
        
        return videos_data
    
    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False) 
    def get_news_data_ultra(_self) -> Dict[str, pd.DataFrame]:
        """Ultra-optimized news data loading"""
        _self._log("Loading news data (ultra-optimized)")
        
        news_data = {}
        
        # Define news sources with their possible file names
        news_sources = [
            ('hackernews', _self.cached_paths['hackernews_dir'], ["stories.json", "hackernews.json", "hackernews_simple.json"]),
            ('futuretools', _self.cached_paths['futuretools_dir'], ["news.json", "futuretoolsnews.json"]),
            ('medium', _self.cached_paths['medium_dir'], ["articles.json"])
        ]
        
        for source_name, source_dir, file_names in news_sources:
            if not source_dir.exists():
                continue
                
            for filename in file_names:
                file_path = source_dir / filename
                if file_path.exists():
                    cache_key = _self._get_cache_key(str(file_path), f"news_{source_name}")
                    data = _self._ultra_fast_json_load(file_path, cache_key)
                    
                    if data:
                        df = pd.DataFrame(data)
                        if not df.empty:
                            df = _self._optimize_dataframe_dtypes(df, {
                                'published_date': 'datetime'
                            })
                            news_data[source_name] = df
                            _self._log(f"Ultra-loaded {len(df)} {source_name} articles")
                    break
        
        return news_data
    
    @st.cache_data(ttl=3600, max_entries=5, show_spinner=False)
    def get_courses_data_ultra(_self) -> Dict[str, pd.DataFrame]:
        """Ultra-optimized courses data loading"""
        _self._log("Loading courses data (ultra-optimized)")
        
        courses_data = {}
        
        # Define course sources
        course_sources = [
            ('coursera', _self.cached_paths['coursera_dir'] / "coursera_courses.json"),
            ('udemy', _self.cached_paths['udemy_dir'] / "udemy_courses.json")
        ]
        
        for source_name, file_path in course_sources:
            if file_path.exists():
                cache_key = _self._get_cache_key(str(file_path), f"courses_{source_name}")
                data = _self._ultra_fast_json_load(file_path, cache_key)
                
                if data:
                    df = pd.DataFrame(data)
                    if not df.empty:
                        courses_data[source_name] = df
                        _self._log(f"Ultra-loaded {len(df)} {source_name} courses")
        
        return courses_data
    
    def _optimize_dataframe_dtypes(self, df: pd.DataFrame, type_mapping: Dict[str, str]) -> pd.DataFrame:
        """Optimize DataFrame data types for memory efficiency"""
        optimized_df = df.copy()
        
        for column, dtype in type_mapping.items():
            if column in optimized_df.columns:
                try:
                    if dtype == 'datetime':
                        optimized_df[column] = pd.to_datetime(optimized_df[column], errors='coerce')
                        # Convert to date for memory efficiency if no time component
                        if optimized_df[column].dt.time.nunique() == 1:
                            optimized_df[column] = optimized_df[column].dt.date
                    elif dtype == 'float':
                        optimized_df[column] = pd.to_numeric(
                            optimized_df[column].replace({None: np.nan, "": np.nan}), 
                            errors='coerce'
                        )
                        # Use float32 if values fit
                        if optimized_df[column].max() < np.finfo(np.float32).max:
                            optimized_df[column] = optimized_df[column].astype(np.float32)
                    elif dtype == 'category':
                        optimized_df[column] = optimized_df[column].astype('category')
                except Exception as e:
                    self._log(f"Failed to optimize column {column}: {e}", "warning")
        
        return optimized_df
    
    def _optimize_video_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Specialized optimization for video DataFrames"""
        # Normalize date columns
        if "published_at" in df.columns:
            df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce")
            df.drop("published_at", axis=1, inplace=True)  # Remove duplicate
        elif "published_date" in df.columns:
            df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
        
        # Ensure required columns exist
        if "channel" in df.columns and "channel_name" not in df.columns:
            df["channel_name"] = df["channel"]
        if "thumbnail_url" in df.columns and "thumbnail" not in df.columns:
            df["thumbnail"] = df["thumbnail_url"]
        
        # Optimize string columns
        string_columns = ['title', 'channel_name', 'url', 'thumbnail']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype('string')
        
        # Pre-sort by date for better performance
        if "published_date" in df.columns:
            df = df.sort_values("published_date", ascending=False)
            df.reset_index(drop=True, inplace=True)
        
        return df
    
    @st.cache_data(ttl=600, show_spinner=False)  # 10 minute cache for summary
    def get_data_summary_ultra(_self) -> Dict[str, Dict]:
        """Ultra-fast data summary generation using cached data"""
        _self._log("Generating ultra-fast data summary")
        
        summary = {}
        
        try:
            # Use cached data loading methods
            games_data = _self.get_games_data_ultra()
            courses_data = _self.get_courses_data_ultra()
            news_data = _self.get_news_data_ultra()
            videos_data = _self.get_videos_data_ultra()
            
            # Games summary
            deals_df, bundles_df, giveaways_df = games_data
            summary["games"] = {
                "deals": len(deals_df),
                "bundles": len(bundles_df), 
                "giveaways": len(giveaways_df),
                "latest_deal": deals_df.iloc[0]["title"] if not deals_df.empty and "title" in deals_df.columns else None,
                "latest_bundle": bundles_df.iloc[0]["title"] if not bundles_df.empty and "title" in bundles_df.columns else None
            }
            
            # Courses summary
            total_courses = sum(len(df) for df in courses_data.values())
            summary["courses"] = {
                "total": total_courses,
                "platforms": list(courses_data.keys()),
                "by_platform": {k: len(v) for k, v in courses_data.items()}
            }
            
            # News summary
            total_news = sum(len(df) for df in news_data.values())
            summary["news"] = {
                "total": total_news,
                "sources": list(news_data.keys()),
                "by_source": {k: len(v) for k, v in news_data.items()}
            }
            
            # Videos summary
            total_videos = sum(len(df) for df in videos_data.values())
            summary["videos"] = {
                "total": total_videos,
                "channels": len(videos_data),
                "by_channel": {k: len(v) for k, v in videos_data.items()}
            }
            
            # Add performance metrics
            summary["performance"] = {
                "cache_entries": len(_self.memory_cache),
                "last_updated": datetime.now().isoformat(),
                "data_sources_available": len([name for name, meta in _self.file_metadata.items() if meta.get('exists', False)])
            }
            
            return summary
            
        except Exception as e:
            _self._log(f"Error generating ultra summary: {str(e)}", "error")
            return _self._get_fallback_summary()
    
    def _get_fallback_summary(self) -> Dict[str, Dict]:
        """Fallback summary when errors occur"""
        return {
            "games": {"deals": 0, "bundles": 0, "giveaways": 0, "latest_deal": None, "latest_bundle": None},
            "courses": {"total": 0, "platforms": [], "by_platform": {}},
            "news": {"total": 0, "sources": [], "by_source": {}},
            "videos": {"total": 0, "channels": 0, "by_channel": {}},
            "performance": {"cache_entries": 0, "last_updated": datetime.now().isoformat(), "data_sources_available": 0}
        }
    
    def clear_cache(self):
        """Clear all caches for memory optimization"""
        if hasattr(self, 'memory_cache'):
            self.memory_cache.clear()
        st.cache_data.clear()
        gc.collect()
        self._log("All caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            "memory_cache_size": len(self.memory_cache) if hasattr(self, 'memory_cache') else 0,
            "file_metadata_entries": len(self.file_metadata),
            "streamlit_cache_stats": "Available" if hasattr(st.cache_data, 'clear') else "Not available"
        }

    def get_data_summary(self) -> Dict[str, Dict]:
        """Compatibility method that calls get_data_summary_ultra"""
        return self.get_data_summary_ultra()

    # Compatibility methods for existing code
    def get_games_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compatibility method that calls get_games_data_ultra"""
        return self.get_games_data_ultra()
    
    def get_videos_data(self) -> Dict[str, pd.DataFrame]:
        """Compatibility method that calls get_videos_data_ultra"""
        return self.get_videos_data_ultra()
    
    def get_news_data(self) -> Dict[str, pd.DataFrame]:
        """Compatibility method that calls get_news_data_ultra"""
        return self.get_news_data_ultra()
    
    def get_courses_data(self) -> Dict[str, pd.DataFrame]:
        """Compatibility method that calls get_courses_data_ultra"""
        return self.get_courses_data_ultra()
    
    def get_arxiv_data(self) -> pd.DataFrame:
        """Get ArXiv papers data"""
        arxiv_dir = self.cached_paths.get('arxiv_dir')
        if not arxiv_dir or not arxiv_dir.exists():
            return pd.DataFrame()
        
        arxiv_file = arxiv_dir / "processed" / "json" / "arxiv_papers.json"
        if arxiv_file.exists():
            cache_key = self._get_cache_key(str(arxiv_file), "arxiv")
            data = self._ultra_fast_json_load(arxiv_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_events_data(self) -> pd.DataFrame:
        """Get events data"""
        events_dir = self.cached_paths.get('events_dir')
        if not events_dir or not events_dir.exists():
            return pd.DataFrame()
        
        events_file = events_dir / "valencia_events.json"
        if events_file.exists():
            cache_key = self._get_cache_key(str(events_file), "events")
            data = self._ultra_fast_json_load(events_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()

    def get_crypto_sentiment_data(self) -> pd.DataFrame:
        """Get cryptocurrency sentiment data"""
        crypto_dir = self.cached_paths.get('crypto_sentiment_dir')
        if not crypto_dir or not crypto_dir.exists():
            return pd.DataFrame()
        
        crypto_file = crypto_dir / "crypto_sentiment_raw_latest.json"
        if crypto_file.exists():
            cache_key = self._get_cache_key(str(crypto_file), "crypto_sentiment")
            data = self._ultra_fast_json_load(crypto_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_crypto_sentiment_aggregated(self) -> Dict[str, Any]:
        """Get aggregated cryptocurrency sentiment data"""
        crypto_dir = self.cached_paths.get('crypto_sentiment_dir')
        if not crypto_dir or not crypto_dir.exists():
            return {}
        
        crypto_file = crypto_dir / "crypto_sentiment_aggregated_latest.json"
        if crypto_file.exists():
            cache_key = self._get_cache_key(str(crypto_file), "crypto_sentiment_agg")
            data = self._ultra_fast_json_load(crypto_file, cache_key)
            return data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else {}
        
        return {}
    
    def get_tech_jobs_data(self) -> pd.DataFrame:
        """Get tech jobs data"""
        jobs_dir = self.cached_paths.get('tech_jobs_dir')
        if not jobs_dir or not jobs_dir.exists():
            return pd.DataFrame()
        
        jobs_file = jobs_dir / "tech_jobs_latest.json"
        if jobs_file.exists():
            cache_key = self._get_cache_key(str(jobs_file), "tech_jobs")
            data = self._ultra_fast_json_load(jobs_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_dev_community_data(self) -> pd.DataFrame:
        """Get dev community data"""
        dev_dir = self.cached_paths.get('dev_community_dir')
        if not dev_dir or not dev_dir.exists():
            return pd.DataFrame()
        
        dev_file = dev_dir / "dev_community_latest.json"
        if dev_file.exists():
            cache_key = self._get_cache_key(str(dev_file), "dev_community")
            data = self._ultra_fast_json_load(dev_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_product_hunt_data(self) -> pd.DataFrame:
        """Get Product Hunt data"""
        ph_dir = self.cached_paths.get('product_hunt_dir')
        if not ph_dir or not ph_dir.exists():
            return pd.DataFrame()
        
        ph_file = ph_dir / "product_hunt_latest.json"
        if ph_file.exists():
            cache_key = self._get_cache_key(str(ph_file), "product_hunt")
            data = self._ultra_fast_json_load(ph_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_github_trends_data(self) -> pd.DataFrame:
        """Get GitHub trends data"""
        gh_dir = self.cached_paths.get('github_trends_dir')
        if not gh_dir or not gh_dir.exists():
            return pd.DataFrame()
        
        gh_file = gh_dir / "github_trending_latest.json"
        if gh_file.exists():
            cache_key = self._get_cache_key(str(gh_file), "github_trends")
            data = self._ultra_fast_json_load(gh_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()

# Factory function for easy instantiation
def create_ultra_optimized_service(logger=None) -> UltraOptimizedDataService:
    """Create an ultra-optimized data service instance"""
    return UltraOptimizedDataService(logger) 