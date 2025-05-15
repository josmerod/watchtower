@echo off
cd /d "C:\Users\josem\watchtower"

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Change to the Streamlit app directory
cd /d "C:\Users\josem\watchtower\src\web\fullstreamlit"

REM Set environment variables
set PYTHONPATH=C:\Users\josem\watchtower
set DATA_DIR=C:\Users\josem\watchtower\data
echo Starting Streamlit app at %date% %time% from %CD%
echo Using Python: %VIRTUAL_ENV%

python -m streamlit run app.py --server.port=8501 --browser.serverAddress=localhost
