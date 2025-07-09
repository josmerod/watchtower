#!/bin/bash

echo "Starting ETL processes with UV at $(date)"

# Change to the project root directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to run ETL script with logging using UV
run_etl() {
    local script=$1
    local name=$(basename "$script" .py)
    echo "Starting $name with UV..."
    
    # Check if uv is available, fallback to python3
    if command -v uv &> /dev/null; then
        uv run python "$script" > "logs/${name}.log" 2>&1 &
    elif command -v python3 &> /dev/null; then
        echo "UV not found, using python3 for $name"
        python3 "$script" > "logs/${name}.log" 2>&1 &
    elif command -v python &> /dev/null; then
        echo "UV not found, using python for $name"
        python "$script" > "logs/${name}.log" 2>&1 &
    else
        echo "ERROR: No Python interpreter found for $name"
        return 1
    fi
    
    local script_pid=$! # PID of the command
    pids+=($script_pid) # Add script_pid to the global pids array
    echo "$name started with PID $script_pid"
    return 0
}

# Run all ETL scripts in parallel and store their PIDs using UV
pids=()
run_etl "src/etl/games/games_get_deals.py" && pids+=($!)
run_etl "src/etl/games/games_get_humblebundles.py" && pids+=($!)
run_etl "src/etl/games/games_get_itchio_trending.py" && pids+=($!)
run_etl "src/etl/games/games_get_new_releases.py" && pids+=($!)
run_etl "src/etl/games/allkeyshop_etl.py" && pids+=($!)
run_etl "src/etl/news/news_get_ycombinator.py" && pids+=($!)
run_etl "src/etl/news/news_get_futuretools.py" && pids+=($!)
run_etl "src/etl/news/news_get_genai_medium.py" && pids+=($!)
run_etl "src/etl/news/news_get_kdnuggets.py" && pids+=($!)
run_etl "src/etl/news/news_get_bensbites.py" && pids+=($!)
run_etl "src/etl/news/news_get_planesvalencia.py" && pids+=($!)
run_etl "src/etl/news/news_get_gooddevs.py" && pids+=($!)
run_etl "src/etl/news/news_get_podcasts.py" && pids+=($!)
run_etl "src/etl/goldigging/goldigging_youtube_posts.py" && pids+=($!)
run_etl "src/watchers/ms_skills_watcher.py" && pids+=($!)
run_etl "src/etl/goldigging/goldigging_coursera_courses.py" && pids+=($!)
run_etl "src/etl/news/news_get_subreddits.py" && pids+=($!)
run_etl "src/etl/news/news_get_media_rss.py" && pids+=($!)
run_etl "src/etl/anime/mal_etl.py" && pids+=($!)
run_etl "src/etl/news/news_get_newsapi.py" && pids+=($!)

# NEW MODULES - Developer Communities & Innovation Tracking
run_etl "src/etl/news/news_get_devto.py"
run_etl "src/etl/news/news_get_producthunt.py"
run_etl "src/etl/news/news_get_indiehackers.py"
run_etl "src/etl/news/news_get_lobsters.py"
run_etl "src/etl/news/news_get_gittrends.py"
run_etl "src/etl/news/news_get_techjobs.py"

# LATEST NEW MODULES - Community & Developer Intelligence
run_etl "src/etl/news/news_get_hackernews_ask.py"
run_etl "src/etl/news/news_get_discord_trending.py"
run_etl "src/etl/news/news_get_stackoverflow_trends.py"
run_etl "src/etl/news/news_get_home_server_trends.py"

# NEW ECOMMERCE TRACKERS
run_etl "src/etl/ecommerce/shoppy_etl.py"

# NEW MINING TOOLS
run_etl "src/miners/crypto_sentiment_miner.py"

# GUMROAD SCRAPER
run_etl "src/etl/goldigging/gumroad_scraper_etl.py"

echo "All ETL processes started in parallel using UV"
echo "Process PIDs: ${pids[*]}"
echo "Check logs directory for individual process logs"
echo "To monitor processes: ps -p ${pids[*]}"

# Wait for all ETL processes to complete
echo "Waiting for all ETL processes to complete..."
for pid in "${pids[@]}"; do
    wait $pid
    if [ $? -eq 0 ]; then
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
echo "- data/product_hunt/"
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
