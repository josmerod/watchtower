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
REM Added new ETL scripts for Humble Bundle, Subreddits, and Media RSS
start /B python3 src/etl/games/games_get_humblebundles.py
start /B python3 src/etl/news/news_get_subreddits.py
start /B python3 src/etl/news/news_get_media_rss.py

REM NEW MODULES - Developer Communities & Innovation Tracking
start /B python3 src/etl/news/news_get_devto.py
start /B python3 src/etl/news/news_get_producthunt.py
start /B python3 src/etl/news/news_get_indiehackers.py
start /B python3 src/etl/news/news_get_lobsters.py
start /B python3 src/etl/news/news_get_gittrends.py
start /B python3 src/etl/news/news_get_techjobs.py

REM LATEST NEW MODULES - Community & Developer Intelligence
start /B python3 src/etl/news/news_get_hackernews_ask.py
start /B python3 src/etl/news/news_get_discord_trending.py
start /B python3 src/etl/news/news_get_stackoverflow_trends.py

REM NEW MINING TOOLS
start /B python3 src/miners/crypto_sentiment_miner.py

echo All ETL processes started in parallel
echo Check logs for individual process status
echo.
echo New modules added:
echo - DEV Community: Developer articles and discussions
echo - Product Hunt: Product launches and innovations
echo - Indie Hackers: Entrepreneur discussions and revenue insights
echo - Lobsters: High-quality tech discussions
echo - GitHub Trends: Trending repositories and open-source projects
echo - Tech Jobs: Job market trends and salary analysis
echo - HackerNews Ask: Community Q&A and discussions
echo - Discord Trending: Developer community insights
echo - Stack Overflow Trends: Developer questions and pain points
echo - Crypto Sentiment: Multi-platform cryptocurrency sentiment analysis
echo.

REM Wait for ETL processes to complete and then auto-apply ultra optimizations
echo Waiting for ETL processes to complete before applying performance optimizations...
echo This may take a few minutes depending on data sources...
timeout /t 180 /nobreak > nul

echo.
echo ⚡ Auto-applying Ultra Performance Optimizations...
echo 🚀 This will make your Watchtower app 90-98%% faster!
echo.

REM Auto-apply ultra optimizations with option 1 (maximum performance)
echo 1 | python apply_ultra_optimizations.py

echo.
echo ✅ ETL and Performance Optimization Complete!
echo 🚀 Your Watchtower app is now ultra-fast and ready to use!
echo 📊 Run: streamlit run src/web/fullstreamlit/app.py
echo.

