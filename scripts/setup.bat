@echo off
REM ==========================================================
REM QQ Bot Setup Script (Windows Server)
REM Run this in PowerShell or cmd on the server after copying
REM the project to a folder (e.g. C:\qq-bot).
REM Encoding: ASCII (no BOM) for safe execution on zh-cn Windows.
REM ==========================================================

REM ---- Check Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python 3.11+ first:
    echo   1) Open Edge and visit https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo   2) Run the installer, IMPORTANT: tick "Add python.exe to PATH"
    echo   3) After install, open a NEW cmd window and re-run this script
    pause
    exit /b 1
)

echo.
echo Detected Python:
python --version

REM ---- Create virtual environment ----
if not exist venv (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

REM ---- Activate venv and install dependencies ----
echo.
echo Activating venv and installing dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo If you see "Microsoft Visual C++ 14.0 is required", run:
    echo   pip install --only-binary=:all: -e .
    echo Or check the error message above.
    pause
    exit /b 1
)

REM ---- .env setup ----
if not exist .env (
    echo.
    echo [WARN] .env not found. Copying from .env.example...
    copy /Y .env.example .env
    echo.
    echo ============================================================
    echo  ACTION REQUIRED: edit .env and fill in your keys.
    echo  At minimum set LONGCAT_API_KEY.
    echo  Notepad will open. Save and close when done.
    echo ============================================================
    echo.
    notepad .env
)

echo.
echo ============================================================
echo  Setup complete.
echo
echo  Manual run:    venv\Scripts\activate ^&^& python bot.py
echo  Install svc:   scripts\install-service.bat
echo ============================================================
echo.
pause
