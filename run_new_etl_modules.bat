@echo off
setlocal enabledelayedexpansion

:: Set console title and colors
title Watchtower ETL Pipeline - New Modules
color 0B

:: Display banner
echo ========================================
echo   WATCHTOWER ETL PIPELINE - NEW MODULES
echo ========================================
echo.
echo Starting enhanced ETL pipeline execution...
echo Time started: %DATE% %TIME%
echo.

:: Initialize variables
set total_modules=5
set completed_modules=0
set failed_modules=0
set start_time=%TIME%

:: Create a simple progress bar function
call :show_progress 0

echo.
echo [1/%total_modules%] 🌐 Running DEV Community ETL...
call :show_progress 1
python src/etl/news/news_get_devto.py
if %errorlevel% neq 0 (
    echo ❌ ERROR: DEV Community ETL failed with exit code %errorlevel%
    set /a failed_modules+=1
    call :log_error "DEV Community ETL"
) else (
    echo ✅ DEV Community ETL completed successfully
    set /a completed_modules+=1
)

echo.
echo [2/%total_modules%] 🚀 Running Product Hunt ETL...
call :show_progress 2
python src/etl/news/news_get_producthunt.py
if %errorlevel% neq 0 (
    echo ❌ ERROR: Product Hunt ETL failed with exit code %errorlevel%
    set /a failed_modules+=1
    call :log_error "Product Hunt ETL"
) else (
    echo ✅ Product Hunt ETL completed successfully
    set /a completed_modules+=1
)

echo.
echo [3/%total_modules%] 💡 Running Indie Hackers ETL...
call :show_progress 3
python src/etl/news/news_get_indiehackers.py
if %errorlevel% neq 0 (
    echo ❌ ERROR: Indie Hackers ETL failed with exit code %errorlevel%
    set /a failed_modules+=1
    call :log_error "Indie Hackers ETL"
) else (
    echo ✅ Indie Hackers ETL completed successfully
    set /a completed_modules+=1
)

echo.
echo [4/%total_modules%] 🦞 Running Lobsters ETL...
call :show_progress 4
python src/etl/news/news_get_lobsters.py
if %errorlevel% neq 0 (
    echo ❌ ERROR: Lobsters ETL failed with exit code %errorlevel%
    set /a failed_modules+=1
    call :log_error "Lobsters ETL"
) else (
    echo ✅ Lobsters ETL completed successfully
    set /a completed_modules+=1
)

echo.
echo [5/%total_modules%] ₿ Running Crypto Sentiment Miner...
call :show_progress 5
python src/miners/crypto_sentiment_miner.py
if %errorlevel% neq 0 (
    echo ❌ ERROR: Crypto Sentiment Miner failed with exit code %errorlevel%
    set /a failed_modules+=1
    call :log_error "Crypto Sentiment Miner"
) else (
    echo ✅ Crypto Sentiment Miner completed successfully
    set /a completed_modules+=1
)

:: Calculate execution time
set end_time=%TIME%

echo.
echo ========================================
echo           EXECUTION SUMMARY
echo ========================================
echo.
echo ✅ Modules completed successfully: %completed_modules%/%total_modules%
echo ❌ Modules failed: %failed_modules%/%total_modules%
echo.
echo 📁 Data has been saved to:
echo    ├─ data/dev_community/       (DEV Community posts)
echo    ├─ data/product_hunt/        (Product Hunt launches)  
echo    ├─ data/indie_hackers/       (Indie Hackers discussions)
echo    ├─ data/lobsters/            (Lobsters tech news)
echo    └─ data/crypto_sentiment/    (Crypto sentiment analysis)
echo.
echo ⏱️  Started:  %start_time%
echo ⏱️  Finished: %end_time%
echo.

if %failed_modules% equ 0 (
    echo 🎉 ALL ETL MODULES COMPLETED SUCCESSFULLY!
    echo The Watchtower data pipeline is up to date.
    color 0A
) else (
    echo ⚠️  PIPELINE COMPLETED WITH %failed_modules% ERRORS
    echo Check the error logs above for details.
    echo Some data sources may not be current.
    color 0E
)

echo.
echo Press any key to exit...
pause >nul
exit /b 0

:: Function to show progress bar
:show_progress
set progress=%1
set filled=
set empty=
set bar_length=20

for /l %%i in (1,1,%bar_length%) do (
    set /a "threshold=%%i*%total_modules%/%bar_length%"
    if %progress% geq !threshold! (
        set filled=!filled!█
    ) else (
        set empty=!empty!░
    )
)

echo Progress: [!filled!!empty!] %progress%/%total_modules% modules
goto :eof

:: Function to log errors
:log_error
echo [%DATE% %TIME%] ERROR: %~1 failed >> logs/etl_errors.log
goto :eof 