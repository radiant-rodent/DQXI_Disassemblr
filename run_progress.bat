@echo off
rem Regenerate the human-facing progress pages and open the overview.
rem The generator is stdlib-only and never talks to the network.
setlocal
cd /d "%~dp0"

python tools\progress.py
if errorlevel 1 (
    echo.
    echo Progress generation failed. See the message above.
    pause
    exit /b 1
)

start "" "%~dp0progress\progress.html"
