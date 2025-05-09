@echo off
echo Starting Watchtower Streamlit App with virtual environment...

:: Change to the project directory
cd /d %~dp0

:: Activate virtual environment - this sets up the environment for subsequent commands
call .venv\Scripts\activate.bat

:: Make sure streamlit is installed
python -m pip install streamlit

:: Run the app
echo Running Streamlit app...
python -m streamlit run src/web/fullstreamlit/app.py

:: Keep the window open if there's an error
if %errorlevel% neq 0 (
    echo An error occurred while running the application.
    pause
) 