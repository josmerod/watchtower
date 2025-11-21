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

REM Run all ETL and watcher scripts in parallel
REM News ETL  
start /B %PYTHON_CMD% src/etl/news/news_get_ycombinator.py
start /B %PYTHON_CMD% src/etl/news/news_get_futuretools.py
start /B %PYTHON_CMD% src/etl/news/news_get_genai_medium.py
start /B %PYTHON_CMD% src/etl/news/news_get_kdnuggets.py
start /B %PYTHON_CMD% src/etl/news/news_get_bensbites.py
start /B %PYTHON_CMD% src/etl/news/news_get_planesvalencia.py
start /B %PYTHON_CMD% src/etl/news/valencia_events_etl.py
start /B %PYTHON_CMD% src/etl/news/news_get_gooddevs.py
start /B %PYTHON_CMD% src/etl/news/news_get_podcasts.py
start /B %PYTHON_CMD% src/etl/news/news_get_newsapi.py
start /B %PYTHON_CMD% src/etl/news/news_get_producthunt.py
start /B %PYTHON_CMD% src/etl/news/news_get_indiehackers.py
start /B %PYTHON_CMD% src/etl/news/news_get_gittrends.py
start /B %PYTHON_CMD% src/etl/github/github_trending_rss_etl.py
start /B %PYTHON_CMD% src/etl/news/news_get_hackernews_ask.py
start /B %PYTHON_CMD% src/etl/news/news_get_stackoverflow_trends.py
start /B %PYTHON_CMD% src/etl/news/news_get_media_rss.py
start /B %PYTHON_CMD% src/etl/news/news_get_meneame.py
start /B %PYTHON_CMD% src/etl/news/news_get_kagi.py
start /B %PYTHON_CMD% src/etl/news/news_get_devto.py
start /B %PYTHON_CMD% src/etl/news/news_get_techcrunch.py
start /B %PYTHON_CMD% src/etl/news/news_get_venturebeat.py
start /B %PYTHON_CMD% src/etl/news/news_get_freecodecamp.py
start /B %PYTHON_CMD% src/etl/news/news_get_google_ai_blog.py
start /B %PYTHON_CMD% src/etl/news/news_get_lobsters.py
start /B %PYTHON_CMD% src/etl/news/news_get_arstechnica.py

REM Reddit ETL
start /B %PYTHON_CMD% src/etl/news/reddit_unified_etl.py
start /B %PYTHON_CMD% src/etl/giveaways/reddit_giveaways_etl.py

REM Deals ETL
start /B %PYTHON_CMD% src/etl/deals/run_all_deals.py
start /B %PYTHON_CMD% src/etl/deals/slickdeals_etl.py
start /B %PYTHON_CMD% src/etl/deals/woot_etl.py
start /B %PYTHON_CMD% src/etl/deals/isthereanydeal_rss_etl.py

REM Goldigging ETL
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_coursera_courses.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_pluralsight_courses.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_youtube_posts.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_scavenging_etl.py
start /B %PYTHON_CMD% src/etl/goldigging/goldigging_deeplearningai_courses.py
start /B %PYTHON_CMD% src/etl/goldigging/gumroad_scraper_etl.py

REM Arxiv ETL
start /B %PYTHON_CMD% src/etl/arxiv/arxiv_etl.py

REM Anime ETL
start /B %PYTHON_CMD% src/etl/anime/mal_etl.py

REM AI Platforms
start /B %PYTHON_CMD% src/etl/ai_platforms/papers_with_code_etl.py

REM Watchers
start /B %PYTHON_CMD% src/watchers/ms_skills_watcher.py

REM Youtube ETL
start /B %PYTHON_CMD% src/etl/youtube_shorts_ocr_etl.py

REM Courses
start /B %PYTHON_CMD% src/etl/courses/khan_academy_etl.py
REM Intelligence feeds
start /B %PYTHON_CMD% src/etl/intelligence/sec_edgar_rss.py
start /B %PYTHON_CMD% src/etl/intelligence/who_outbreaks_rss.py

REM Games ETL
start /B %PYTHON_CMD% src/etl/games/games_get_deals.py
start /B %PYTHON_CMD% src/etl/games/games_get_humblebundles.py
start /B %PYTHON_CMD% src/etl/games/games_get_new_releases.py
start /B %PYTHON_CMD% src/etl/games/games_get_itchio_trending.py
start /B %PYTHON_CMD% src/etl/games/games_get_epic_free.py
start /B %PYTHON_CMD% src/etl/games/enhanced_free_games_etl.py
start /B %PYTHON_CMD% src/etl/games/games_get_gog_rss.py
start /B %PYTHON_CMD% src/etl/games/games_get_isthereanydeal_api.py
start /B %PYTHON_CMD% src/etl/games/games_get_metacritic_rss.py
start /B %PYTHON_CMD% src/etl/games/games_get_giantbomb.py

REM Entertainment ETL
start /B %PYTHON_CMD% src/etl/entertainment/trakt_trending_etl.py
start /B %PYTHON_CMD% src/etl/entertainment/spotify_browse_etl.py

REM AI Platforms ETL
start /B %PYTHON_CMD% src/etl/ai_platforms/replicate_models_etl.py
start /B %PYTHON_CMD% src/etl/ai_platforms/replicate_explore_playwright_etl.py

REM Spanish Public Aid ETL
start /B %PYTHON_CMD% src/etl/spanish_public_aid/spanish_public_aid_etl.py

REM 4chan Generals ETL
start /B %PYTHON_CMD% src/etl/fourchan/fourchan_generals_etl.py


echo All available ETL processes started in parallel using %PYTHON_CMD%
echo Check logs directory for individual process logs
echo.
echo ETL processes are running in background...
echo Data will be saved to respective directories:
echo - data/games/
echo - data/news/
echo - data/ai_platforms/
echo - data/courses/
echo - data/meneame/
echo - data/deals/
echo - data/goldigging/
echo - data/anime/
echo - data/watchers/
echo - data/youtube_shorts_ocr/
echo - data/spanish_public_aid/
echo - data/reddit_unified/
echo - data/giveaways/
echo - data/4chan_generals/
echo.
echo Script completed at %date% %time%
echo Note: Individual ETL processes may still be running in background
pause
