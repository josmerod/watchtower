#!/bin/bash

echo "Starting ETL processes with UV at $(date)"

# Change to the project root directory
cd "$(dirname "$0")" || exit

# Create logs directory if it doesn't exist
mkdir -p logs

# Run all ETL scripts
echo "Starting all ETL pipelines..."

# Function to run a script in the background
# Function to run a script in the background
run_etl() {
    local script=$1
    local name
    name=$(basename "$script" .py)
    echo "Starting $name with UV..."

    # Check if uv is available, fallback to python3
    if command -v uv &> /dev/null; then
        timeout 1800 uv run python "$script" > "logs/${name}.log" 2>&1 &
    elif command -v python3 &> /dev/null; then
        echo "UV not found, using python3 for $name"
        timeout 1800 python3 "$script" > "logs/${name}.log" 2>&1 &
    elif command -v python &> /dev/null; then
        echo "UV not found, using python for $name"
        timeout 1800 python "$script" > "logs/${name}.log" 2>&1 &
    else
        echo "ERROR: No Python interpreter found for $name"
        return 1
    fi

    local script_pid=$! # PID of the command
    pids+=("$script_pid") # Add script_pid to the global pids array
}

# Run all ETL scripts in parallel and store their PIDs using UV
pids=()

run_etl "src/etl/news/news_get_freecodecamp.py"
run_etl "src/etl/news/news_get_google_ai_blog.py"
run_etl "src/etl/news/news_get_lobsters.py"
run_etl "src/etl/news/news_get_arstechnica.py"
run_etl "src/etl/news/news_get_techcrunch.py"
run_etl "src/etl/news/news_get_venturebeat.py"
run_etl "src/etl/news/news_get_bensbites.py"
run_etl "src/etl/news/news_get_genai_medium.py"
run_etl "src/etl/news/news_get_gooddevs.py"
run_etl "src/etl/news/news_get_indiehackers.py"
run_etl "src/etl/news/news_get_kagi.py"
run_etl "src/etl/news/news_get_kdnuggets.py"
run_etl "src/etl/news/microsiervos_etl.py"
run_etl "src/etl/news/news_get_meneame.py"
run_etl "src/etl/news/news_get_podcasts.py"

# Hacker News & Tech Trends
run_etl "src/etl/news/news_get_ycombinator.py"
run_etl "src/etl/news/news_get_hackernews_ask.py"
run_etl "src/etl/news/news_get_gittrends.py"

# Reddit ETL
run_etl "src/etl/news/reddit_unified_etl.py"
run_etl "src/etl/giveaways/reddit_giveaways_etl.py"

# Deals ETL
# Deals ETL (Code missing)
# run_etl "src/etl/deals/run_all_deals.py"
# run_etl "src/etl/deals/slickdeals_etl.py"
# run_etl "src/etl/deals/woot_etl.py"
# run_etl "src/etl/deals/isthereanydeal_rss_etl.py"

# Goldigging ETL
run_etl "src/etl/goldigging/goldigging_coursera_courses.py"
run_etl "src/etl/goldigging/goldigging_pluralsight_courses.py"
run_etl "src/etl/goldigging/goldigging_youtube_posts.py"
run_etl "src/etl/goldigging/goldigging_scavenging_etl.py"
run_etl "src/etl/goldigging/goldigging_deeplearningai_courses.py" # Added from .bat
run_etl "src/etl/goldigging/gumroad_scraper_etl.py"

# Arxiv ETL
run_etl "src/etl/arxiv/arxiv_etl.py" # Added from .bat

# Anime ETL
run_etl "src/etl/anime/mal_etl.py"

# AI Platforms
run_etl "src/etl/ai_platforms/papers_with_code_etl.py"
run_etl "src/etl/ai_platforms/replicate_models_etl.py"
run_etl "src/etl/ai_platforms/replicate_explore_playwright_etl.py"

# Watchers
run_etl "src/watchers/ms_skills_watcher.py"

# Youtube ETL
run_etl "src/etl/youtube_shorts_ocr_etl.py" # Added from .bat

# Courses
run_etl "src/etl/courses/khan_academy_etl.py"

# Intelligence feeds
run_etl "src/etl/intelligence/sec_edgar_rss.py"
run_etl "src/etl/intelligence/who_outbreaks_rss.py"
run_etl "src/etl/intelligence/lesswrong_etl.py"

# Games ETL
run_etl "src/etl/games/games_get_deals.py"
run_etl "src/etl/games/games_get_humblebundles.py"
run_etl "src/etl/games/games_get_new_releases.py"
run_etl "src/etl/games/games_get_itchio_trending.py"
run_etl "src/etl/games/games_get_epic_free.py"
run_etl "src/etl/games/enhanced_free_games_etl.py"
run_etl "src/etl/games/games_get_gog_rss.py"
run_etl "src/etl/games/games_get_isthereanydeal_api.py"
run_etl "src/etl/games/games_get_metacritic_rss.py"
run_etl "src/etl/games/games_get_giantbomb.py"

# Entertainment ETL
run_etl "src/etl/entertainment/trakt_trending_etl.py"
run_etl "src/etl/entertainment/spotify_browse_etl.py"

# Spanish Public Aid ETL
run_etl "src/etl/spanish_public_aid/spanish_public_aid_etl.py"

# 4chan Generals ETL
run_etl "src/etl/fourchan/fourchan_generals_etl.py"

# Phase 1 Expanded ETLs - New Sources (January 2025)
run_etl "src/etl/expanded/newsapi_etl.py"
run_etl "src/etl/expanded/rapidapi_etl.py"
run_etl "src/etl/expanded/hashnode_etl.py"
run_etl "src/etl/expanded/github_analytics_etl.py"
run_etl "src/etl/expanded/package_registry_etl.py"

# Phase 2 Expanded ETLs - Strategic Sources (January 2025)
run_etl "src/etl/expanded/stackexchange_etl.py"
run_etl "src/etl/expanded/openalex_etl.py"
run_etl "src/etl/expanded/kaggle_etl.py"
run_etl "src/etl/expanded/gaming_anime_etl.py"

# Miners
run_etl "src/miners/crypto_sentiment_miner.py"

# Viajeros Piratas Scraper
run_etl "src/etl/goldigging/viajeros_piratas_etl.py"


# Open Source Projects ETL
run_etl "src/etl/opensource/opensource_projects_etl.py"

# Uneed.best ETL (Replaces Product Hunt)
run_etl "src/etl/news/news_get_uneed.py"

echo "All ETL processes started in parallel using UV"
echo "Process PIDs: ${pids[*]}"
echo "Check logs directory for individual process logs"
echo "To monitor processes: ps -p ${pids[*]}"

# Wait for all ETL processes to complete
echo "Waiting for all ETL processes to complete..."
for pid in "${pids[@]}"; do
    if wait "$pid"; then
        echo "Process $pid completed successfully"
    else
        echo "Process $pid completed with errors (check logs)"
    fi
done

echo "All ETL processes completed at $(date)"

echo "All ETL processes completed. Starting backup process..."

# Run backup process using UV or fallback
echo "Starting backup process..."
if command -v uv &> /dev/null; then
    if uv run python run_backup.py >> "logs/backup_process.log" 2>&1; then
        echo "Backup process completed successfully at $(date)."
    else
        echo "Backup process failed. Check logs/backup_process.log for details."
    fi
elif command -v python3 &> /dev/null; then
    echo "UV not found, using python3 for backup"
    if python3 run_backup.py >> "logs/backup_process.log" 2>&1; then
        echo "Backup process completed successfully at $(date)."
    else
        echo "Backup process failed. Check logs/backup_process.log for details."
    fi
elif command -v python &> /dev/null; then
    echo "UV not found, using python for backup"
    if python run_backup.py >> "logs/backup_process.log" 2>&1; then
        echo "Backup process completed successfully at $(date)."
    else
        echo "Backup process failed. Check logs/backup_process.log for details."
    fi
else
    echo "ERROR: No Python interpreter found for backup process"
fi

echo "ETL and Backup workflow finished at $(date)."

echo "Data has been saved to respective directories:"
echo "- data/dev_community/"
# echo "- data/product_hunt/"
echo "- data/uneed/"
echo "- data/indie_hackers/"
echo "- data/lobsters/"
echo "- data/crypto_sentiment/"
echo "- data/games/"
echo "- data/news/"
echo "- data/raw/newsapi/"
echo "- data/goldigging/"
echo "- data/watchers/"
echo "- data/anime/"
echo "- data/home_server_trends/"
echo "- data/shoppy/"
echo "- data/scavenging/"
echo "- data/devto/"
echo "- data/meneame/"
echo "- data/spanish_public_aid/"
echo "- data/reddit_unified/"
echo "- data/giveaways/"
echo "- data/4chan_generals/"
echo "- data/arxiv/" # Added from .bat
echo "- data/youtube_shorts_ocr/" # Added from .bat
