@echo off
REM Always start from this script's directory so AGH workspace = EDA root.
cd /d "%~dp0"
start "EDA Dev" /D "%~dp0" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
exit /b 0
