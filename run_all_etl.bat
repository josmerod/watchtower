@echo off
echo Starting ETL processes at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Run all ETL and watcher scripts in parallel
start /B python3 src/etl/games/games_get_deals.py
start /B python3 src/etl/news/news_get_ycombinator.py
start /B python3 src/etl/news/news_get_futuretools.py
start /B python3 src/etl/news/news_get_genai_medium.py
start /B python3 src/etl/news/news_get_kdnuggets.py
start /B python3 src/etl/news/news_get_bensbites.py
start /B python3 src/etl/news/news_get_planesvalencia.py
start /B python3 src/etl/news/news_get_gooddevs.py
start /B python3 src/etl/news/news_get_meneame.py
start /B python3 src/etl/news/news_get_podcasts.py
start /B python3 src/etl/goldigging/goldigging_youtube_posts.py
start /B python3 src/watchers/ms_skills_watcher.py --once
start /B python3 src/etl/goldigging/goldigging_udemy_courses.py
start /B python3 src/etl/goldigging/goldigging_coursera_courses.py


echo All ETL processes started in parallel
echo Check logs for individual process status 

