@echo off
echo Starting Streamlit app at %date% %time%

REM Set environment variables
set PYTHONPATH=%PYTHONPATH%;%~dp0

REM Run Streamlit app on port 8501
echo Starting Streamlit app on http://localhost:8501
start http://localhost:8501
python3 -m streamlit run src/web/fullstreamlit/app.py --server.port=8501 