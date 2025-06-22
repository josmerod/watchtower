#!/bin/bash

echo "Starting ETL processes at $(date)"

# Change to the project root directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to run ETL script with logging
run_etl() {
    local script=$1
    local name=$(basename "$script" .py)
    echo "Starting $name..."
    python "$script" > "logs/${name}.log" 2>&1 &
    local script_pid=$! # PID of the python script
    pids+=($script_pid) # Add script_pid to the global pids array
    echo "$name started with PID $script_pid"
    # The function can return 0 to indicate success for the && operator
    return 0
}

# Run all ETL scripts in parallel and store their PIDs
pids=()
run_etl "src/etl/games/games_get_deals.py" && pids+=($!)
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
run_etl "src/etl/goldigging/goldigging_deeplearningai_courses.py" && pids+=($!)
run_etl "src/etl/games/games_get_humblebundles.py" && pids+=($!)
run_etl "src/etl/games/games_get_itchio_trending.py" && pids+=($!)
run_etl "src/etl/news/news_get_subreddits.py" && pids+=($!)
run_etl "src/etl/news/news_get_media_rss.py" && pids+=($!)
run_etl "src/etl/anime/mal_etl.py" && pids+=($!)
run_etl "src/etl/adhd/adhd_publications_etl.py" && pids+=($!)
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
run_etl "src/etl/ecommerce/shoppy_etl.py" && pids+=($!)

# NEW MINING TOOLS
run_etl "src/miners/crypto_sentiment_miner.py"

echo "All ETL processes started in parallel"
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

# Ensure python executable is available, might need to specify python3
# Assuming run_backup.py is in the project root and executable
# Log output of the backup script as well
if python run_backup.py >> "logs/backup_process.log" 2>&1; then
    echo "Backup process completed successfully at $(date)."
else
    echo "Backup process failed. Check logs/backup_process.log for details."
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
echo "- data/deeplearningai/"
echo "- data/watchers/"
echo "- data/anime/"
echo "- data/home_server_trends/"
echo "- data/shoppy/"
