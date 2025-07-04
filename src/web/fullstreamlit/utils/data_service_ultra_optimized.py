"""Ultra-optimized data service for Streamlit dashboard.

High-performance data loading with advanced caching, memory management,
and parallel processing optimizations.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

# Import the logger conditionally
try:
    from utils.logging import get_logger
except ImportError:
    # Fallback logger if the module is not available
    import logging
    def get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

# Import technology analyzer
try:
    from analytics.technology_adoption import TechnologyAdoptionAnalyzer
except ImportError:
    TechnologyAdoptionAnalyzer = None

# NEW IMPORT: technology models for serialization
try:
    from models.technology import FrameworkBattleModel, TechnologyPredictionModel
except ImportError:
    FrameworkBattleModel = None  # type: ignore
    TechnologyPredictionModel = None  # type: ignore

# Import configuration
try:
    from config.settings import get_settings
except ImportError:
    def get_settings():
        return None

# Data cleaning and hashing functions (moved to top)
def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame for Streamlit caching by converting complex objects to strings.
    This prevents 'unhashable type: dict' errors in Streamlit's caching system.
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original
    df_clean = df.copy()

    # Convert problematic columns to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Check if any values are dictionaries, lists, or other complex objects
            sample_value = df_clean[col].iloc[0] if len(df_clean) > 0 else None
            if isinstance(sample_value, dict | list | set):
                # Convert complex objects to JSON strings
                def format_value(x):
                    if pd.isna(x):
                        return None
                    try:
                        if isinstance(x, dict | list | set):
                            return json.dumps(x, default=str)
                        return str(x)
                    except:
                        return str(x)

                df_clean[col] = df_clean[col].apply(format_value)

    return df_clean

# Custom hash function for DataFrames that handles complex objects
def safe_dataframe_hash(df: pd.DataFrame) -> str:
    """Safely hash a DataFrame by converting complex objects to strings first."""
    try:
        if df.empty:
            return "empty_dataframe"

        # Clean the DataFrame first
        df_clean = clean_dataframe_for_caching(df)

        # Create a simple hash based on shape and column names
        basic_hash = f"{df_clean.shape}_{hash(tuple(df_clean.columns))}"

        # Add a sample of the data for uniqueness
        if len(df_clean) > 0:
            sample_data = df_clean.head(3).to_string()
            basic_hash += f"_{hash(sample_data)}"

        return basic_hash
    except Exception as e:
        # Fallback to basic information
        return f"df_shape_{df.shape}_cols_{len(df.columns)}_error_{hash(str(e))}"

# Create a common hash function dictionary
SAFE_HASH_FUNCS = {
    pd.DataFrame: safe_dataframe_hash,
    dict: lambda d: hash(json.dumps(d, sort_keys=True, default=str)),
    list: lambda l: hash(json.dumps(l, default=str)),
    set: lambda s: hash(json.dumps(sorted(s), default=str))
}

class UltraOptimizedDataService:
    """Ultra-optimized data service with advanced caching and memory management."""

    def __init__(self, logger=None):
        self.logger = logger
        self._setup_paths()
        self._init_memory_cache()
        self._preload_file_metadata()

        # Initialize technology adoption analyzer
        self.tech_analyzer: TechnologyAdoptionAnalyzer | None = None
        self._tech_intelligence_cache: dict[str, Any] = {}
        self._cache_expiry: datetime | None = None
        self._cache_duration_minutes = 30  # Cache for 30 minutes
        self._initialize_tech_analyzer()

        # Performance monitoring
        self._performance_stats = {
            'load_times': {},
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }

    def _setup_paths(self):
        """Setup and cache all file paths to avoid repeated path operations."""
        current_dir = Path(__file__).parent
        self.data_dir = current_dir.parent.parent.parent.parent / "data"
        self._log(f"Data directory: {self.data_dir}")

        # Pre-cache all important paths
        self.cached_paths = {
            'games_dir': self.data_dir / "games",
            'allkeyshop_games_dir': self.data_dir / "allkeyshop_games" / "output",
            'youtube_dir': self.data_dir / "youtube",
            'hackernews_dir': self.data_dir / "hackernews",
            'futuretools_dir': self.data_dir / "futuretools",
            'medium_dir': self.data_dir / "medium_genai",
            'coursera_dir': self.data_dir / "classcentral",
            'udemy_dir': self.data_dir / "udemy",
            'deeplearningai_dir': self.data_dir / "deeplearningai",
            'arxiv_dir': self.data_dir / "arxiv",
            'events_dir': self.data_dir / "valencia_events",

            'tech_jobs_dir': self.data_dir / "tech_jobs",
            'dev_community_dir': self.data_dir / "dev_community",
            'product_hunt_dir': self.data_dir / "product_hunt",
            'github_trends_dir': self.data_dir / "github_trends",
            'security_vulnerabilities_dir': self.data_dir / "security_vulnerabilities",
            'home_server_trends_dir': self.data_dir / "home_server_trends",
            'museums_output_dir': self.data_dir / "virtual_museums_etl" / "output"
        }

    def _init_memory_cache(self):
        """Initialize in-memory cache for frequently accessed data."""
        if 'ultra_data_cache' not in st.session_state:
            st.session_state.ultra_data_cache = {}

        self.memory_cache = st.session_state.ultra_data_cache

    def _preload_file_metadata(self):
        """Pre-load file metadata to avoid repeated file existence checks."""
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
        """Optimized logging with reduced overhead."""
        if self.logger and hasattr(self.logger, level):
            getattr(self.logger, level)(message)

    @lru_cache(maxsize=1000)
    def _get_cache_key(self, file_path: str, operation: str) -> str:
        """Generate cache key using file hash for better cache invalidation."""
        try:
            path_obj = Path(file_path)
            if path_obj.exists():
                stat = path_obj.stat()
                # Use file size and modification time for cache key
                return hashlib.md5(f"{file_path}_{operation}_{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
            return hashlib.md5(f"{file_path}_{operation}_missing".encode()).hexdigest()
        except:
            return hashlib.md5(f"{file_path}_{operation}".encode()).hexdigest()

    def _ultra_fast_json_load(self, file_path: Path, cache_key: str) -> list[dict]:
        """Ultra-fast JSON loading with multiple optimization layers."""
        start_time = time.time()

        # Check memory cache first
        if cache_key in self.memory_cache:
            self._performance_stats['cache_hits'] += 1
            return self.memory_cache[cache_key]

        try:
            if not file_path.exists():
                self._track_performance(f"load_{file_path.name}", time.time() - start_time, False)
                return []

            # Read file in binary mode for speed with timeout protection
            try:
                with open(file_path, 'rb') as f:
                    # Load JSON with optimized settings
                    data = json.loads(f.read().decode('utf-8'))
            except Exception as read_error:
                self._log(f"File read error for {file_path}: {read_error}", "error")
                self._track_performance(f"load_{file_path.name}", time.time() - start_time, False)
                return []

            # Validate and cache
            if isinstance(data, list):
                # Store in memory cache with size limit
                if len(self.memory_cache) < 50:  # Limit cache size
                    self.memory_cache[cache_key] = data
                self._track_performance(f"load_{file_path.name}", time.time() - start_time, True)
                return data
            elif isinstance(data, dict):
                # Convert single dict to list for consistency
                result = [data]
                if len(self.memory_cache) < 50:
                    self.memory_cache[cache_key] = result
                self._track_performance(f"load_{file_path.name}", time.time() - start_time, True)
                return result
            else:
                self._log(f"Unexpected data type in {file_path}: {type(data)}", "warning")
                self._track_performance(f"load_{file_path.name}", time.time() - start_time, False)
                return []

        except Exception as e:
            self._log(f"Error loading {file_path}: {e!s}", "error")
            self._track_performance(f"load_{file_path.name}", time.time() - start_time, False)
            return []

    @st.cache_data(ttl=3600, max_entries=10, show_spinner=False)
    def get_games_data_ultra(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Ultra-optimized games data loading with parallel processing."""
        self._log("🔍 DEBUG: get_games_data_ultra called!")
        self._log("Loading games data (ultra-optimized)")

        games_dir = self.cached_paths['games_dir']

        # Define file operations, including Itch.io trending
        file_operations = [
            ('deals', games_dir / "deals.json"),
            ('bundles', games_dir / "bundles.json"),
            ('humble', games_dir / "humblebundles.json"),
            ('giveaways', games_dir / "giveaways.json"),
            ('itchio', games_dir / "itchio_trending.json")
        ]

        # Load files in parallel using cached operations
        loaded_data = {}
        for op_name, file_path in file_operations:
            self._log(f"🔍 DEBUG: Loading {op_name} from {file_path}")
            self._log(f"🔍 DEBUG: File exists: {file_path.exists()}")
            cache_key = self._get_cache_key(str(file_path), op_name)
            data = self._ultra_fast_json_load(file_path, cache_key)
            self._log(f"🔍 DEBUG: Loaded {len(data) if data else 0} items for {op_name}")
            loaded_data[op_name] = data

        # Process deals
        deals_df = pd.DataFrame()
        self._log(f"🔍 DEBUG: Processing deals, raw data length: {len(loaded_data.get('deals', []))}")
        if loaded_data['deals']:
            deals_df = pd.DataFrame(loaded_data['deals'])
            self._log(f"🔍 DEBUG: Created deals DataFrame with shape: {deals_df.shape}")
            # Optimize data types in one pass
            if not deals_df.empty:
                # Fix column name mismatches - convert 'published' to 'published_date'
                if 'published' in deals_df.columns and 'published_date' not in deals_df.columns:
                    deals_df['published_date'] = deals_df['published']
                    deals_df = deals_df.drop('published', axis=1)

                deals_df = self._optimize_dataframe_dtypes(deals_df, {
                    'published_date': 'datetime',
                    'price': 'float'
                })
                self._log(f"🔍 DEBUG: Deals DataFrame before cleaning: {deals_df.shape}")
                # TEMPORARILY DISABLED: deals_df = clean_dataframe_for_caching(deals_df)
                self._log(f"🔍 DEBUG: Deals DataFrame after cleaning (SKIPPED): {deals_df.shape}")

        # Process bundles (combine regular and humble)
        bundles_data = []
        self._log(f"🔍 DEBUG: Processing bundles, raw bundles: {len(loaded_data.get('bundles', []))}, humble: {len(loaded_data.get('humble', []))}")
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
        self._log(f"🔍 DEBUG: Combined bundles_data length: {len(bundles_data)}")
        if bundles_data:
            bundles_df = pd.DataFrame(bundles_data)
            self._log(f"🔍 DEBUG: Created bundles DataFrame with shape: {bundles_df.shape}")
            if not bundles_df.empty:
                # Fix column name mismatches - convert 'published' to 'published_date'
                if 'published' in bundles_df.columns:
                    if 'published_date' not in bundles_df.columns:
                        bundles_df['published_date'] = bundles_df['published']
                    bundles_df = bundles_df.drop('published', axis=1)

                bundles_df = self._optimize_dataframe_dtypes(bundles_df, {
                    'published_date': 'datetime'
                })
                self._log(f"🔍 DEBUG: Bundles DataFrame before cleaning: {bundles_df.shape}")
                # TEMPORARILY DISABLED: bundles_df = clean_dataframe_for_caching(bundles_df)
                self._log(f"🔍 DEBUG: Bundles DataFrame after cleaning (SKIPPED): {bundles_df.shape}")

        # Process giveaways
        giveaways_df = pd.DataFrame()
        self._log(f"🔍 DEBUG: Processing giveaways, raw data length: {len(loaded_data.get('giveaways', []))}")
        if loaded_data['giveaways']:
            giveaways_df = pd.DataFrame(loaded_data['giveaways'])
            self._log(f"🔍 DEBUG: Created giveaways DataFrame with shape: {giveaways_df.shape}")
            if not giveaways_df.empty:
                # Fix column name mismatches - convert 'published' to 'published_date' and 'expires' to 'expires_date'
                if 'published' in giveaways_df.columns:
                    giveaways_df['published_date'] = giveaways_df['published']
                    giveaways_df = giveaways_df.drop('published', axis=1)
                if 'expires' in giveaways_df.columns:
                    giveaways_df['expires_date'] = giveaways_df['expires']
                    giveaways_df = giveaways_df.drop('expires', axis=1)

                # Convert Unix timestamps to datetime strings
                for col in ['published_date', 'expires_date']:
                    if col in giveaways_df.columns:
                        # Check if values are Unix timestamps (integers)
                        if giveaways_df[col].dtype in ['int64', 'float64']:
                            # Convert Unix timestamps (milliseconds) to datetime strings
                            giveaways_df[col] = pd.to_datetime(giveaways_df[col], unit='ms', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

                giveaways_df = self._optimize_dataframe_dtypes(giveaways_df, {
                    'published_date': 'datetime',
                    'expires_date': 'datetime'
                })
                self._log(f"🔍 DEBUG: Giveaways DataFrame before cleaning: {giveaways_df.shape}")
                # TEMPORARILY DISABLED: giveaways_df = clean_dataframe_for_caching(giveaways_df)
                self._log(f"🔍 DEBUG: Giveaways DataFrame after cleaning (SKIPPED): {giveaways_df.shape}")

        # Process Itch.io trending games
        itchio_df = pd.DataFrame()
        if loaded_data.get('itchio'):
            itchio_df = pd.DataFrame(loaded_data['itchio'])
            if not itchio_df.empty:
                # TEMPORARILY DISABLED: itchio_df = clean_dataframe_for_caching(itchio_df)
                self._log(f"🔍 DEBUG: Itch.io DataFrame cleaning (SKIPPED): {itchio_df.shape}")

        self._log(f"🔍 DEBUG: Ultra-loaded: {len(deals_df)} deals, {len(bundles_df)} bundles, {len(giveaways_df)} giveaways, {len(itchio_df)} itch.io trending")
        self._log(f"🔍 DEBUG: Returning tuple with shapes: {deals_df.shape}, {bundles_df.shape}, {giveaways_df.shape}, {itchio_df.shape}")
        return deals_df, bundles_df, giveaways_df, itchio_df

    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False, hash_funcs=SAFE_HASH_FUNCS)
    def get_videos_data_ultra(self) -> dict[str, pd.DataFrame]:
        """Ultra-optimized video data loading with memory efficiency."""
        self._log("Loading videos data (ultra-optimized)")

        youtube_dir = self.cached_paths['youtube_dir']
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
                        cache_key = self._get_cache_key(str(videos_file), f"videos_{channel_dir.name}")
                        channel_data = self._ultra_fast_json_load(videos_file, cache_key)

                        if channel_data:
                            # Convert to DataFrame with optimizations
                            df = pd.DataFrame(channel_data)

                            if not df.empty:
                                # Optimize in one pass
                                df = self._optimize_video_dataframe(df)
                                df = clean_dataframe_for_caching(df)
                                videos_data[channel_dir.name] = df
                                self._log(f"Ultra-loaded {len(df)} videos from {channel_dir.name}")
                        break

        except Exception as e:
            self._log(f"Error in ultra video loading: {e!s}", "error")

        return videos_data

    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False, hash_funcs=SAFE_HASH_FUNCS)
    def get_news_data_ultra(self) -> dict[str, pd.DataFrame]:
        """Ultra-optimized news data loading."""
        self._log("Loading news data (ultra-optimized)")

        news_data = {}

        # Define news sources with multiple file options
        news_sources = [
            ('hackernews', self.cached_paths['hackernews_dir'], ["stories.json", "hackernews.json", "hackernews_simple.json"]),
            ('futuretools', self.cached_paths['futuretools_dir'], ["news.json", "futuretoolsnews.json"]),
            ('medium', self.cached_paths['medium_dir'], ["articles.json"]),
        ]

        for source_name, source_dir, file_names in news_sources:
            if not source_dir or not source_dir.exists():
                continue

            for filename in file_names:
                file_path = source_dir / filename
                if file_path.exists():
                    cache_key = self._get_cache_key(str(file_path), f"news_{source_name}")
                    data = self._ultra_fast_json_load(file_path, cache_key)

                    if data:
                        df = pd.DataFrame(data)
                        if not df.empty:
                            df = self._optimize_dataframe_dtypes(df, {
                                'published_date': 'datetime'
                            })
                            df = clean_dataframe_for_caching(df)
                            news_data[source_name] = df
                            self._log(f"Ultra-loaded {len(df)} {source_name} articles")
                    break

        return news_data

    @st.cache_data(ttl=3600, max_entries=5, show_spinner=False, hash_funcs=SAFE_HASH_FUNCS)
    def get_courses_data_ultra(self) -> dict[str, pd.DataFrame]:
        """Ultra-optimized courses data loading."""
        self._log("Loading courses data (ultra-optimized)")

        courses_data = {}

        # Define course sources
        course_sources = [
            ('coursera', self.cached_paths['coursera_dir'] / "coursera_courses.json"),
            ('udemy', self.cached_paths['udemy_dir'] / "udemy_courses.json"),
            ('deeplearningai', self.cached_paths['deeplearningai_dir'] / "deeplearningai_courses.json")
        ]

        for source_name, file_path in course_sources:
            if file_path.exists():
                cache_key = self._get_cache_key(str(file_path), f"courses_{source_name}")
                data = self._ultra_fast_json_load(file_path, cache_key)

                if data:
                    df = pd.DataFrame(data)
                    if not df.empty:
                        df = clean_dataframe_for_caching(df)
                        courses_data[source_name] = df
                        self._log(f"Ultra-loaded {len(df)} {source_name} courses")

        return courses_data

    def _optimize_dataframe_dtypes(self, df: pd.DataFrame, type_mapping: dict[str, str]) -> pd.DataFrame:
        """Optimize DataFrame data types for memory efficiency."""
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
        """Specialized optimization for video DataFrames."""
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

    @st.cache_data(ttl=600, show_spinner=False, hash_funcs=SAFE_HASH_FUNCS)  # 10 minute cache for summary
    def get_data_summary_ultra(self) -> dict[str, dict]:
        """Ultra-fast data summary generation using cached data."""
        self._log("Generating ultra-fast data summary")

        summary = {}

        try:
            # Use cached data loading methods
            games_data = self.get_games_data_ultra()
            courses_data = self.get_courses_data_ultra()
            news_data = self.get_news_data_ultra()
            videos_data = self.get_videos_data_ultra()

            # Games summary
            deals_df, bundles_df, giveaways_df, itchio_df = games_data
            summary["games"] = {
                "deals": len(deals_df),
                "bundles": len(bundles_df),
                "giveaways": len(giveaways_df),
                "itchio_trending": len(itchio_df),
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
                "cache_entries": len(self.memory_cache),
                "last_updated": datetime.now().isoformat(),
                "data_sources_available": len([name for name, meta in self.file_metadata.items() if meta.get('exists', False)])
            }

            return summary

        except Exception as e:
            self._log(f"Error generating ultra summary: {e!s}", "error")
            return self._get_fallback_summary()

    def _get_fallback_summary(self) -> dict[str, dict]:
        """Fallback summary when errors occur."""
        return {
            "games": {"deals": 0, "bundles": 0, "giveaways": 0, "itchio_trending": 0, "latest_deal": None, "latest_bundle": None},
            "courses": {"total": 0, "platforms": [], "by_platform": {}},
            "news": {"total": 0, "sources": [], "by_source": {}},
            "videos": {"total": 0, "channels": 0, "by_channel": {}},
            "performance": {"cache_entries": 0, "last_updated": datetime.now().isoformat(), "data_sources_available": 0}
        }

    def clear_cache(self):
        """Clear all caches for memory optimization."""
        if hasattr(self, 'memory_cache'):
            self.memory_cache.clear()
        st.cache_data.clear()
        gc.collect()
        self._log("All caches cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "memory_cache_size": len(self.memory_cache) if hasattr(self, 'memory_cache') else 0,
            "file_metadata_entries": len(self.file_metadata),
            "streamlit_cache_stats": "Available" if hasattr(st.cache_data, 'clear') else "Not available"
        }

    def get_data_summary(self) -> dict[str, dict]:
        """Compatibility method that calls get_data_summary_ultra."""
        return self.get_data_summary_ultra()

    # Compatibility methods for existing code
    def get_games_data(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compatibility method that calls get_games_data_ultra including Itch.io trending."""
        self._log("🔍 DEBUG: get_games_data wrapper called!")
        result = self.get_games_data_ultra()
        self._log(f"🔍 DEBUG: get_games_data wrapper got result type: {type(result)}")
        if isinstance(result, tuple):
            self._log(f"🔍 DEBUG: get_games_data wrapper tuple lengths: {[len(df) if hasattr(df, '__len__') else 'no len' for df in result]}")
        return result

    def get_videos_data(self) -> dict[str, pd.DataFrame]:
        """Compatibility method that calls get_videos_data_ultra."""
        return self.get_videos_data_ultra()

    def get_news_data(self) -> dict[str, pd.DataFrame]:
        """Compatibility method that calls get_news_data_ultra."""
        return self.get_news_data_ultra()

    def get_courses_data(self) -> dict[str, pd.DataFrame]:
        """Compatibility method that calls get_courses_data_ultra."""
        return self.get_courses_data_ultra()

    def get_arxiv_data(self) -> pd.DataFrame:
        """Get ArXiv papers data."""
        arxiv_dir = self.cached_paths.get('arxiv_dir')
        if not arxiv_dir or not arxiv_dir.exists():
            return pd.DataFrame()

        arxiv_file = arxiv_dir / "processed" / "json" / "arxiv_papers.json"
        if arxiv_file.exists():
            cache_key = self._get_cache_key(str(arxiv_file), "arxiv")
            data = self._ultra_fast_json_load(arxiv_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()

        return pd.DataFrame()

    def get_enhanced_arxiv_data(self) -> dict[str, Any]:
        """Get enhanced ArXiv papers data with intelligence features."""
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
            self._log(f"Error loading enhanced ArXiv data: {e!s}", "error")
            return {"papers": [], "metadata": {}, "error": str(e)}

    def get_events_data(self) -> pd.DataFrame:
        """Get events data."""
        events_dir = self.cached_paths.get('events_dir')
        if not events_dir or not events_dir.exists():
            return pd.DataFrame()

        events_file = events_dir / "valencia_events.json"
        if events_file.exists():
            cache_key = self._get_cache_key(str(events_file), "events")
            data = self._ultra_fast_json_load(events_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()

        return pd.DataFrame()



    def get_tech_jobs_data(self) -> pd.DataFrame:
        """Get tech jobs data."""
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
        """Get dev community data."""
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
        """Get Product Hunt data."""
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
        """Get GitHub trends data."""
        gh_dir = self.cached_paths.get('github_trends_dir')
        if not gh_dir or not gh_dir.exists():
            return pd.DataFrame()

        gh_file = gh_dir / "github_trending_latest.json"
        if gh_file.exists():
            cache_key = self._get_cache_key(str(gh_file), "github_trends")
            data = self._ultra_fast_json_load(gh_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()

        return pd.DataFrame()

    def get_new_game_releases_data(self) -> pd.DataFrame:
        """Loads new game releases data from the JSON file.
        Uses ultra_fast_json_load for optimized loading and caching.
        """
        self._log("Loading new game releases data")
        games_dir = self.cached_paths.get('games_dir')
        if not games_dir or not games_dir.exists():
            self._log("Games directory not found in cached_paths or does not exist.", "warning")
            return pd.DataFrame()

        file_path = games_dir / "new_releases.json"

        if not file_path.exists():
            self._log(f"New releases file not found at {file_path}. Returning empty DataFrame.", "warning")
            return pd.DataFrame()

        cache_key = self._get_cache_key(str(file_path), "new_game_releases")
        data = self._ultra_fast_json_load(file_path, cache_key)

        if not data:
            self._log(f"No data loaded from {file_path} for new game releases.", "info")
            return pd.DataFrame()

        try:
            df = pd.DataFrame(data)
            if not df.empty:
                # Basic type optimization, can be expanded if needed
                df = self._optimize_dataframe_dtypes(df, {
                    'released': 'datetime', # Assuming 'released' is a date string
                    'metacritic': 'float'
                })
                df = clean_dataframe_for_caching(df) # Ensure cache compatibility
            self._log(f"Successfully loaded and processed new game releases data. Shape: {df.shape}", "info")
            return df
        except Exception as e:
            self._log(f"Error converting new game releases data to DataFrame: {e}", "error")
            return pd.DataFrame()

    @st.cache_data(ttl=1800, max_entries=5, show_spinner=False) # Cache for 30 mins
    def get_google_cloud_blog_data(self) -> list[dict[str, Any]]:
        """Reads Google Cloud Blog data from data/news/google_cloud_blog.json.
        Handles FileNotFoundError and json.JSONDecodeError.
        Returns a list of blog post dictionaries.
        """
        self._log("Loading Google Cloud Blog data")

        # Construct the path using _self.data_dir for consistency
        gcb_file_path = self.data_dir / "news" / "google_cloud_blog.json"

        if not gcb_file_path.exists():
            self._log(f"Google Cloud Blog data file not found: {gcb_file_path}", "error")
            return []

        cache_key = self._get_cache_key(str(gcb_file_path), "google_cloud_blog")

        # Check memory cache first (using the class's caching mechanism)
        if cache_key in self.memory_cache:
            self._log(f"Returning cached Google Cloud Blog data for key: {cache_key}", "debug")
            return self.memory_cache[cache_key]

        try:
            with open(gcb_file_path, encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                self._log(f"Google Cloud Blog data is not a list: {type(data)}", "warning")
                # Attempt to wrap if it's a single dictionary, otherwise return empty
                if isinstance(data, dict):
                    data = [data]
                else:
                    return []

            # Store in memory cache
            if len(self.memory_cache) < 50: # Adhering to existing cache size limit
                self.memory_cache[cache_key] = data

            self._log(f"Successfully loaded {len(data)} entries from {gcb_file_path}")
            return data

        except FileNotFoundError: # This case is technically covered by the gcb_file_path.exists() check
            self._log(f"Google Cloud Blog data file not found during read: {gcb_file_path}", "error")
            return []
        except json.JSONDecodeError as e:
            self._log(f"Error decoding JSON from {gcb_file_path}: {e}", "error")
            return []
        except Exception as e:
            self._log(f"An unexpected error occurred while reading {gcb_file_path}: {e}", "error")
            return []

    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False)
    def get_aws_training_data(self) -> list[dict[str, Any]]:
        """Reads AWS Training data from data/courses/aws_training_updates.json.
        Handles FileNotFoundError and json.JSONDecodeError.
        Returns a list of AWS training post dictionaries.
        """
        self._log("Loading AWS Training data")
        file_path = self.data_dir / "courses" / "aws_training_updates.json"
        cache_key_op_name = "aws_training_data"

        if not file_path.exists():
            self._log(f"AWS Training data file not found: {file_path}", "error")
            return []

        cache_key = self._get_cache_key(str(file_path), cache_key_op_name)
        if cache_key in self.memory_cache:
            self._log(f"Returning cached AWS Training data for key: {cache_key}", "debug")
            return self.memory_cache[cache_key]

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                self._log(f"AWS Training data is not a list: {type(data)}", "warning")
                if isinstance(data, dict): # Wrap if single dict
                    data = [data]
                else:
                    return [] # Invalid format

            if len(self.memory_cache) < 50: # Adhere to L1 cache size
                self.memory_cache[cache_key] = data

            self._log(f"Successfully loaded {len(data)} entries from {file_path}")
            return data

        except json.JSONDecodeError as e:
            self._log(f"Error decoding JSON from {file_path}: {e}", "error")
            return []
        except Exception as e: # Catch any other reading errors
            self._log(f"An unexpected error occurred while reading {file_path}: {e}", "error")
            return []

    @st.cache_data(ttl=1800, max_entries=10, show_spinner=False)
    def get_azure_training_data(self) -> list[dict[str, Any]]:
        """Reads Azure Training data from data/courses/azure_training_updates.json.
        Handles FileNotFoundError and json.JSONDecodeError.
        Returns a list of Azure training post dictionaries.
        """
        self._log("Loading Azure Training data")
        file_path = self.data_dir / "courses" / "azure_training_updates.json"
        cache_key_op_name = "azure_training_data"

        if not file_path.exists():
            self._log(f"Azure Training data file not found: {file_path}", "error")
            return []

        cache_key = self._get_cache_key(str(file_path), cache_key_op_name)
        if cache_key in self.memory_cache:
            self._log(f"Returning cached Azure Training data for key: {cache_key}", "debug")
            return self.memory_cache[cache_key]

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                self._log(f"Azure Training data is not a list: {type(data)}", "warning")
                if isinstance(data, dict): # Wrap if single dict
                    data = [data]
                else:
                    return [] # Invalid format

            if len(self.memory_cache) < 50: # Adhere to L1 cache size
                self.memory_cache[cache_key] = data

            self._log(f"Successfully loaded {len(data)} entries from {file_path}")
            return data

        except json.JSONDecodeError as e:
            self._log(f"Error decoding JSON from {file_path}: {e}", "error")
            return []
        except Exception as e: # Catch any other reading errors
            self._log(f"An unexpected error occurred while reading {file_path}: {e}", "error")
            return []

    def get_security_vulnerabilities_data(self) -> pd.DataFrame:
        """Get security vulnerabilities data."""
        vulnerabilities_dir = self.cached_paths.get('security_vulnerabilities_dir')
        if not vulnerabilities_dir or not vulnerabilities_dir.exists():
            return pd.DataFrame()

        vulnerabilities_file = vulnerabilities_dir / "vulnerabilities_latest.json"
        if vulnerabilities_file.exists():
            cache_key = self._get_cache_key(str(vulnerabilities_file), "security")
            data = self._ultra_fast_json_load(vulnerabilities_file, cache_key)
            return pd.DataFrame(data) if data else pd.DataFrame()

        return pd.DataFrame()

    def get_tech_events_intelligence(self) -> dict[str, Any]:
        """Get technology events and conference intelligence.

        Returns:
            Technology events intelligence data.
        """
        try:
            # Load events from the ETL output
            events_file = self.data_dir / "tech_conference" / "output" / "tech_events_latest.json"

            if not events_file.exists():
                self._log("Tech events file not found, generating demo data", "warning")
                return self._generate_demo_events_data()

            with open(events_file, encoding="utf-8") as f:
                events_data = json.load(f)

            # Process events data
            processed_events = []
            upcoming_events = []
            high_quality_events = []
            free_events = []

            for event in events_data:
                processed_event = {
                    'name': event.get('name'),
                    'description': event.get('description', '')[:200] + '...' if len(event.get('description', '')) > 200 else event.get('description', ''),
                    'start_date': event.get('start_date'),
                    'event_type': event.get('event_type'),
                    'format': event.get('format'),
                    'is_virtual': event.get('is_virtual', False),
                    'location': event.get('location') or (event.get('venue', {}).get('city') if event.get('venue') else 'TBD'),
                    'organizer': event.get('organizer'),
                    'estimated_cost': event.get('estimated_cost', 0),
                    'is_free': event.get('is_free', False),
                    'topics': event.get('topics', []),
                    'categories': event.get('categories', []),
                    'quality_score': event.get('quality_score', 0),
                    'relevance_score': event.get('relevance_score', 0),
                    'networking_score': event.get('networking_score', 0),
                    'roi_score': event.get('roi_score', 0),
                    'registration_url': event.get('registration_url'),
                    'website_url': event.get('website_url'),
                    'tags': event.get('tags', []),
                    'source_name': event.get('source_name')
                }

                processed_events.append(processed_event)

                # Categorize events
                try:
                    event_date = datetime.fromisoformat(event.get('start_date', '').replace('Z', '+00:00'))
                    if event_date > datetime.utcnow():
                        upcoming_events.append(processed_event)
                except:
                    pass

                if event.get('quality_score', 0) >= 75:
                    high_quality_events.append(processed_event)

                if event.get('is_free', False):
                    free_events.append(processed_event)

            # Calculate statistics
            total_events = len(processed_events)
            upcoming_count = len(upcoming_events)
            high_quality_count = len(high_quality_events)
            free_events_count = len(free_events)

            # Calculate average scores
            avg_quality = sum(e.get('quality_score', 0) for e in processed_events) / max(total_events, 1)
            avg_relevance = sum(e.get('relevance_score', 0) for e in processed_events) / max(total_events, 1)
            avg_networking = sum(e.get('networking_score', 0) for e in processed_events) / max(total_events, 1)
            avg_roi = sum(e.get('roi_score', 0) for e in processed_events) / max(total_events, 1)

            # Event type distribution
            event_types = {}
            for event in processed_events:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1

            # Topic distribution
            all_topics = []
            for event in processed_events:
                all_topics.extend(event.get('topics', []))

            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Format categories
            format_distribution = {}
            for event in processed_events:
                format_type = event.get('format', 'unknown')
                format_distribution[format_type] = format_distribution.get(format_type, 0) + 1

            return {
                'events': processed_events,
                'upcoming_events': upcoming_events[:20],  # Top 20 upcoming
                'high_quality_events': high_quality_events[:10],  # Top 10 high quality
                'free_events': free_events[:15],  # Top 15 free events
                'statistics': {
                    'total_events': total_events,
                    'upcoming_count': upcoming_count,
                    'high_quality_count': high_quality_count,
                    'free_events_count': free_events_count,
                    'avg_quality_score': round(avg_quality, 1),
                    'avg_relevance_score': round(avg_relevance, 1),
                    'avg_networking_score': round(avg_networking, 1),
                    'avg_roi_score': round(avg_roi, 1)
                },
                'distributions': {
                    'event_types': event_types,
                    'formats': format_distribution,
                    'top_topics': top_topics
                },
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log(f"Tech events intelligence error: {e}", "error")
            return {'error': str(e)}

    def _generate_demo_events_data(self) -> dict[str, Any]:
        """Generate demo events data for when ETL hasn't run yet.

        Returns:
            Demo events intelligence data.
        """
        demo_events = [
            {
                'name': 'AI & Machine Learning Conference 2024',
                'description': 'Join industry leaders for the latest in AI and ML innovations, featuring keynotes, workshops, and networking opportunities.',
                'start_date': (datetime.utcnow() + timedelta(days=30)).isoformat(),
                'event_type': 'conference',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'San Francisco, CA',
                'organizer': 'AI Society',
                'estimated_cost': 299.0,
                'is_free': False,
                'topics': ['artificial intelligence', 'machine learning', 'deep learning'],
                'categories': ['AI/ML'],
                'quality_score': 85.0,
                'relevance_score': 90.0,
                'networking_score': 80.0,
                'roi_score': 75.0,
                'registration_url': 'https://example.com/ai-conference-2024',
                'website_url': 'https://example.com/ai-conference-2024',
                'tags': ['conference', 'ai', 'premium'],
                'source_name': 'eventbrite'
            },
            {
                'name': 'Python Data Science Workshop',
                'description': 'Hands-on workshop for data science with Python, covering pandas, scikit-learn, and machine learning fundamentals.',
                'start_date': (datetime.utcnow() + timedelta(days=21)).isoformat(),
                'event_type': 'workshop',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'Austin, TX',
                'organizer': 'Austin Python Meetup',
                'estimated_cost': 50.0,
                'is_free': False,
                'topics': ['python', 'data science', 'workshop'],
                'categories': ['Data Science'],
                'quality_score': 70.0,
                'relevance_score': 85.0,
                'networking_score': 65.0,
                'roi_score': 85.0,
                'registration_url': 'https://example.com/python-workshop',
                'website_url': 'https://example.com/python-workshop',
                'tags': ['workshop', 'python', 'affordable'],
                'source_name': 'meetup'
            },
            {
                'name': 'React Developer Meetup',
                'description': 'Monthly meetup for React developers to share knowledge, network, and learn about the latest React ecosystem updates.',
                'start_date': (datetime.utcnow() + timedelta(days=14)).isoformat(),
                'event_type': 'meetup',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'New York, NY',
                'organizer': 'React NYC',
                'estimated_cost': 0.0,
                'is_free': True,
                'topics': ['react', 'javascript', 'frontend'],
                'categories': ['Web Development'],
                'quality_score': 65.0,
                'relevance_score': 80.0,
                'networking_score': 75.0,
                'roi_score': 90.0,
                'registration_url': 'https://example.com/react-meetup',
                'website_url': 'https://example.com/react-meetup',
                'tags': ['meetup', 'react', 'free'],
                'source_name': 'meetup'
            },
            {
                'name': 'Blockchain & Web3 Summit',
                'description': 'Explore the future of decentralized web, featuring talks on DeFi, NFTs, and blockchain technology.',
                'start_date': (datetime.utcnow() + timedelta(days=60)).isoformat(),
                'event_type': 'summit',
                'format': 'virtual',
                'is_virtual': True,
                'location': 'Online',
                'organizer': 'Web3 Community',
                'estimated_cost': 150.0,
                'is_free': False,
                'topics': ['blockchain', 'web3', 'DeFi'],
                'categories': ['Blockchain/Web3'],
                'quality_score': 78.0,
                'relevance_score': 75.0,
                'networking_score': 60.0,
                'roi_score': 70.0,
                'registration_url': 'https://example.com/web3-summit',
                'website_url': 'https://example.com/web3-summit',
                'tags': ['summit', 'blockchain', 'virtual'],
                'source_name': 'dev_events'
            }
        ]

        return {
            'events': demo_events,
            'upcoming_events': demo_events,
            'high_quality_events': [e for e in demo_events if e['quality_score'] >= 75],
            'free_events': [e for e in demo_events if e['is_free']],
            'statistics': {
                'total_events': len(demo_events),
                'upcoming_count': len(demo_events),
                'high_quality_count': len([e for e in demo_events if e['quality_score'] >= 75]),
                'free_events_count': len([e for e in demo_events if e['is_free']]),
                'avg_quality_score': 74.5,
                'avg_relevance_score': 82.5,
                'avg_networking_score': 70.0,
                'avg_roi_score': 80.0
            },
            'distributions': {
                'event_types': {'conference': 1, 'workshop': 1, 'meetup': 1, 'summit': 1},
                'formats': {'in_person': 3, 'virtual': 1},
                'top_topics': [('python', 1), ('react', 1), ('blockchain', 1), ('machine learning', 1)]
            },
            'last_updated': datetime.utcnow().isoformat()
        }

    def get_security_intelligence(self) -> dict[str, Any]:
        """Get security intelligence summary and analysis."""
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
            self._log(f"Error generating security intelligence: {e!s}", "error")
            return {
                'error': f'Error processing security data: {e!s}',
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

    def get_github_trends(self) -> list[dict[str, Any]]:
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

    def get_dev_community(self) -> list[dict[str, Any]]:
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

    async def get_technology_radar(self) -> dict[str, Any]:
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

    def _serialize_framework_battles(self, battles) -> dict[str, Any]:
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

    def _serialize_predictions(self, predictions) -> dict[str, Any]:
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

    def _generate_technology_recommendations(self, battles, predictions) -> dict[str, Any]:
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

    def _analyze_market_trends(self, battles, predictions) -> dict[str, Any]:
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

    def get_home_server_trends_data(self):
        file_path = self.cached_paths['home_server_trends_dir'] / "home_server_trends_latest.json"
        if not file_path.exists():
            self._log(f"Home server trends data file not found: {file_path}", "warning")
            return []
        try:
            cache_key = self._get_cache_key(str(file_path), "home_server_trends")
            data = self._ultra_fast_json_load(file_path, cache_key)
            # Optionally convert to DataFrame if other tabs expect it, otherwise list of dicts is fine
            # For example: return pd.DataFrame(data) if data else pd.DataFrame()
            return data # Returning list of dicts for flexibility
        except Exception as e:
            self._log(f"Error loading home server trends data from {file_path}: {e}", "error")
            return []

    @st.cache_data(ttl=1800, max_entries=5, show_spinner=False)
    def get_allkeyshop_data(self) -> list[dict[str, Any]]:
        """Get AllKeyShop game deals data from the ETL."""
        self._log("Loading AllKeyShop games data")

        try:
            allkeyshop_dir = self.cached_paths['allkeyshop_games_dir']

            # Try to load latest data file first
            latest_file = allkeyshop_dir / "latest_allkeyshop_games.json"

            if latest_file.exists():
                cache_key = self._get_cache_key(str(latest_file), "allkeyshop_latest")
                data = self._ultra_fast_json_load(latest_file, cache_key)
                self._log(f"Loaded {len(data)} AllKeyShop games from latest file")
                return data

            # Fallback to timestamped files if latest doesn't exist
            if allkeyshop_dir.exists():
                json_files = list(allkeyshop_dir.glob("allkeyshop_games_*.json"))
                if json_files:
                    # Get the most recent file
                    latest_timestamped = max(json_files, key=lambda x: x.stat().st_mtime)
                    cache_key = self._get_cache_key(str(latest_timestamped), "allkeyshop_timestamped")
                    data = self._ultra_fast_json_load(latest_timestamped, cache_key)
                    self._log(f"Loaded {len(data)} AllKeyShop games from timestamped file: {latest_timestamped.name}")
                    return data

            self._log("No AllKeyShop data files found", "warning")
            return []

        except Exception as e:
            self._log(f"Error loading AllKeyShop data: {e}", "error")
            return []

    @st.cache_data(ttl=1800, max_entries=5, show_spinner=False, hash_funcs=SAFE_HASH_FUNCS)
    def get_museum_data(self) -> pd.DataFrame:
        """Load and process virtual museum data."""
        self._log("Loading virtual museum data...")

        museums_output_dir = self.cached_paths.get('museums_output_dir')

        if not museums_output_dir:
            self._log("Museums output directory not configured.", "warning")
            return pd.DataFrame()

        if not museums_output_dir.exists():
            self._log(f"Museums output directory not found: {museums_output_dir}", "warning")
            return pd.DataFrame()

        try:
            json_files = list(museums_output_dir.glob("virtual_museums_etl_*.json"))
            if not json_files:
                self._log(f"No museum JSON files found in {museums_output_dir}", "warning")
                return pd.DataFrame()

            # Select the most recent file based on modification time
            latest_file_path = max(json_files, key=lambda p: p.stat().st_mtime)
            self._log(f"Latest museum data file: {latest_file_path}")

        except Exception as e:
            self._log(f"Error finding latest museum file in {museums_output_dir}: {e}", "error")
            return pd.DataFrame()

        cache_key = self._get_cache_key(str(latest_file_path), "museums_data")
        data = self._ultra_fast_json_load(latest_file_path, cache_key)

        if not data:
            self._log(f"No data loaded from {latest_file_path} or file is empty.", "warning")
            return pd.DataFrame()

        try:
            df = pd.DataFrame(data)
            if df.empty:
                self._log("Museum data converted to DataFrame is empty.", "info")
                return pd.DataFrame()

            # Define type mappings based on VirtualMuseumModel
            # id (uuid.UUID) becomes string, name (str), description (Optional[str])
            # website_url (Optional[HttpUrl]) becomes string, virtual_tour_url (Optional[HttpUrl]) becomes string
            # country_label (Optional[str]), city_label (Optional[str]), main_subject_label (Optional[str])
            # image_url (Optional[HttpUrl]) becomes string, wikidata_url (Optional[HttpUrl]) becomes string
            # latitude (Optional[float]), longitude (Optional[float])
            # data_source (str) = "Wikidata"
            # retrieved_at (datetime), created_at (datetime), updated_at (datetime)
            type_mapping = {
                'retrieved_at': 'datetime',
                'created_at': 'datetime',
                'updated_at': 'datetime',
                'latitude': 'float',
                'longitude': 'float'
                # Other fields are likely strings or will be handled correctly by default.
                # Pydantic HttpUrl fields become strings in JSON.
            }

            df = self._optimize_dataframe_dtypes(df, type_mapping)
            df = clean_dataframe_for_caching(df) # Apply cleaning for cache compatibility

            self._log(f"Successfully loaded and processed {len(df)} museum entries from {latest_file_path}.")
            return df

        except Exception as e:
            self._log(f"Error processing museum data from {latest_file_path} into DataFrame: {e}", "error")
            return pd.DataFrame()

    def get_health_status(self) -> dict[str, Any]:
        """Get health status and performance metrics."""
        try:
            total_files = sum(1 for meta in self.file_metadata.values() if meta.get('exists', False))
            cache_size = len(self.memory_cache)

            avg_load_time = 0
            if self._performance_stats['load_times']:
                avg_load_time = sum(self._performance_stats['load_times'].values()) / len(self._performance_stats['load_times'])

            return {
                'status': 'healthy',
                'total_data_files': total_files,
                'cache_size': cache_size,
                'cache_hit_rate': self._performance_stats['cache_hits'] / max(1, self._performance_stats['cache_hits'] + self._performance_stats['cache_misses']),
                'average_load_time_ms': round(avg_load_time * 1000, 2),
                'total_errors': self._performance_stats['errors'],
                'memory_usage_mb': sum(len(str(v)) for v in self.memory_cache.values()) / (1024 * 1024)
            }
        except Exception as e:
            self._log(f"Error getting health status: {e}", "error")
            return {'status': 'unhealthy', 'error': str(e)}

    def _track_performance(self, operation: str, duration: float, success: bool = True):
        """Track performance metrics."""
        try:
            self._performance_stats['load_times'][operation] = duration
            if success:
                self._performance_stats['cache_misses'] += 1
            else:
                self._performance_stats['errors'] += 1
        except:
            pass  # Don't let performance tracking break the app

    @st.cache_data(ttl=1800, max_entries=5, show_spinner=False)
    def get_ai_platforms_data(self) -> list[dict[str, Any]]:
        """Get AI platforms monitoring data."""
        try:
            ai_models_dir = self.data_dir / "ai_models"
            ai_models_file = ai_models_dir / "ai_models_latest.json"

            if not ai_models_file.exists():
                self._log("AI models data file not found", "warning")
                return []

            cache_key = self._get_cache_key(str(ai_models_file), "ai_platforms")
            data = self._ultra_fast_json_load(ai_models_file, cache_key)

            # Ensure data is always a list
            if isinstance(data, dict):
                data = [data]
            elif isinstance(data, int):
                self._log(f"AI platforms data is an integer ({data}), returning empty list", "warning")
                return []
            elif not isinstance(data, list):
                self._log(f"AI platforms data is unexpected type {type(data)}, converting to empty list", "warning")
                return []

            self._log(f"Successfully loaded {len(data)} AI platform entries")
            return data

        except Exception as e:
            self._log(f"Error loading AI platforms data: {e}", "error")
            return []


# Factory function for easy instantiation
def create_ultra_optimized_service(logger=None) -> UltraOptimizedDataService:
    """Create an ultra-optimized data service instance."""
    return UltraOptimizedDataService(logger)


def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame for Streamlit caching by converting complex objects to strings.
    This prevents 'unhashable type: dict' errors in Streamlit's caching system.
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original
    df_clean = df.copy()

    # Convert problematic columns to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Check if any values are dictionaries, lists, or other complex objects
            sample_value = df_clean[col].iloc[0] if len(df_clean) > 0 else None
            if isinstance(sample_value, dict | list | set):
                # Convert complex objects to JSON strings
                def format_value(x):
                    if pd.isna(x):
                        return None
                    try:
                        if isinstance(x, dict | list | set):
                            return json.dumps(x, default=str)
                        return str(x)
                    except:
                        return str(x)

                df_clean[col] = df_clean[col].apply(format_value)

    return df_clean

# Custom hash function for DataFrames that handles complex objects
def safe_dataframe_hash(df: pd.DataFrame) -> str:
    """Safely hash a DataFrame by converting complex objects to strings first."""
    try:
        if df.empty:
            return "empty_dataframe"

        # Clean the DataFrame first
        df_clean = clean_dataframe_for_caching(df)

        # Create a simple hash based on shape and column names
        basic_hash = f"{df_clean.shape}_{hash(tuple(df_clean.columns))}"

        # Add a sample of the data for uniqueness
        if len(df_clean) > 0:
            sample_data = df_clean.head(3).to_string()
            basic_hash += f"_{hash(sample_data)}"

        return basic_hash
    except Exception as e:
        # Fallback to basic information
        return f"df_shape_{df.shape}_cols_{len(df.columns)}_error_{hash(str(e))}"

# Create a common hash function dictionary
SAFE_HASH_FUNCS = {
    pd.DataFrame: safe_dataframe_hash,
    dict: lambda d: hash(json.dumps(d, sort_keys=True, default=str)),
    list: lambda l: hash(json.dumps(l, default=str)),
    set: lambda s: hash(json.dumps(sorted(s), default=str))
}
