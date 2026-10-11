@echo off
REM Launch from repo root. Opens a console running start.ps1 (API + web + AGH).
cd /d "%~dp0"
start "Agnes-Harness" /D "%~dp0" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
exit /b 0