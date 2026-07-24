@echo off
REM ==========================================================
REM repair.bat - ONE-CLICK diagnose + repair for QQBot.
REM Double-click safe: always pauses at the end.
REM Encoding: ASCII (no BOM). No parentheses in echoes
REM (cmd mis-parses them even at top level).
REM ==========================================================
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "BOT_SCRIPT=%PROJECT_DIR%\bot.py"
set "ENV_FILE=%PROJECT_DIR%\.env"
set "VENV_PY=%PROJECT_DIR%\venv\Scripts\python.exe"
set "SERVICE_NAME=QQBot"

echo ==========================================================
echo   QQBot One-Click Repair
echo   Project: %PROJECT_DIR%
echo ==========================================================
echo.

echo [CHECK] bot.py ...
if not exist "%BOT_SCRIPT%" (
    echo   [FAIL] bot.py missing. Cannot continue.
    goto :finish
) else (
    echo   [OK] present
)

echo [CHECK] .env ...
if exist "%ENV_FILE%" (
    echo   [OK] present
) else (
    echo   [WARN] missing - bot may fail to call the LLM, restore from backup
)

echo [CHECK] venv ...
if exist "%VENV_PY%" (
    echo   [OK] present
) else (
    echo   [WARN] missing - will be rebuilt automatically on start, offline from desktop wheels
)

echo [CHECK] service %SERVICE_NAME% ...
sc query %SERVICE_NAME% >nul 2>&1
if errorlevel 1 (
    echo   [STATE] service NOT installed
) else (
    for /f "tokens=*" %%a in ('sc query %SERVICE_NAME% ^| findstr /i "STATE"') do echo   %%a
)

echo.
echo [REPAIR] Re-registering the service, App equals cmd slash c run_bot.bat
echo   This removes the broken service and recreates it correctly.
echo.
call "%SCRIPT_DIR%install-service.bat"

echo.
echo [VERIFY] service status:
sc query %SERVICE_NAME% | findstr /i "STATE"
echo.
echo Open this in a browser to confirm the bot is alive:
echo   http://127.0.0.1:8080/health
echo.

:finish
echo ==========================================================
echo   Done. If the bot is not alive, open scripts\monitor.bat
echo   for live logs, or check the health URL above.
echo ==========================================================
pause
endlocal
