@echo off
rem ---------------------------------------------------------------------------
rem  DQXI mod export - turns the mod\ workspace into something a 3DS/2DS runs.
rem
rem  luma   SD-card folder for Luma3DS game patching (recommended on hardware)
rem  3ds    complete rebuilt 4 GiB .3ds cartridge image
rem  cia    installable CIA for a CFW console (FBI)
rem  all    all three targets
rem  check  validate out\3ds\romfs.bin only - fast, no 4 GiB image
rem ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "TARGET=%~1"

:ask
if not "%TARGET%"=="" goto have
echo.
echo What do you want to export?
echo.
echo   [1] luma   SD-card folder for Luma3DS game patching   (recommended)
echo   [2] 3ds    complete rebuilt .3ds cartridge image
echo   [3] all    all three targets
echo   [4] check  validate the patched RomFS only (fast)
echo   [5] cia    installable CIA (needs a CFW console + FBI)
echo.
set /p "CHOICE=Choice [1]: "
if "%CHOICE%"=="" set "CHOICE=1"
if "%CHOICE%"=="1" set "TARGET=luma"
if "%CHOICE%"=="2" set "TARGET=3ds"
if "%CHOICE%"=="3" set "TARGET=all"
if "%CHOICE%"=="4" set "TARGET=check"
if "%CHOICE%"=="5" set "TARGET=cia"
if "%TARGET%"=="" goto ask

:have
echo.
echo === mod workspace ==========================================================
if exist "mod\mod.json" (
    findstr /c:"\"name\"" /c:"\"version\"" /c:"\"author\"" "mod\mod.json"
) else (
    echo   mod\mod.json is missing - the export still works, metadata will be empty.
    echo   Copy mod\mod.example.json to mod\mod.json to name your mod.
)
if exist "mod\romfs" (
    for /r "mod\romfs" %%F in (*) do echo   romfs: %%~nxF  ^(%%~zF bytes^)
) else (
    echo   mod\romfs does not exist - nothing to replace.
)
if exist "mod\code\code.bin" (
    echo   code:  mod\code\code.bin
) else (
    echo   code:  unchanged ^(no mod\code\code.bin^)
)

echo.
if /i "%TARGET%"=="check" goto check
if /i "%TARGET%"=="luma"  goto luma
if /i "%TARGET%"=="3ds"   goto threeds
if /i "%TARGET%"=="all"   goto all
if /i "%TARGET%"=="cia"   goto cia
echo Unknown target "%TARGET%". Use luma, 3ds, all, check or cia.
goto end

:luma
echo === exporting the Luma3DS SD-card folder ===================================
python tools\export_mod.py --target luma --mod mod --out out
goto done

:threeds
echo === exporting the rebuilt .3ds =============================================
echo Building a 4 GiB image takes about half a minute and ~4.5 GB of disk.
python tools\export_mod.py --target 3ds --mod mod --out out
goto done

:all
echo === exporting every target =================================================
python tools\export_mod.py --target all --mod mod --out out
goto done

:cia
echo === CIA ====================================================================
echo A CIA needs the rebuilt .3ds, so this also builds the 4 GiB image first.
python tools\export_mod.py --target cia --mod mod --out out
echo.
echo Install out\cia\DQXI_modded.cia with FBI on a Luma3DS console.
goto done

:check
echo === validating the patched RomFS ===========================================
python tools\export_mod.py --target 3ds --no-rom --mod mod --out out
goto done

:done
echo.
if errorlevel 1 (
    echo Export FAILED - read the messages above.
    goto end
)
echo Done. Results are in out\ :
if /i "%TARGET%"=="check" goto done_check
echo   out\luma\   copy its contents to the SD-card root ^(merge with existing folders^)
echo   out\3ds\    DQXI_modded.3ds for a flashcart / Godmode9
echo   out\cia\    DQXI_modded.cia to install with FBI on a CFW console
goto done_report

:done_check
echo   out\3ds\romfs.bin  the patched RomFS (the 4 GiB image was skipped)

:done_report
echo   out\EXPORT_REPORT.json  every changed file, hash and check result
echo.
echo Installation steps: docs\EXPORT.md

:end
echo.
pause
endlocal
exit /b 0
