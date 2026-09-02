import argparse
import os
import subprocess
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
    "src/etl/news/news_get_futuretools.py",
    "src/etl/news/news_get_genai_medium.py",
    "src/etl/news/news_get_gooddevs.py",
    "src/etl/news/news_get_selfhosted.py",
    "src/etl/news/news_get_verge_ai.py",  # The Verge AI feed — feeds Tech Radar tab
    "src/etl/news/news_get_hn_frontpage.py",  # HN front page via Algolia (spec 13) — feeds Tech Radar tab
    "src/etl/news/news_get_wired.py",  # Wired feed — feeds Tech Radar tab
    "src/etl/news/news_get_mit_techreview.py",  # MIT Tech Review feed — feeds Tech Radar tab
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
    "src/etl/news/news_get_devto.py",  # Dev.to public API — feeds Knowledge Garden "Dev.to" subtab
    "src/etl/news/news_get_stackoverflow_trends.py",  # StackExchange API — feeds Knowledge Garden "Stack Overflow" subtab
    "src/etl/news/news_get_tldr.py",  # tldr.tech newsletters (Tech/AI/Data) — feeds News tab
    "src/etl/news/news_get_infoq.py",  # InfoQ feed — feeds Tech Radar tab
    "src/etl/news/news_get_thenewstack.py",  # The New Stack feed — feeds Tech Radar tab
    "src/etl/news/news_get_changelog.py",  # changelog.com feed — feeds Tech Radar tab
    "src/etl/news/news_get_phoronix.py",  # Phoronix feed — feeds Tech Radar tab (T-070)
    "src/etl/news/news_get_unraid_forums.py",  # Unraid forums (Invision RSS) — feeds Tech Radar tab (T-070)
    "src/etl/news/news_get_sth.py",  # ServeTheHome feed — feeds Tech Radar tab (T-078)
    "src/etl/news/news_get_xataka.py",  # Xataka feed — feeds Tech Radar tab (T-078)
    "src/etl/analytics/trends_etl.py",  # Cross-source trend analysis — feeds 🔥 badges (News/ArXiv). Local files only; must run after news ETLs
    "src/etl/analytics/weekly_digest_etl.py",  # Weekly digest (T-054) — compiles trends/radar/markets/watchers into data/insights/. Local files only; feeds 📅 Digest tab
    "src/watchers/data_freshness_watcher.py",  # MUST BE LAST — flags sources that failed to refresh this run (feeds Metrics card)
    "src/etl/news/valencia_events_etl.py",  # Feeds dashboard Valencia Events tab
    "src/etl/news/news_get_spanish_tech.py",  # Xataka, Hipertextual, Genbeta
    "src/etl/news/news_get_cloud_updates.py",  # AWS, GCP, CNCF, GitHub Blog
    "src/etl/markets/coingecko_etl.py",  # Top-50 crypto — feeds Markets tab (T-043)
    "src/etl/security/security_feeds_etl.py",  # CISA KEV + security news — feeds Security tab (T-050)
    "src/etl/news/news_get_valencia_local.py",  # 20minutos CV, Metro Valencia
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
    # BLOCKED: Epic's storefront API host (store-site.ak.epicgames.com) returns NXDOMAIN
    # globally and the HTML page is bot-protected. ETL kept for when an endpoint returns.
    # "src/etl/goldigging/epic_free_games_etl.py",
    # Arxiv
    "src/etl/arxiv/arxiv_etl.py",
    "src/etl/arxiv/hf_daily_papers_etl.py",  # HF trending papers — PWC successor (old ETL deleted: API dead, 0 consumers)
    # AI Platforms
    "src/etl/ai_platforms/replicate_models_etl.py",
    "src/etl/ai_platforms/replicate_explore_playwright_etl.py",
    "src/etl/ai_platforms/ollama_library_etl.py",  # T-075: newest ollama.com/library models — Radar "🦙 Ollama"
    # Watchers
    "src/watchers/ms_skills_watcher.py",
    # Youtube
    "src/etl/youtube_shorts_ocr_etl.py",
    # Courses
    "src/etl/courses/udemy_spreadsheet_etl.py",
    "src/etl/courses/hf_learn_etl.py",  # Hugging Face Learn catalog — feeds Learning tab
    "src/etl/courses/ms_applied_skills_etl.py",
    "src/etl/courses/aws_skill_builder_etl.py",
    "src/etl/courses/gcp_skills_boost_etl.py",
    "src/etl/courses/deeplearning_ai_etl.py",  # DeepLearning.AI catalog — feeds Learning tab (T-069)
    "src/watchers/courses_watcher.py",  # Diffs course catalogs, emits new_matching_course events (T-066); best after courses ETLs
    # Intelligence
    "src/etl/intelligence/sec_edgar_rss.py",
    "src/etl/intelligence/who_outbreaks_rss.py",
    "src/etl/intelligence/nvd_cve_etl.py",
    "src/etl/intelligence/lesswrong_etl.py",
    "src/etl/intelligence/security_feeds_etl.py",  # CISA, THN, BleepingComputer, Krebs
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
    "src/etl/spanish_public_aid/bdns_convocatorias_etl.py",  # BDNS API: fechas/cuantías reales (T-076)
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
    # Miners
    "src/miners/crypto_sentiment_miner.py",
    # Open Source Projects
    "src/etl/opensource/opensource_projects_etl.py",
    "src/etl/github/stack_releases_etl.py",  # TR-F4: GitHub releases of the self-hosted stack — Radar "Mi stack" (T-051)
    "src/etl/github/github_trending_etl.py",  # T-078: github.com/trending repos — Radar "🐙 GH Trending"
    # Knowledge Garden
    "src/etl/substack/substack_etl.py",
    # Benchmarks
    "src/etl/benchmarks/artificial_analysis_etl.py",
    "src/etl/benchmarks/bridgebench_etl.py",
    "src/etl/benchmarks/llm_leaderboard_etl.py",
    "src/etl/benchmarks/livebench_etl.py",  # LiveBench leaderboard via browserless (T-069)
    "src/etl/benchmarks/openrouter_models_etl.py",  # OpenRouter new-models feed, keyless (T-071)
    "src/etl/trendshift/trendshift_etl.py",
    "src/etl/rss_feeds/rss_feed_etl.py",
    "src/etl/museums/museum_etl.py",
]


def run_script(script_path):
    if not os.path.exists(script_path):
        print(f"[{datetime.now()}] Warning: Script {script_path} does not exist. Skipping.")
        return False, script_path, 0.0

    name = os.path.basename(script_path).replace(".py", "")
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")

    start_time = time.time()

    cmd = ["uv", "run", "python", script_path]
    print(f"[{datetime.now()}] Starting {script_path}")

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
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
            success, _script_path, _duration = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1

    total_duration = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"ETL Workflow finished in {total_duration:.1f}s.")
    print(f"Successful: {success_count} | Failed: {fail_count}")
    print("=" * 50)

    # T-055: prune old timestamped JSON snapshots (keep newest 30 per prefix).
    # Runs AFTER the pool so every ETL has finished writing; *_latest.json /
    # watchers / state files are never touched by design.
    retention_script = "src/utils/snapshot_retention.py"
    if os.path.exists(retention_script):
        print(f"[{datetime.now()}] Pruning old data snapshots (keep-last 30)...")
        cmd = ["uv", "run", "python", "-m", "src.utils.snapshot_retention", "--keep-last", "30", "--apply"]
        with open("logs/snapshot_retention.log", "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            print(f"[{datetime.now()}] Snapshot retention completed successfully.")
        else:
            print(f"[{datetime.now()}] Snapshot retention failed. Check logs/snapshot_retention.log.")

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
