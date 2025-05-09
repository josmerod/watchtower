@echo off
echo Starting Watchtower Streamlit App...

:: Activate virtual environment
call .venv\Scripts\activate

:: Set Python path variables
set PYTHON_PATH=.venv\Scripts\python.exe
set STREAMLIT_PATH=.venv\Scripts\streamlit.exe

:: Check if streamlit is installed
%PYTHON_PATH% -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo Streamlit not found. Installing streamlit...
    %PYTHON_PATH% -m pip install streamlit
)

:: Run the app
echo Running Streamlit app...
%PYTHON_PATH% -m streamlit run src/web/fullstreamlit/app.py

:: Keep the window open if there's an error
if %errorlevel% neq 0 (
    echo An error occurred while running the application.
    pause
) 