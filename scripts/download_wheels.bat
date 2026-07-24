@echo off
REM ==========================================================
REM download_wheels.bat - build a local offline wheel cache.
REM
REM IMPORTANT: run this ONCE on the SERVER (Python 3.11, Windows),
REM after the venv + deps are already installed. It caches every
REM runtime + build dependency as a .whl for this exact platform,
REM so future installs need NO network.
REM
REM The cache is written to the SERVER'S DESKTOP (Public Desktop):
REM   C:\Users\Public\Desktop\wheels
REM - It shows up on your desktop (Public Desktop is visible to all users)
REM - It is readable by the QQBot SERVICE account (SYSTEM), so the
REM   self-healing launcher can rebuild the venv offline even after a
REM   full folder re-upload wipes venv/.
REM - It lives OUTSIDE the project folder, so you never need to copy
REM   it back to your PC or re-upload it.
REM - Do NOT commit it to GitHub.
REM Encoding: ASCII (no BOM).
REM ==========================================================
setlocal

pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd

set "WHEELS_DIR=%PUBLIC%\Desktop\wheels"
if not exist "%WHEELS_DIR%" mkdir "%WHEELS_DIR%"

if not exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run scripts\setup.bat first.
    pause
    exit /b 1
)

echo ==========================================================
echo   Building offline wheel cache
echo   Target: %WHEELS_DIR%
echo   (one-time, requires network this once)
echo ==========================================================
echo.

echo [1/2] Downloading project dependencies...
"%PROJECT_DIR%\venv\Scripts\python.exe" -m pip download . -d "%WHEELS_DIR%"
if errorlevel 1 (
    echo [ERROR] failed to download dependencies.
    pause
    exit /b 1
)

echo [2/2] Downloading build backend (hatchling) for offline editable installs...
"%PROJECT_DIR%\venv\Scripts\python.exe" -m pip download hatchling -d "%WHEELS_DIR%"
if errorlevel 1 (
    echo [WARN] hatchling download failed; editable offline install may need network.
)

echo.
echo ==========================================================
echo   Done. Offline wheel cache is ready at:
echo     %WHEELS_DIR%
echo   (this is on the server's Public Desktop - visible on your
echo    desktop, and used automatically by the service for offline
echo    rebuilds. No need to copy it back to your PC.)
echo ==========================================================
echo.
pause
endlocal
