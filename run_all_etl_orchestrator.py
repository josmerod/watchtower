import os
import sys
import subprocess
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

ETL_SCRIPTS = [
    # News ETL
    "src/etl/news/news_get_freecodecamp.py",
    "src/etl/news/news_get_google_ai_blog.py",
    "src/etl/news/news_get_lobsters.py",
    "src/etl/news/news_get_arstechnica.py",
    "src/etl/news/news_get_techcrunch.py",
    "src/etl/news/news_get_venturebeat.py",
    "src/etl/news/news_get_bensbites.py",
    "src/etl/news/news_get_genai_medium.py",
    "src/etl/news/news_get_gooddevs.py",
    "src/etl/news/news_get_indiehackers.py",
    "src/etl/news/news_get_kagi.py",
    "src/etl/news/news_get_kdnuggets.py",
    "src/etl/news/microsiervos_etl.py",
    "src/etl/news/news_get_meneame.py",
    "src/etl/news/news_get_podcasts.py",
    "src/etl/news/news_get_ycombinator.py",
    "src/etl/news/news_get_hackernews_ask.py",
    "src/etl/news/news_get_gittrends.py",
    "src/etl/news/news_get_uneed.py",
    "src/etl/news/news_get_producthunt.py",  # Was orphan — not in ETL_SCRIPTS, causing stale Product Hunt data
    
    # Reddit
    "src/etl/news/reddit_unified_etl.py",
    
    # Deals
    "src/etl/deals/lifetimo_etl.py",
    
    # Goldigging
    "src/etl/goldigging/goldigging_coursera_courses.py",
    "src/etl/goldigging/goldigging_pluralsight_courses.py",
    "src/etl/goldigging/goldigging_youtube_posts.py",
    "src/etl/goldigging/goldigging_scavenging_etl.py",
    "src/etl/goldigging/goldigging_deeplearningai_courses.py",
    "src/etl/goldigging/gumroad_scraper_etl.py",
    "src/etl/goldigging/audible_releases_etl.py",
    "src/etl/goldigging/viajeros_piratas_etl.py",
    "src/etl/goldigging/humble_books_etl.py",
    
    # Arxiv
    "src/etl/arxiv/arxiv_etl.py",
    
    # Anime
    "src/etl/anime/mal_etl.py",
    "src/etl/anime/anilist_schedule_etl.py",
    
    # AI Platforms
    "src/etl/ai_platforms/papers_with_code_etl.py",
    "src/etl/ai_platforms/replicate_models_etl.py",
    "src/etl/ai_platforms/replicate_explore_playwright_etl.py",
    
    # Watchers
    "src/watchers/ms_skills_watcher.py",
    
    # Youtube
    "src/etl/youtube_shorts_ocr_etl.py",
    
    # Courses
    "src/etl/courses/udemy_spreadsheet_etl.py",
    "src/etl/courses/ms_applied_skills_etl.py",
    "src/etl/courses/aws_skill_builder_etl.py",
    "src/etl/courses/gcp_skills_boost_etl.py",
    
    # Intelligence
    "src/etl/intelligence/sec_edgar_rss.py",
    "src/etl/intelligence/who_outbreaks_rss.py",
    "src/etl/intelligence/nvd_cve_etl.py",
    "src/etl/intelligence/lesswrong_etl.py",
    
    # ADHD & Neurodivergent
    "src/etl/adhd/adhd_publications_etl.py",
    "src/etl/neurodivergent/adhd_friendly_locations_etl.py",
    
    # Games
    "src/etl/games/games_get_deals.py",
    "src/etl/games/games_get_humblebundles.py",
    "src/etl/games/games_get_itchio_trending.py",
    "src/etl/games/games_get_gog_rss.py",
    "src/etl/games/games_get_isthereanydeal_api.py",
    "src/etl/games/games_get_metacritic_rss.py",
    
    # Entertainment
    "src/etl/entertainment/trakt_trending_etl.py",
    "src/etl/entertainment/spotify_browse_etl.py",
    # cinema_ecartelera_etl.py removed — file missing, only _improved version exists
    "src/etl/entertainment/cinema_ecartelera_improved_etl.py",
    "src/etl/entertainment/meme_economics_etl.py",
    
    # Ecommerce
    "src/etl/ecommerce/shoppy_etl.py",
    
    # Spanish Public Aid
    "src/etl/spanish_public_aid/spanish_public_aid_etl.py",
    
    # 4chan
    "src/etl/fourchan/fourchan_generals_etl.py",
    
    # Expanded Phase 1
    "src/etl/expanded/newsapi_etl.py",
    "src/etl/expanded/rapidapi_etl.py",
    "src/etl/expanded/hashnode_etl.py",
    "src/etl/expanded/github_analytics_etl.py",
    "src/etl/expanded/package_registry_etl.py",
    
    # Expanded Phase 2
    "src/etl/expanded/stackexchange_etl.py",
    "src/etl/expanded/openalex_etl.py",
    "src/etl/expanded/kaggle_etl.py",
    "src/etl/expanded/gaming_anime_etl.py",
    
    # Miners
    "src/miners/crypto_sentiment_miner.py",
    
    # Open Source Projects
    "src/etl/opensource/opensource_projects_etl.py",
    
    # Knowledge Garden
    "src/etl/substack/substack_etl.py",
    
    # Benchmarks
    "src/etl/benchmarks/artificial_analysis_etl.py",
    "src/etl/benchmarks/bridgebench_etl.py",
    
    "src/etl/trendshift/trendshift_etl.py",
    "src/etl/rss_feeds/rss_feed_etl.py",
    "src/etl/museums/museum_etl.py",
]

def run_script(script_path):
    if not os.path.exists(script_path):
        print(f"[{datetime.now()}] Warning: Script {script_path} does not exist. Skipping.")
        return False, script_path, 0.0
        
    name = os.path.basename(script_path).replace('.py', '')
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")
    
    start_time = time.time()
    
    cmd = ["uv", "run", "python", script_path]
    print(f"[{datetime.now()}] Starting {script_path}")
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )
            process.wait(timeout=1800)
            
        duration = time.time() - start_time
        if process.returncode == 0:
            print(f"[{datetime.now()}] SUCCESS: {script_path} (took {duration:.1f}s)")
            return True, script_path, duration
        else:
            print(f"[{datetime.now()}] ERROR: {script_path} failed with code {process.returncode} (took {duration:.1f}s). Check {log_file}")
            return False, script_path, duration
            
    except subprocess.TimeoutExpired:
        process.kill()
        duration = time.time() - start_time
        print(f"[{datetime.now()}] TIMEOUT: {script_path} took longer than 30m.")
        return False, script_path, duration
    except Exception as e:
        print(f"[{datetime.now()}] EXCEPTION running {script_path}: {e}")
        return False, script_path, 0.0

def main():
    parser = argparse.ArgumentParser(description="Run ETL scripts using a thread pool.")
    parser.add_argument("--workers", type=int, default=4, help="Maximum number of concurrent ETL processes to run.")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)

    print(f"Starting ETL Orchestrator with {args.workers} workers at {datetime.now()}")
    print(f"Found {len(ETL_SCRIPTS)} ETL scripts to run.")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_script, script): script for script in ETL_SCRIPTS}
        
        for future in as_completed(futures):
            success, script_path, duration = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1
                
    total_duration = time.time() - start_time
    print("\n" + "="*50)
    print(f"ETL Workflow finished in {total_duration:.1f}s.")
    print(f"Successful: {success_count} | Failed: {fail_count}")
    print("="*50)
    
    backup_script = "run_backup.py"
    if os.path.exists(backup_script):
        print(f"[{datetime.now()}] Starting backup process...")
        cmd = ["uv", "run", "python", backup_script]
        with open("logs/backup_process.log", "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                print(f"[{datetime.now()}] Backup process completed successfully.")
            else:
                print(f"[{datetime.now()}] Backup process failed. Check logs/backup_process.log.")

if __name__ == "__main__":
    main()
