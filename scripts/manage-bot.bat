@echo off
REM ==========================================================
REM QQBot Manager - stop/start/restart/tail the bot ONLY.
REM NapCat is NOT touched, so QQ login is preserved across
REM bot restarts (use this whenever you upload new bot files).
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM ==========================================================
setlocal

pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd
set "LOG_DIR=%PROJECT_DIR%\logs"
set "SERVICE_NAME=QQBot"

:menu
cls
echo ===============================================
echo   QQBot Manager  (does NOT touch NapCat)
echo ===============================================
echo.
echo   [1] Stop bot        (free to upload updates)
echo   [2] Start bot
echo   [3] Restart bot     (apply code changes)
echo   [4] Status + recent log
echo   [5] Tail live log   (Ctrl+C to exit)
echo.
echo   [0] Exit
echo.
set /p "choice=Choose [0-5]: "
if "%choice%"=="1" goto do_stop
if "%choice%"=="2" goto do_start
if "%choice%"=="3" goto do_restart
if "%choice%"=="4" goto do_status
if "%choice%"=="5" goto do_tail
if "%choice%"=="0" exit /b
goto menu

:do_stop
echo.
echo Stopping %SERVICE_NAME% ...
sc stop %SERVICE_NAME% >nul 2>&1
echo Done. NapCat is NOT affected, QQ login still valid.
pause
goto menu

:do_start
echo.
echo Starting %SERVICE_NAME% ...
sc start %SERVICE_NAME%
echo Done.
pause
goto menu

:do_restart
echo.
echo Restarting %SERVICE_NAME% ...
sc stop %SERVICE_NAME% >nul 2>&1
timeout /t 5 /nobreak >nul
sc start %SERVICE_NAME%
echo Done. NapCat is NOT affected, QQ login still valid.
pause
goto menu

:do_status
echo.
echo --- sc query %SERVICE_NAME% ---
sc query %SERVICE_NAME%
echo.
echo --- last 30 lines of latest log ---
for /f "delims=" %%f in ('powershell -NoProfile -Command "try { (Get-ChildItem -LiteralPath '%LOG_DIR%\bot_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name } catch { '' }"') do set "LATEST=%%f"
if defined LATEST (
    powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG_DIR%\%LATEST%' -Tail 30 -Encoding UTF8 -ErrorAction SilentlyContinue"
) else (
    echo (no bot log files found - is bot running?)
)
echo.
pause
goto menu

:do_tail
echo.
echo Tailing latest log live (Ctrl+C to exit)...
set "LATEST="
for /f "delims=" %%f in ('powershell -NoProfile -Command "try { (Get-ChildItem -LiteralPath '%LOG_DIR%\bot_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name } catch { '' }"') do set "LATEST=%%f"
if defined LATEST (
    echo   tracking: %LATEST%
    powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG_DIR%\%LATEST%' -Tail 50 -Wait -Encoding UTF8"
) else (
    echo (no bot log files found - is bot running?)
    pause
)
goto menu
