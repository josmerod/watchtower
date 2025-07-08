@echo off
echo Starting ETL processes with UV at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Run all ETL and watcher scripts in parallel using UV
start /B uv run python src/etl/games/games_get_deals.py
start /B uv run python src/etl/games/games_get_humblebundles.py
start /B uv run python src/etl/games/games_get_itchio_trending.py
start /B uv run python src/etl/games/games_get_new_releases.py


start /B uv run python src/etl/news/news_get_ycombinator.py
start /B uv run python src/etl/news/news_get_futuretools.py
start /B uv run python src/etl/news/news_get_genai_medium.py
start /B uv run python src/etl/news/news_get_kdnuggets.py
start /B uv run python src/etl/news/news_get_bensbites.py
start /B uv run python src/etl/news/news_get_planesvalencia.py
start /B uv run python src/etl/news/news_get_gooddevs.py
start /B uv run python src/etl/news/news_get_podcasts.py
start /B uv run python src/etl/news/news_get_newsapi.py
start /B uv run python src/etl/news/news_get_devto.py
start /B uv run python src/etl/news/news_get_producthunt.py
start /B uv run python src/etl/news/news_get_indiehackers.py
start /B uv run python src/etl/news/news_get_lobsters.py
start /B uv run python src/etl/news/news_get_gittrends.py
start /B uv run python src/etl/news/news_get_techjobs.py
start /B uv run python src/etl/news/news_get_hackernews_ask.py
start /B uv run python src/etl/news/news_get_discord_trending.py
start /B uv run python src/etl/news/news_get_stackoverflow_trends.py
start /B uv run python src/etl/news/news_get_subreddits.py
start /B uv run python src/etl/news/news_get_media_rss.py

start /B uv run python src/etl/goldigging/goldigging_youtube_posts.py
start /B uv run python src/etl/goldigging/goldigging_coursera_courses.py

start /B uv run python src/etl/anime/mal_etl.py

start /B uv run python src/miners/crypto_sentiment_miner.py

start /B uv run python src/etl/fourchan/fourchan_generals_etl.py

start /B uv run python src/watchers/ms_skills_watcher.py


echo All ETL processes started in parallel using UV
echo Check logs directory for individual process logs
echo .
echo .
