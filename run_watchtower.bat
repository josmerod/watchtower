@echo off
echo Starting Watchtower Dashboard...
echo.

REM Activate virtual environment
call .venv\Scripts\Activate.ps1

REM Start Streamlit app
echo Starting Streamlit on http://localhost:8501
python -m streamlit run src/web/fullstreamlit/app.py --server.port=8501

pause 