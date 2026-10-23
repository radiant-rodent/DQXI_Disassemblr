@echo off
rem ---------------------------------------------------------------------------
rem  DQXI Explorer (Rust) - builds if needed, then starts the viewer.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "EXE=%~dp0viewer_rs\target\release\viewer_rs.exe"
if exist "%EXE%" goto run

echo Building the Rust viewer - first run only, this takes a few minutes...
pushd "%~dp0viewer_rs"
cargo build --release
popd
if not exist "%EXE%" goto failed

:run
echo Starting DQXI Explorer (Rust).  Close this window to stop it.
echo.
"%EXE%" %*
exit /b %errorlevel%

:failed
echo.
echo Build failed - is the Rust toolchain installed?  https://rustup.rs
pause
exit /b 1
