@echo off
REM ==========================================================
REM QQ Bot Setup - create venv + install deps.
REM Auto-detects Python: py launcher -> PATH -> common
REM install folders. Every path has pause, never flash-exits.
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM ==========================================================
setlocal EnableDelayedExpansion

pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd

echo ==========================================================
echo   QQ Bot Setup
echo   Project: %PROJECT_DIR%
echo ==========================================================
echo.

REM ---- Locate Python (py launcher, then PATH, then common dirs) ----
set "PYEXE="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py -3"
    echo [OK] Found Python via py launcher.
    goto :found_python
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    echo [OK] Found Python in PATH.
    goto :found_python
)

for %%V in (Python313 Python312 Python311 Python310) do (
    if exist "C:\Users\Administrator\AppData\Local\Programs\Python\%%V\python.exe" (
        set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\%%V\python.exe"
        echo [OK] Found Python at !PYEXE!
        goto :found_python
    )
    if exist "%LOCALAPPDATA%\Programs\Python\%%V\python.exe" (
        set "PYEXE=%LOCALAPPDATA%\Programs\Python\%%V\python.exe"
        echo [OK] Found Python at !PYEXE!
        goto :found_python
    )
)

echo.
echo [ERROR] Python not found.
echo Tried: py launcher, PATH, common install folders.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo IMPORTANT: tick "Add python.exe to PATH" during install.
echo.
pause
exit /b 1

:found_python
echo Using: %PYEXE%
%PYEXE% --version
echo.

REM ---- Create venv (skip if already exists) ----
if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    echo venv already exists, skipping creation.
) else (
    echo Creating virtual environment...
    %PYEXE% -m venv "%PROJECT_DIR%\venv"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

REM ---- Install dependencies (offline from server-local wheels cache) ----
echo.
echo Installing dependencies (this may take a few minutes)...
REM Locate the offline cache (server Desktop, NOT in the project folder):
REM Public Desktop (visible on desktop + readable by the SYSTEM
REM service account), Administrator Desktop, C:\wheels, then project.
set "WHEELS_DIR="
if exist "%PUBLIC%\Desktop\wheels" set "WHEELS_DIR=%PUBLIC%\Desktop\wheels"
if not defined WHEELS_DIR if exist "C:\Users\Administrator\Desktop\wheels" set "WHEELS_DIR=C:\Users\Administrator\Desktop\wheels"
if not defined WHEELS_DIR if exist "C:\wheels" set "WHEELS_DIR=C:\wheels"
if not defined WHEELS_DIR if exist "%PROJECT_DIR%\wheels" set "WHEELS_DIR=%PROJECT_DIR%\wheels"
if defined WHEELS_DIR echo wheels cache found: %WHEELS_DIR%
if exist "%WHEELS_DIR%" (
    echo wheels cache found, installing offline...
    "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install --upgrade pip --no-index --find-links "%WHEELS_DIR%" 2>nul
    REM Build isolation pulls hatchling + its deps from the cache.
    "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install --no-index --find-links "%WHEELS_DIR%" -e "%PROJECT_DIR%"
    if errorlevel 1 (
        echo [WARN] offline install failed, falling back to network...
        "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install --upgrade pip
        "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install -e "%PROJECT_DIR%"
    )
) else (
    echo wheels cache not found, installing from network...
    "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install --upgrade pip
    "%PROJECT_DIR%\venv\Scripts\python.exe" -m pip install -e "%PROJECT_DIR%"
)
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo If you see "Microsoft Visual C++ 14.0 is required", try:
    echo   venv\Scripts\python.exe -m pip install --only-binary=:all: -e .
    pause
    exit /b 1
)

REM ---- .env (only prompt if missing) ----
if not exist "%PROJECT_DIR%\.env" (
    if exist "%PROJECT_DIR%\.env.example" (
        echo.
        echo [WARN] .env not found, copying from .env.example...
        copy /Y "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env" >nul
    )
    echo.
    echo ============================================================
    echo  ACTION REQUIRED: edit .env and fill LONGCAT_API_KEY.
    echo  Notepad will open. Save and close when done.
    echo  (If in a no-desktop session like Workbench, press Ctrl+C
    echo   to skip and edit .env manually later.)
    echo ============================================================
    notepad "%PROJECT_DIR%\.env"
)

echo.
echo ============================================================
echo  Setup complete.
echo  Next: scripts\install-all.bat   (register as service)
echo        venv\Scripts\python.exe bot.py  (manual test run)
echo ============================================================
echo.
pause
endlocal
