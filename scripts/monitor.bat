@echo off
REM ==========================================================
REM Launch the QQ Bot live-monitor window.
REM Mirrors the NapCat console look: a rolling log view +
REM service status indicator, with quick Stop/Restart buttons.
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM ==========================================================
setlocal
pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd
if not exist "%PROJECT_DIR%\venv\Scripts\pythonw.exe" (
    echo [ERROR] venv not found at %PROJECT_DIR%\venv
    echo Run scripts\setup.bat first.
    pause
    exit /b 1
)
start "" "%PROJECT_DIR%\venv\Scripts\pythonw.exe" "%PROJECT_DIR%\scripts\bot_monitor.pyw"
endlocal
