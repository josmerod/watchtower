@echo off
echo Starting Streamlit app at %date% %time%

REM Get the absolute path to the project root
set PROJECT_ROOT=%~dp0
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

REM Change to the Streamlit app directory
cd /d "%PROJECT_ROOT%\src\web\fullstreamlit"

REM Set environment variables
set PYTHONPATH=%PYTHONPATH%;%PROJECT_ROOT%
set DATA_DIR=%PROJECT_ROOT%\data

REM Run Streamlit app on port 8501
echo Starting Streamlit app on http://localhost:8501
echo Working directory: %CD%
echo PYTHONPATH: %PYTHONPATH%
echo Data directory: %DATA_DIR%

python -m streamlit run app.py --server.port=8501 