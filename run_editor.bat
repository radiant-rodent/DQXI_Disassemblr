@echo off
rem ---------------------------------------------------------------------------
rem  DQXI Level Editor - builds the Rust viewer if needed, then opens the editor.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "EXE=%~dp0viewer_rs\target\release\viewer_rs.exe"
if exist "%EXE%" goto run

echo Building the Rust editor - first run only, this takes a few minutes...
pushd "%~dp0viewer_rs"
cargo build --release
popd
if not exist "%EXE%" goto failed

:run
set "DQXI_START_SECTION=editor"
echo Starting DQXI Level Editor. Close this window to stop it.
echo.
"%EXE%" %*
exit /b %errorlevel%

:failed
echo.
echo Build failed - is the Rust toolchain installed?  https://rustup.rs
pause
exit /b 1
