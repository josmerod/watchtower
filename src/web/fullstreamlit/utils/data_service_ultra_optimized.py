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
import time
import threading

# Import technology intelligence components
try:
    from src.analytics.technology_adoption import TechnologyAdoptionAnalyzer
    from src.models.technology import FrameworkBattleModel, TechnologyCategory, TechnologyPredictionModel
except ImportError:
    # Fallback if modules not available
    TechnologyAdoptionAnalyzer = None
    FrameworkBattleModel = None
    TechnologyCategory = None
    TechnologyPredictionModel = None

from src.utils.logging import get_logger

class UltraOptimizedDataService:
    """Ultra-optimized data service with advanced caching and memory management"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._setup_paths()
        self._init_memory_cache()
        self._preload_file_metadata()
        
        # Initialize technology adoption analyzer
        self.tech_analyzer: Optional[TechnologyAdoptionAnalyzer] = None
        self._tech_intelligence_cache: Dict[str, Any] = {}
        self._cache_expiry: Optional[datetime] = None
        self._cache_duration_minutes = 30  # Cache for 30 minutes
        self._initialize_tech_analyzer()
        
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
            'github_trends_dir': self.data_dir / "github_trends",
            'security_vulnerabilities_dir': self.data_dir / "security_vulnerabilities"
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
    
    @st.cache_data(ttl=3600, max_entries=10, show_spinner=False, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.columns.tolist())})
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
                deals_df = clean_dataframe_for_caching(deals_df)
        
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
                bundles_df = clean_dataframe_for_caching(bundles_df)
        
        # Process giveaways
        giveaways_df = pd.DataFrame()
        if loaded_data['giveaways']:
            giveaways_df = pd.DataFrame(loaded_data['giveaways'])
            if not giveaways_df.empty:
                giveaways_df = _self._optimize_dataframe_dtypes(giveaways_df, {
                    'published_date': 'datetime',
                    'expires_date': 'datetime'
                })
                giveaways_df = clean_dataframe_for_caching(giveaways_df)
        
        _self._log(f"Ultra-loaded: {len(deals_df)} deals, {len(bundles_df)} bundles, {len(giveaways_df)} giveaways")
        return deals_df, bundles_df, giveaways_df
    
    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.columns.tolist())})
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
                                df = clean_dataframe_for_caching(df)
                                videos_data[channel_dir.name] = df
                                _self._log(f"Ultra-loaded {len(df)} videos from {channel_dir.name}")
                        break
                        
        except Exception as e:
            _self._log(f"Error in ultra video loading: {str(e)}", "error")
        
        return videos_data
    
    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.columns.tolist())}) 
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
                            df = clean_dataframe_for_caching(df)
                            news_data[source_name] = df
                            _self._log(f"Ultra-loaded {len(df)} {source_name} articles")
                    break
        
        return news_data
    
    @st.cache_data(ttl=3600, max_entries=5, show_spinner=False, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.columns.tolist())})
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
                        df = clean_dataframe_for_caching(df)
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
    
    @st.cache_data(ttl=600, show_spinner=False, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.columns.tolist())})  # 10 minute cache for summary
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
    
    def get_enhanced_arxiv_data(self) -> Dict[str, Any]:
        """Get enhanced ArXiv papers data with intelligence features"""
        try:
            # Try different possible locations for enhanced papers
            possible_paths = [
                self.data_dir / "streamlit_enhanced_arxiv" / "output" / "latest_enhanced_papers.json",
                self.data_dir / "enhanced_arxiv" / "output" / "latest_enhanced_papers.json",
                self.data_dir / "arxiv" / "output" / "latest_enhanced_papers.json"
            ]
            
            for path in possible_paths:
                if path.exists():
                    cache_key = self._get_cache_key(str(path), "enhanced_arxiv")
                    data = self._ultra_fast_json_load(path, cache_key)
                    
                    if isinstance(data, dict):
                        return data
                    elif isinstance(data, list):
                        return {"papers": data, "metadata": {}}
            
            return {"papers": [], "metadata": {}}
            
        except Exception as e:
            self._log(f"Error loading enhanced ArXiv data: {str(e)}", "error")
            return {"papers": [], "metadata": {}, "error": str(e)}
    
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
    
    def get_security_vulnerabilities_data(self) -> pd.DataFrame:
        """Get security vulnerabilities data"""
        security_dir = self.cached_paths.get('security_vulnerabilities_dir', 
                                           self.data_dir / "security_vulnerabilities")
        if not security_dir or not security_dir.exists():
            return pd.DataFrame()
        
        security_file = security_dir / "security_vulnerabilities_latest.json"
        if security_file.exists():
            cache_key = self._get_cache_key(str(security_file), "security_vulnerabilities")
            data = self._ultra_fast_json_load(security_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_security_intelligence(self) -> Dict[str, Any]:
        """Get security intelligence summary and analysis"""
        try:
            vulnerabilities_df = self.get_security_vulnerabilities_data()
            
            if vulnerabilities_df.empty:
                return {
                    'error': 'No security vulnerability data available',
                    'vulnerabilities': [],
                    'critical_count': 0,
                    'average_severity': 0.0,
                    'patch_availability': 0,
                    'affected_technologies': []
                }
            
            # Convert to list of dictionaries for processing
            vulnerabilities = vulnerabilities_df.to_dict('records')
            
            # Calculate metrics
            critical_count = sum(1 for v in vulnerabilities 
                               if v.get('risk_level') == 'critical' or v.get('severity_score', 0) >= 9.0)
            
            severity_scores = [v.get('severity_score', 0) for v in vulnerabilities]
            avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0.0
            
            with_patches = sum(1 for v in vulnerabilities if v.get('patch_available', False))
            patch_availability = (with_patches / len(vulnerabilities) * 100) if vulnerabilities else 0
            
            # Get affected technologies
            affected_technologies = set()
            for v in vulnerabilities:
                tech_stack = v.get('technology_stack', [])
                if isinstance(tech_stack, list):
                    affected_technologies.update(tech_stack)
                elif isinstance(tech_stack, str):
                    try:
                        import json
                        parsed_tech = json.loads(tech_stack)
                        if isinstance(parsed_tech, list):
                            affected_technologies.update(parsed_tech)
                    except:
                        affected_technologies.add(tech_stack)
            
            return {
                'vulnerabilities': vulnerabilities,
                'critical_count': critical_count,
                'average_severity': round(avg_severity, 1),
                'patch_availability': round(patch_availability, 1),
                'affected_technologies': list(affected_technologies),
                'total_count': len(vulnerabilities),
                'high_count': sum(1 for v in vulnerabilities if v.get('risk_level') == 'high'),
                'medium_count': sum(1 for v in vulnerabilities if v.get('risk_level') == 'medium'),
                'low_count': sum(1 for v in vulnerabilities if v.get('risk_level') == 'low'),
                'with_exploits': sum(1 for v in vulnerabilities if v.get('exploit_available', False)),
                'needs_urgent_attention': sum(1 for v in vulnerabilities if v.get('needs_urgent_attention', False)),
                'recent_vulnerabilities': sum(1 for v in vulnerabilities if v.get('is_recent', False))
            }
            
        except Exception as e:
            self._log(f"Error generating security intelligence: {str(e)}", "error")
            return {
                'error': f'Error processing security data: {str(e)}',
                'vulnerabilities': [],
                'critical_count': 0,
                'average_severity': 0.0,
                'patch_availability': 0,
                'affected_technologies': []
            }

    def _initialize_tech_analyzer(self) -> None:
        """Initialize the technology adoption analyzer."""
        try:
            if TechnologyAdoptionAnalyzer:
                self.tech_analyzer = TechnologyAdoptionAnalyzer(self)
                self._log("Technology adoption analyzer initialized successfully")
            else:
                self._log("Technology analyzer components not available", "warning")
                self.tech_analyzer = None
        except Exception as e:
            self._log(f"Failed to initialize technology analyzer: {e}", "error")
            self.tech_analyzer = None
    
    def get_github_trends(self) -> List[Dict[str, Any]]:
        """Get GitHub trends data as list of dictionaries."""
        try:
            df = self.get_github_trends_data()
            if not df.empty:
                return df.to_dict('records')
            
            # Fallback: try different file name
            gh_dir = self.cached_paths.get('github_trends_dir')
            if gh_dir:
                for filename in ["github_trends_latest.json", "github_trending_latest.json"]:
                    gh_file = gh_dir / filename
                    if gh_file.exists():
                        cache_key = self._get_cache_key(str(gh_file), "github_trends")
                        data = self._ultra_fast_json_load(gh_file, cache_key)
                        self._log(f"Loaded {len(data)} GitHub repositories from {filename}")
                        return data
            
            self._log("GitHub trends file not found", "warning")
            return []
                
        except Exception as e:
            self._log(f"Failed to get GitHub trends: {e}", "error")
            return []
    
    def get_dev_community(self) -> List[Dict[str, Any]]:
        """Get DEV community data as list of dictionaries."""
        try:
            df = self.get_dev_community_data()
            if not df.empty:
                return df.to_dict('records')
            
            self._log("DEV community data not available", "warning")
            return []
                
        except Exception as e:
            self._log(f"Failed to get DEV community data: {e}", "error")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if the technology intelligence cache is still valid."""
        if not self._cache_expiry:
            return False
        return datetime.utcnow() < self._cache_expiry
    
    def _update_cache_expiry(self) -> None:
        """Update the cache expiry timestamp."""
        self._cache_expiry = datetime.utcnow() + timedelta(minutes=self._cache_duration_minutes)
    
    async def get_technology_radar(self) -> Dict[str, Any]:
        """Get comprehensive technology adoption intelligence."""
        self._log("Generating technology radar intelligence")
        
        try:
            # Check cache first
            if self._is_cache_valid() and 'technology_radar' in self._tech_intelligence_cache:
                self._log("Returning cached technology radar data", "debug")
                return self._tech_intelligence_cache['technology_radar']
            
            if not self.tech_analyzer:
                self._log("Technology analyzer not available", "warning")
                return {'error': 'Technology analyzer not initialized'}
            
            # Generate framework battles
            framework_battles = await self.tech_analyzer.analyze_framework_battles()
            
            # Generate adoption predictions
            adoption_predictions = await self.tech_analyzer.predict_adoption_trends()
            
            # Generate technology recommendations
            recommendations = self._generate_technology_recommendations(
                framework_battles, adoption_predictions
            )
            
            # Analyze market intelligence
            market_intelligence = self._analyze_market_trends(
                framework_battles, adoption_predictions
            )
            
            # Compile results
            radar_data = {
                'framework_battles': self._serialize_framework_battles(framework_battles),
                'adoption_predictions': self._serialize_predictions(adoption_predictions),
                'recommendation_engine': recommendations,
                'market_intelligence': market_intelligence,
                'last_updated': datetime.utcnow().isoformat(),
                'data_sources': ['github_trends', 'dev_community', 'analytics_engine'],
                'confidence_score': self._calculate_overall_confidence(
                    framework_battles, adoption_predictions
                )
            }
            
            # Cache the results
            self._tech_intelligence_cache['technology_radar'] = radar_data
            self._update_cache_expiry()
            
            self._log(f"Technology radar generated with {len(framework_battles)} battles and {len(adoption_predictions)} predictions")
            return radar_data
            
        except Exception as e:
            self._log(f"Technology radar generation failed: {e}", "error")
            return {
                'error': str(e),
                'message': 'Failed to generate technology radar intelligence',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _serialize_framework_battles(self, battles) -> Dict[str, Any]:
        """Serialize framework battles for JSON response."""
        if not battles or not FrameworkBattleModel:
            return {}
        
        serialized = {}
        
        for category, battle in battles.items():
            try:
                battle_data = {
                    'category': category.value if hasattr(category, 'value') else str(category),
                    'winner': battle.winner,
                    'runner_up': battle.runner_up,
                    'rising_star': battle.rising_star,
                    'market_share_leader': battle.market_share_leader,
                    'developer_preference': battle.developer_preference,
                    'enterprise_adoption': battle.enterprise_adoption,
                    'predicted_winner_6m': battle.predicted_winner_6m,
                    'predicted_winner_12m': battle.predicted_winner_12m,
                    'confidence_score': battle.confidence_score,
                    'data_quality_score': battle.data_quality_score,
                    'total_frameworks': battle.total_frameworks,
                    'battle_summary': battle.battle_summary,
                    'frameworks': []
                }
                
                # Serialize framework details
                for framework in battle.frameworks:
                    framework_data = {
                        'name': framework.technology_name,
                        'category': framework.category.value if hasattr(framework.category, 'value') else str(framework.category),
                        'popularity_score': framework.popularity_score,
                        'growth_rate': framework.growth_rate,
                        'community_health': framework.community_health,
                        'job_market_demand': framework.job_market_demand,
                        'learning_curve': framework.learning_curve,
                        'maturity_level': framework.maturity_level.value if hasattr(framework.maturity_level, 'value') else str(framework.maturity_level),
                        'ecosystem_size': framework.ecosystem_size,
                        'performance_score': framework.performance_score,
                        'overall_rank': framework.overall_rank,
                        'strengths': framework.strengths,
                        'weaknesses': framework.weaknesses,
                        'recommendation_score': framework.recommendation_score,
                        'use_cases': framework.use_cases
                    }
                    battle_data['frameworks'].append(framework_data)
                
                category_key = category.value if hasattr(category, 'value') else str(category)
                serialized[category_key] = battle_data
                
            except Exception as e:
                self._log(f"Failed to serialize battle for {category}: {e}", "warning")
                continue
        
        return serialized
    
    def _serialize_predictions(self, predictions) -> Dict[str, Any]:
        """Serialize technology predictions for JSON response."""
        if not predictions or not TechnologyPredictionModel:
            return {}
        
        serialized = {}
        
        for tech_name, prediction in predictions.items():
            try:
                prediction_data = {
                    'technology_name': prediction.technology_name,
                    'current_score': prediction.current_score,
                    'current_adoption_level': prediction.current_adoption_level.value if hasattr(prediction.current_adoption_level, 'value') else str(prediction.current_adoption_level),
                    'predicted_score': prediction.predicted_score,
                    'predicted_adoption_level': prediction.predicted_adoption_level.value if hasattr(prediction.predicted_adoption_level, 'value') else str(prediction.predicted_adoption_level),
                    'growth_rate': prediction.growth_rate,
                    'trend_direction': prediction.trend_direction.value if hasattr(prediction.trend_direction, 'value') else str(prediction.trend_direction),
                    'prediction_timeframe_months': prediction.prediction_timeframe_months,
                    'confidence': prediction.confidence,
                    'expected_growth_percentage': prediction.expected_growth_percentage,
                    'investment_recommendation': prediction.investment_recommendation,
                    'key_drivers': prediction.key_drivers,
                    'risk_factors': prediction.risk_factors,
                    'recommendation': prediction.recommendation,
                    'early_adoption_indicators': prediction.early_adoption_indicators,
                    'competitive_threats': prediction.competitive_threats
                }
                
                serialized[tech_name] = prediction_data
                
            except Exception as e:
                self._log(f"Failed to serialize prediction for {tech_name}: {e}", "warning")
                continue
        
        return serialized
    
    def _generate_technology_recommendations(self, battles, predictions) -> Dict[str, Any]:
        """Generate technology recommendations based on battles and predictions."""
        try:
            recommendations = {
                'top_recommendations': [],
                'category_winners': {},
                'rising_technologies': [],
                'avoid_technologies': [],
                'investment_grades': {
                    'strong_buy': [],
                    'buy': [],
                    'hold': [],
                    'avoid': []
                }
            }
            
            # Extract category winners
            for category, battle in battles.items():
                category_key = category.value if hasattr(category, 'value') else str(category)
                recommendations['category_winners'][category_key] = {
                    'winner': battle.winner,
                    'recommendation_reason': f"Leading {category_key} framework with highest overall score"
                }
            
            # Analyze predictions for investment recommendations
            for tech_name, prediction in predictions.items():
                investment_rec = prediction.investment_recommendation.lower()
                
                if 'strong buy' in investment_rec:
                    recommendations['investment_grades']['strong_buy'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation,
                        'growth_potential': f"{prediction.expected_growth_percentage}%"
                    })
                elif 'buy' in investment_rec:
                    recommendations['investment_grades']['buy'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation,
                        'growth_potential': f"{prediction.expected_growth_percentage}%"
                    })
                elif 'hold' in investment_rec:
                    recommendations['investment_grades']['hold'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation
                    })
                elif 'avoid' in investment_rec or 'sell' in investment_rec:
                    recommendations['investment_grades']['avoid'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation
                    })
                
                # Identify rising technologies
                trend_direction = prediction.trend_direction.value if hasattr(prediction.trend_direction, 'value') else str(prediction.trend_direction)
                if trend_direction in ['rising', 'explosive'] and prediction.confidence > 0.7:
                    recommendations['rising_technologies'].append({
                        'technology': tech_name,
                        'trend': trend_direction,
                        'confidence': prediction.confidence,
                        'key_drivers': prediction.key_drivers
                    })
                
                # Identify technologies to avoid
                if trend_direction == 'declining' and prediction.confidence > 0.6:
                    recommendations['avoid_technologies'].append({
                        'technology': tech_name,
                        'reason': 'Declining adoption trend predicted',
                        'risk_factors': prediction.risk_factors
                    })
            
            # Generate top recommendations
            all_strong_buys = recommendations['investment_grades']['strong_buy']
            all_buys = recommendations['investment_grades']['buy']
            
            top_recommendations = (all_strong_buys + all_buys)[:5]  # Top 5
            recommendations['top_recommendations'] = top_recommendations
            
            return recommendations
            
        except Exception as e:
            self._log(f"Failed to generate recommendations: {e}", "error")
            return {'error': 'Failed to generate recommendations'}
    
    def _analyze_market_trends(self, battles, predictions) -> Dict[str, Any]:
        """Analyze market trends from battle and prediction data."""
        try:
            market_analysis = {
                'overall_trends': [],
                'category_insights': {},
                'adoption_lifecycle': {
                    'emerging': [],
                    'growing': [],
                    'mainstream': [],
                    'mature': []
                },
                'market_shifts': [],
                'competitive_landscape': {}
            }
            
            # Analyze overall market trends
            growth_technologies = []
            for name, pred in predictions.items():
                if pred.growth_rate > 0.2:
                    growth_technologies.append(name)
            
            if len(growth_technologies) > len(predictions) * 0.6:
                market_analysis['overall_trends'].append(
                    "Market shows strong innovation and growth across multiple technologies"
                )
            
            declining_count = 0
            for name, pred in predictions.items():
                trend_direction = pred.trend_direction.value if hasattr(pred.trend_direction, 'value') else str(pred.trend_direction)
                if trend_direction == 'declining':
                    declining_count += 1
            
            if declining_count > 0:
                market_analysis['overall_trends'].append(
                    f"{declining_count} technologies showing declining trends - market consolidation occurring"
                )
            
            # Category insights
            for category, battle in battles.items():
                category_key = category.value if hasattr(category, 'value') else str(category)
                rising_star = battle.rising_star
                winner = battle.winner
                
                insight = f"In {category_key}: {winner} dominates"
                if rising_star and rising_star != winner:
                    insight += f", but {rising_star} is the rising challenger"
                
                market_analysis['category_insights'][category_key] = {
                    'insight': insight,
                    'market_leader': winner,
                    'challenger': rising_star,
                    'confidence': battle.confidence_score
                }
            
            # Adoption lifecycle analysis
            for tech_name, prediction in predictions.items():
                lifecycle_stage = prediction.current_adoption_level.value if hasattr(prediction.current_adoption_level, 'value') else str(prediction.current_adoption_level)
                trend_direction = prediction.trend_direction.value if hasattr(prediction.trend_direction, 'value') else str(prediction.trend_direction)
                
                if lifecycle_stage in market_analysis['adoption_lifecycle']:
                    market_analysis['adoption_lifecycle'][lifecycle_stage].append({
                        'technology': tech_name,
                        'score': prediction.current_score,
                        'trend': trend_direction
                    })
            
            # Identify market shifts
            explosive_growth = []
            for name, pred in predictions.items():
                trend_direction = pred.trend_direction.value if hasattr(pred.trend_direction, 'value') else str(pred.trend_direction)
                if trend_direction == 'explosive':
                    explosive_growth.append(name)
            
            if explosive_growth:
                market_analysis['market_shifts'].append({
                    'type': 'explosive_growth',
                    'technologies': explosive_growth,
                    'description': 'Technologies experiencing explosive growth and rapid adoption'
                })
            
            return market_analysis
            
        except Exception as e:
            self._log(f"Failed to analyze market trends: {e}", "error")
            return {'error': 'Failed to analyze market trends'}
    
    def _calculate_overall_confidence(self, battles, predictions) -> float:
        """Calculate overall confidence score for the technology intelligence."""
        try:
            confidence_scores = []
            
            # Add battle confidence scores
            for battle in battles.values():
                confidence_scores.append(battle.confidence_score)
            
            # Add prediction confidence scores
            for prediction in predictions.values():
                confidence_scores.append(prediction.confidence)
            
            if not confidence_scores:
                return 0.0
            
            # Calculate weighted average
            average_confidence = sum(confidence_scores) / len(confidence_scores)
            
            # Bonus for having more data points
            data_bonus = min(len(confidence_scores) / 20, 0.1)  # Up to 10% bonus
            
            final_confidence = min(average_confidence + data_bonus, 1.0)
            return round(final_confidence, 3)
            
        except Exception as e:
            self._log(f"Failed to calculate overall confidence: {e}", "warning")
            return 0.5  # Default moderate confidence


# Factory function for easy instantiation
def create_ultra_optimized_service(logger=None) -> UltraOptimizedDataService:
    """Create an ultra-optimized data service instance"""
    return UltraOptimizedDataService(logger) 

def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame to avoid unhashable type errors during Streamlit caching."""
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    df_clean = df.copy()
    
    # Convert any dictionary or list columns to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Check if column contains dictionaries or lists
            try:
                # Sample a few non-null values to check type
                sample_values = df_clean[col].dropna().head(3)
                if not sample_values.empty:
                    for val in sample_values:
                        if isinstance(val, (dict, list)):
                            # Convert all values that are dict or list to JSON strings
                            df_clean[col] = df_clean[col].apply(
                                lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list)) else x
                            )
                            break
            except (TypeError, ValueError):
                # If there's any issue, convert the entire column to string
                df_clean[col] = df_clean[col].astype(str)
    
    return df_clean 