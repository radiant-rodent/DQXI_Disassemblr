@echo off
rem ---------------------------------------------------------------------------
rem  DQXI Explorer (Python/Tk fallback launcher).
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "APP=%~dp0DQXI_Viewer.pyw"
where pythonw >nul 2>nul
if errorlevel 1 goto python
echo Starting DQXI Explorer (Python)...
pythonw "%APP%" %*
exit /b 0

:python
echo Starting DQXI Explorer (Python, console)...
python "%APP%" %*
exit /b %errorlevel%
