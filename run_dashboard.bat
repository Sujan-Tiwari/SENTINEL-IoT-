@echo off
title SENTINEL-IoT // SOC Dashboard Console
echo ================================================================
echo   STARTING SENTINEL-IoT AIRSPACE SOC DASHBOARD
echo ================================================================
cd /d "%~dp0"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false"
set "PYTHONPATH=%~dp0Sentinel-IoT\.venv\Lib\site-packages;%~dp0;%PYTHONPATH%"

set "PYTHON_EXE=python"
if exist "%~dp0Sentinel-IoT\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0Sentinel-IoT\.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -m streamlit run "%~dp0app.py" --server.port 8501 --server.headless false --server.showEmailPrompt false --browser.gatherUsageStats false
pause
