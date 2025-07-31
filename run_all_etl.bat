@echo off
echo Starting ETL processes at %date% %time%

REM Change to the project root directory
cd /d %~dp0

REM Check if environment is set up
if not exist ".venv" (
    echo.
    echo ERROR: Virtual environment not found!
    echo Please run setup_environment.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

REM Verify UV and virtual environment are working
echo Checking environment...
uv run python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Environment is not working properly!
    echo Please run setup_environment.bat to fix the environment.
    echo.
    pause
    exit /b 1
)

set PYTHON_CMD=uv run python
echo Using UV for Python execution

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Run all ETL and watcher scripts in parallel - only files that exist
REM Games ETL
if exist "src\etl\games\allkeyshop_etl.py" start /B %PYTHON_CMD% src/etl/games/allkeyshop_etl.py

REM News ETL  
if exist "src\etl\news\news_get_ycombinator.py" start /B %PYTHON_CMD% src/etl/news/news_get_ycombinator.py
if exist "src\etl\news\news_get_futuretools.py" start /B %PYTHON_CMD% src/etl/news/news_get_futuretools.py
if exist "src\etl\news\news_get_genai_medium.py" start /B %PYTHON_CMD% src/etl/news/news_get_genai_medium.py
if exist "src\etl\news\news_get_kdnuggets.py" start /B %PYTHON_CMD% src/etl/news/news_get_kdnuggets.py
if exist "src\etl\news\news_get_bensbites.py" start /B %PYTHON_CMD% src/etl/news/news_get_bensbites.py
if exist "src\etl\news\news_get_planesvalencia.py" start /B %PYTHON_CMD% src/etl/news/news_get_planesvalencia.py
if exist "src\etl\news\valencia_events_etl.py" start /B %PYTHON_CMD% src/etl/news/valencia_events_etl.py
if exist "src\etl\news\news_get_gooddevs.py" start /B %PYTHON_CMD% src/etl/news/news_get_gooddevs.py
if exist "src\etl\news\news_get_podcasts.py" start /B %PYTHON_CMD% src/etl/news/news_get_podcasts.py
if exist "src\etl\news\news_get_newsapi.py" start /B %PYTHON_CMD% src/etl/news/news_get_newsapi.py
if exist "src\etl\news\news_get_producthunt.py" start /B %PYTHON_CMD% src/etl/news/news_get_producthunt.py
if exist "src\etl\news\news_get_indiehackers.py" start /B %PYTHON_CMD% src/etl/news/news_get_indiehackers.py
if exist "src\etl\news\news_get_gittrends.py" start /B %PYTHON_CMD% src/etl/news/news_get_gittrends.py
if exist "src\etl\github\github_trending_rss_etl.py" start /B %PYTHON_CMD% src/etl/github/github_trending_rss_etl.py
if exist "src\etl\news\news_get_hackernews_ask.py" start /B %PYTHON_CMD% src/etl/news/news_get_hackernews_ask.py
if exist "src\etl\news\news_get_stackoverflow_trends.py" start /B %PYTHON_CMD% src/etl/news/news_get_stackoverflow_trends.py
if exist "src\etl\news\news_get_media_rss.py" start /B %PYTHON_CMD% src/etl/news/news_get_media_rss.py
if exist "src\etl\news\news_get_kagi.py" start /B %PYTHON_CMD% src/etl/news/news_get_kagi.py
if exist "src\etl\news\news_get_devto.py" start /B %PYTHON_CMD% src/etl/news/news_get_devto.py

REM Deals ETL
if exist "src\etl\deals\run_all_deals.py" start /B %PYTHON_CMD% src/etl/deals/run_all_deals.py

REM Goldigging ETL
if exist "src\etl\goldigging\goldigging_coursera_courses.py" start /B %PYTHON_CMD% src/etl/goldigging/goldigging_coursera_courses.py
if exist "src\etl\goldigging\goldigging_youtube_posts.py" start /B %PYTHON_CMD% src/etl/goldigging/goldigging_youtube_posts.py
if exist "src\etl\goldigging\goldigging_scavenging_etl.py" start /B %PYTHON_CMD% src/etl/goldigging/goldigging_scavenging_etl.py
if exist "src\etl\goldigging\goldigging_deeplearningai_courses.py" start /B %PYTHON_CMD% src/etl/goldigging/goldigging_deeplearningai_courses.py
if exist "src\etl\goldigging\gumroad_scraper_etl.py" start /B %PYTHON_CMD% src/etl/goldigging/gumroad_scraper_etl.py

REM Arxiv ETL
if exist "src\etl\arxiv\arxiv_etl.py" start /B %PYTHON_CMD% src/etl/arxiv/arxiv_etl.py

REM Anime ETL
if exist "src\etl\anime\mal_etl.py" start /B %PYTHON_CMD% src/etl/anime/mal_etl.py

REM Watchers
if exist "src\watchers\ms_skills_watcher.py" start /B %PYTHON_CMD% src/watchers/ms_skills_watcher.py

REM Youtube ETL
if exist "src\etl\youtube_shorts_ocr_etl.py" start /B %PYTHON_CMD% src/etl/youtube_shorts_ocr_etl.py


echo All available ETL processes started in parallel using %PYTHON_CMD%
echo Check logs directory for individual process logs
echo.
echo ETL processes are running in background...
echo Data will be saved to respective directories:
echo - data/games/
echo - data/news/
echo - data/deals/
echo - data/goldigging/
echo - data/anime/
echo - data/watchers/
echo - data/youtube_shorts_ocr/
echo.
echo Script completed at %date% %time%
echo Note: Individual ETL processes may still be running in background
pause
