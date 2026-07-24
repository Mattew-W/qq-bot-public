@echo off
REM ==========================================================
REM One-click installer for QQ bot + NapCat auto-start.
REM   * bot      -> Windows service (NSSM, no console window,
REM                 survives RDP disconnect, auto-restart on crash).
REM   * NapCat   -> Scheduled task on user logon (GUI session,
REM                 QR-code scan window shows up).
REM Run scripts\setup.bat first (creates venv + installs deps).
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM ==========================================================
setlocal

pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd

echo ==========================================================
echo   QQ Bot + NapCat auto-start installer
echo   Project: %PROJECT_DIR%
echo ==========================================================
echo.

REM ---- Auto-create venv if missing (calls setup.bat) ----
if not exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    echo venv not found, running setup.bat first to create it...
    echo.
    call "%~dp0setup.bat"
    if errorlevel 1 (
        echo.
        echo [ERROR] setup.bat failed. Fix the error above and re-run install-all.bat.
        pause
        exit /b 1
    )
    echo.
    echo venv ready, continuing with service install...
    echo.
)

echo [Step 1/2] Installing QQ bot as Windows Service (NSSM)...
call "%~dp0install-service.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Bot service install failed. Fix the error and re-run.
    pause
    exit /b 1
)
echo.

echo [Step 2/2] Auto-launching NapCat on user logon (Task Scheduler)...
call "%~dp0install-napcat-autostart.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] NapCat autostart install failed.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo   All set. Recommended next steps:
echo     1. Trigger NapCat now to finish QR login:
echo          schtasks /run /tn "NapCatAutoStart"
echo     2. Open a browser to http://127.0.0.1:8080/health
echo        (should return {"status":"ok"} once bot is up)
echo     3. Daily use:
echo          scripts\monitor.bat          (live log window)
echo          scripts\manage-bot.bat       (kill/start/restart bot only)
echo          scripts\uninstall-all.bat    (remove service + task)
echo ==========================================================
endlocal
