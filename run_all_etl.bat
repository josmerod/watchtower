@echo off
echo Starting ETL processes with UV at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Add UV to PATH for this session
set PATH=%PATH%;C:\Users\josem\AppData\Roaming\Python\Python313\Scripts

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Check if UV is available, set the Python command accordingly
where uv >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=uv run python
    echo Using UV for Python execution
) else (
    where py >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD=py
        echo UV not found, using py launcher
    ) else (
        where python >nul 2>&1
        if %errorlevel% == 0 (
            set PYTHON_CMD=python
            echo Using python
        ) else (
            echo ERROR: No Python interpreter found!
            pause
            exit /b 1
        )
    )
)

REM Run all ETL and watcher scripts in parallel
start /B %PYTHON_CMD% src/etl/games/games_get_deals.py
start /B %PYTHON_CMD% src/etl/games/games_get_humblebundles.py
start /B %PYTHON_CMD% src/etl/games/games_get_itchio_trending.py
start /B %PYTHON_CMD% src/etl/games/games_get_new_releases.py
start /B %PYTHON_CMD% src/etl/games/allkeyshop_etl.py

start /B %PYTHON_CMD% src/etl/news/news_get_ycombinator.py
start /B %PYTHON_CMD% src/etl/news/news_get_futuretools.py
start /B %PYTHON_CMD% src/etl/news/news_get_genai_medium.py
start /B %PYTHON_CMD% src/etl/news/news_get_kdnuggets.py
start /B %PYTHON_CMD% src/etl/news/news_get_bensbites.py
start /B %PYTHON_CMD% src/etl/news/news_get_planesvalencia.py
start /B %PYTHON_CMD% src/etl/news/news_get_gooddevs.py
start /B %PYTHON_CMD% src/etl/news/news_get_podcasts.py
start /B %PYTHON_CMD% src/etl/news/news_get_newsapi.py
start /B %PYTHON_CMD% src/etl/news/news_get_devto.py
start /B %PYTHON_CMD% src/etl/news/news_get_producthunt.py
start /B %PYTHON_CMD% src/etl/news/news_get_indiehackers.py
start /B %PYTHON_CMD% src/etl/news/news_get_lobsters.py
start /B %PYTHON_CMD% src/etl/news/news_get_gittrends.py
start /B %PYTHON_CMD% src/etl/news/news_get_techjobs.py
start /B %PYTHON_CMD% src/etl/news/news_get_hackernews_ask.py
start /B %PYTHON_CMD% src/etl/news/news_get_discord_trending.py
start /B %PYTHON_CMD% src/etl/news/news_get_stackoverflow_trends.py
start /B %PYTHON_CMD% src/etl/news/news_get_subreddits.py
start /B %PYTHON_CMD% src/etl/news/news_get_media_rss.py
start /B %PYTHON_CMD% src/etl/news/news_get_home_server_trends.py
start /B %PYTHON_CMD% src/etl/news/news_get_reddit_ai.py

start /B %PYTHON_CMD% src/etl/goldigging/goldigging_youtube_posts.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_coursera_courses.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_scavenging_etl.py

start /B %PYTHON_CMD% src/etl/anime/mal_etl.py

start /B %PYTHON_CMD% src/miners/crypto_sentiment_miner.py

start /B %PYTHON_CMD% src/etl/fourchan/fourchan_generals_etl.py

start /B %PYTHON_CMD% src/etl/ecommerce/shoppy_etl.py

start /B %PYTHON_CMD% src/etl/goldigging/gumroad_scraper_etl.py

start /B %PYTHON_CMD% src/etl/goldigging/viajeros_piratas_etl.py

start /B %PYTHON_CMD% src/watchers/ms_skills_watcher.py

REM Enhanced Udemy Universal Miner with new unified CLI
start /B %PYTHON_CMD% src/miners/udemy-universal/unified_cli.py run --metrics


echo All ETL processes started in parallel using %PYTHON_CMD%
echo Check logs directory for individual process logs
echo.
echo ETL processes are running in background...
echo Data will be saved to respective directories:
echo - data/games/
echo - data/news/
echo - data/goldigging/
echo - data/anime/
echo - data/crypto_sentiment/
echo - data/fourchan/
echo - data/ecommerce/
echo - data/scavenging/
echo - data/watchers/
echo.
echo Script completed at %date% %time%
echo Note: Individual ETL processes may still be running in background
pause
