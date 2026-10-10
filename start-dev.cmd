@echo off
REM Launch in a dedicated PowerShell window so this .cmd exits immediately
REM and never shows "Terminate batch job (Y/N)?".
cd /d "%~dp0"
start "EDA Dev" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
exit /b 0
