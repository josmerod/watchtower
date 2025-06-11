@echo off
echo Starting ETL processes at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Run all ETL and watcher scripts in parallel
start /B python src/etl/games/games_get_deals.py
start /B python src/etl/news/news_get_ycombinator.py
start /B python src/etl/news/news_get_futuretools.py
start /B python src/etl/news/news_get_genai_medium.py
start /B python src/etl/news/news_get_kdnuggets.py
start /B python src/etl/news/news_get_bensbites.py
start /B python src/etl/news/news_get_planesvalencia.py
start /B python src/etl/news/news_get_gooddevs.py
start /B python src/etl/news/news_get_podcasts.py
start /B python src/etl/goldigging/goldigging_youtube_posts.py
start /B python src/watchers/ms_skills_watcher.py
start /B python src/etl/goldigging/goldigging_coursera_courses.py
start /B python src/etl/games/games_get_humblebundles.py
start /B python src/etl/games/games_get_itchio_trending.py
start /B python src/etl/news/news_get_subreddits.py
start /B python src/etl/news/news_get_media_rss.py
start /B python src\etl\anime\mal_etl.py
start /B python src/etl/news/news_get_newsapi.py

REM NEW MODULES - Developer Communities & Innovation Tracking
start /B python src/etl/news/news_get_devto.py
start /B python src/etl/news/news_get_producthunt.py
start /B python src/etl/news/news_get_indiehackers.py
start /B python src/etl/news/news_get_lobsters.py
start /B python src/etl/news/news_get_gittrends.py
start /B python src/etl/news/news_get_techjobs.py

REM LATEST NEW MODULES - Community & Developer Intelligence
start /B python src/etl/news/news_get_hackernews_ask.py
start /B python src/etl/news/news_get_discord_trending.py
start /B python src/etl/news/news_get_stackoverflow_trends.py

REM NEW MINING TOOLS
start /B python src/miners/crypto_sentiment_miner.py

echo All ETL processes started in parallel
echo Check logs directory for individual process logs
echo .
echo .
