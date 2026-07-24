@echo off
REM ==========================================================
REM run_bot.bat - self-healing launcher for the QQBot service.
REM
REM NSSM runs this via:  cmd.exe /c "...\scripts\run_bot.bat"
REM
REM On every start it checks (and repairs if needed):
REM   1. venv exists, else create it
REM   2. pip present in venv, else bootstrap ensurepip
REM   3. dependencies installed, else `pip install -e .`
REM Then launches bot.py in the foreground (NSSM tracks it).
REM
REM Result: if the venv ever gets wiped (e.g. by a full folder
REM re-upload), the service rebuilds it automatically on start.
REM Encoding: ASCII (no BOM) for safe execution on zh-cn Windows.
REM ==========================================================

setlocal ENABLEDELAYEDEXPANSION

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "VENV_DIR=%PROJECT_DIR%\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

REM ---- locate offline wheels cache (server-local, NOT in project) ----
REM Priority: Public Desktop (shows on desktop + readable by the
REM           SYSTEM service account), Administrator Desktop,
REM           C:\wheels, then project wheels/ as last resort.
set "WHEELS_DIR="
if exist "%PUBLIC%\Desktop\wheels" set "WHEELS_DIR=%PUBLIC%\Desktop\wheels"
if not defined WHEELS_DIR if exist "C:\Users\Administrator\Desktop\wheels" set "WHEELS_DIR=C:\Users\Administrator\Desktop\wheels"
if not defined WHEELS_DIR if exist "C:\wheels" set "WHEELS_DIR=C:\wheels"
if not defined WHEELS_DIR if exist "%PROJECT_DIR%\wheels" set "WHEELS_DIR=%PROJECT_DIR%\wheels"
if defined WHEELS_DIR echo [run_bot] using wheels cache: %WHEELS_DIR%
if not defined WHEELS_DIR echo [run_bot] no wheels cache found, will use network

REM ---- find a base Python to (re)build the venv ----
set "BASE_PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "BASE_PY=py -3"
if "%BASE_PY%"=="" (
    for %%V in (313 312 311 310 39) do (
        if "%BASE_PY%"=="" (
            if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python%%V\python.exe" (
                set "BASE_PY=C:\Users\Administrator\AppData\Local\Programs\Python\Python%%V\python.exe"
            )
        )
    )
)

REM ---- create venv if missing or broken ----
if not exist "%VENV_PY%" (
    if "%BASE_PY%"=="" (
        echo [run_bot] ERROR: no Python found to create venv.
        exit /b 1
    )
    echo [run_bot] venv missing, creating with %BASE_PY% ...
    %BASE_PY% -m venv "%VENV_DIR%"
)

REM ---- ensure pip is present inside the venv ----
"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [run_bot] pip missing in venv, bootstrapping...
    "%VENV_PY%" -m ensurepip --upgrade
)

REM ---- install dependencies if import check fails ----
REM Prefer local wheels (offline) when available; fall back to PyPI.
"%VENV_PY%" -c "import nonebot" >nul 2>&1
if errorlevel 1 (
    echo [run_bot] dependencies missing, installing...
    if exist "%WHEELS_DIR%" (
        set "PIPARGS=--no-index --find-links %WHEELS_DIR%"
        echo [run_bot] offline mode (wheels cached at %WHEELS_DIR%)
        "%VENV_PY%" -m pip install --upgrade pip %PIPARGS% 2>nul
        REM Build isolation pulls hatchling + its deps from the cache,
        REM so we do NOT pre-install hatchling or use --no-build-isolation.
        "%VENV_PY%" -m pip install %PIPARGS% -e "%PROJECT_DIR%"
        if errorlevel 1 (
            echo [run_bot] offline install failed, falling back to network...
            "%VENV_PY%" -m pip install -e "%PROJECT_DIR%"
        )
    ) else (
        "%VENV_PY%" -m pip install --upgrade pip
        "%VENV_PY%" -m pip install -e "%PROJECT_DIR%"
    )
)

REM ---- launch bot in foreground (NSSM tracks this process) ----
cd /d "%PROJECT_DIR%"
echo [run_bot] starting bot.py ...
"%VENV_PY%" bot.py
exit /b %errorlevel%
