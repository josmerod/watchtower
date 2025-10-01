@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
uv run python "C:\Users\josem\watchtower\src\launcher\main.py" --mode production

endlocal
