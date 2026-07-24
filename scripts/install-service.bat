@echo off
REM ==========================================================
REM QQ Bot Windows Service Installer (via nssm)
REM Run scripts\setup.bat first to create the venv.
REM Encoding: ASCII (no BOM) for safe execution on zh-cn Windows.
REM ==========================================================

setlocal

REM ---- Settings (edit if your paths differ) ----
set SERVICE_NAME=QQBot
set DISPLAY_NAME=QQ Bot (NoneBot2)
set DESCRIPTION=QQ Group Bot based on NoneBot2 + OneBot v11
set PROJECT_DIR=%~dp0..
set PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe
set BOT_SCRIPT=%PROJECT_DIR%\bot.py
set RUN_BOT=%~dp0run_bot.bat
set LOG_DIR=%PROJECT_DIR%\logs
set NSSM_DIR=%PROJECT_DIR%\tools\nssm
set NSSM_EXE=

REM ---- Sanity checks ----
if not exist "%PYTHON_EXE%" (
    echo [WARN] venv not found at: %PYTHON_EXE%
    echo The self-healing launcher run_bot.bat will create it on first start.
)
if not exist "%BOT_SCRIPT%" (
    echo [ERROR] bot.py not found at: %BOT_SCRIPT%
    pause
    exit /b 1
)
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM ---- Locate or download nssm ----
echo Looking for nssm.exe...
for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem -Path '%NSSM_DIR%' -Filter 'nssm.exe' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.DirectoryName -match 'win64' } | Select-Object -First 1 -ExpandProperty FullName"') do set NSSM_EXE=%%f

if "%NSSM_EXE%"=="" (
    echo nssm not found, downloading...
    if not exist "%PROJECT_DIR%\tools" mkdir "%PROJECT_DIR%\tools"
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%PROJECT_DIR%\tools\nssm.zip' -UseBasicParsing } catch { Write-Error $_; exit 1 }; Expand-Archive -Path '%PROJECT_DIR%\tools\nssm.zip' -DestinationPath '%NSSM_DIR%' -Force"
    for /f "delims=" %%f in ('powershell -NoProfile -Command "Get-ChildItem -Path '%NSSM_DIR%' -Filter 'nssm.exe' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.DirectoryName -match 'win64' } | Select-Object -First 1 -ExpandProperty FullName"') do set NSSM_EXE=%%f
)

if "%NSSM_EXE%"=="" (
    echo [ERROR] Failed to locate nssm.exe.
    echo Please download manually from https://nssm.cc and place nssm.exe under tools\nssm\
    pause
    exit /b 1
)

echo Using nssm: %NSSM_EXE%

REM ---- Remove old service if exists ----
"%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1
"%NSSM_EXE%" remove %SERVICE_NAME% confirm >nul 2>&1

REM ---- Install and configure the service ----
REM App points to the self-healing launcher (not python directly),
REM so a wiped venv is rebuilt automatically on start.
echo Installing Windows service...
"%NSSM_EXE%" install %SERVICE_NAME% cmd.exe /c "%RUN_BOT%"
"%NSSM_EXE%" set %SERVICE_NAME% DisplayName "%DISPLAY_NAME%"
"%NSSM_EXE%" set %SERVICE_NAME% Description "%DESCRIPTION%"
"%NSSM_EXE%" set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
"%NSSM_EXE%" set %SERVICE_NAME% AppStdout "%LOG_DIR%\service-stdout.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppStderr "%LOG_DIR%\service-stderr.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateBytes 10485760
"%NSSM_EXE%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM_EXE%" set %SERVICE_NAME% AppRestartDelay 5000
"%NSSM_EXE%" set %SERVICE_NAME% AppExit Default Restart
"%NSSM_EXE%" set %SERVICE_NAME% AppEnvironmentExtra "PYTHONIOENCODING=utf-8"

REM ---- Start the service ----
echo.
echo Starting service...
"%NSSM_EXE%" start %SERVICE_NAME%
timeout /t 3 >nul
"%NSSM_EXE%" status %SERVICE_NAME%

echo.
echo ============================================================
echo  Done. Service "%DISPLAY_NAME%" is installed.
echo
echo  Manage:
echo    services.msc                           (GUI, look for the name)
echo    nssm edit %SERVICE_NAME%               (advanced settings)
echo    sc query %SERVICE_NAME%                (status)
echo    tail -f logs\service-stdout.log        (logs, from Git Bash)
echo
echo  Uninstall later:
echo    nssm stop %SERVICE_NAME%
echo    nssm remove %SERVICE_NAME% confirm
echo ============================================================
echo.
pause
endlocal
