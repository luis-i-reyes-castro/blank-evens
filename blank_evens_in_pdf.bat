@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if "%~1"=="" (
    echo Drag one or more documents onto this file.
    echo.
    if not defined BLANK_EVENS_NO_PAUSE pause
    exit /b 1
)

set "FAIL=0"

:next
if "%~1"=="" goto finish
call :convert "%~1"
if errorlevel 1 set "FAIL=1"
shift
goto next

:convert
if exist "%~dp0.venv\Scripts\python.exe" goto use_venv
where py >nul 2>&1
if not errorlevel 1 goto use_py
python "%~dp0blank_evens.py" "%~1"
exit /b %errorlevel%

:use_venv
"%~dp0.venv\Scripts\python.exe" "%~dp0blank_evens.py" "%~1"
exit /b %errorlevel%

:use_py
py -3 "%~dp0blank_evens.py" "%~1"
exit /b %errorlevel%

:finish
echo.
if not defined BLANK_EVENS_NO_PAUSE pause
exit /b %FAIL%
