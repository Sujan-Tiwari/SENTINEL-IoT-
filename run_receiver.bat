@echo off
title SENTINEL-IoT // ESP32 Serial Telemetry Bridge
echo ================================================================
echo   STARTING SENTINEL-IoT ESP32 TELEMETRY BRIDGE
echo ================================================================
cd /d "%~dp0"
set "PYTHONPATH=%~dp0Sentinel-IoT\.venv\Lib\site-packages;%~dp0;%PYTHONPATH%"

set "PYTHON_EXE=python"
if exist "%~dp0Sentinel-IoT\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0Sentinel-IoT\.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" "%~dp0Sentinel-IoT\device\Esp32_receiver.py" %*
pause
