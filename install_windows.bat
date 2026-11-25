@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
set "RC=%errorlevel%"
echo.
pause
exit /b %RC%
