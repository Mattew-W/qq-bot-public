@echo off
REM ==========================================================
REM QQ Bot Framework Setup Script
REM ==========================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

python --version

if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .

if not exist .env (
    copy /Y .env.example .env
    notepad .env
)

echo Setup complete.
