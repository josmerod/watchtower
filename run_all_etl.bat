@echo off
echo Starting ETL processes at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Run all ETL scripts in parallel
start /B python src/etl/games/games_get_deals.py
start /B python src/etl/news/news_get_ycombinator.py
start /B python src/etl/news/news_get_futuretools.py
start /B python src/etl/news/news_get_genai_medium.py
start /B python src/etl/goldigging/goldigging_youtube_posts.py

echo All ETL processes started in parallel
echo Check logs for individual process status 