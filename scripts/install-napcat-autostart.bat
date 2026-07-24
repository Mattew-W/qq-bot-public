@echo off
REM ==========================================================
REM NapCat auto-start installer (Task Scheduler, on logon)
REM Run on the server in your Administrator session.
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM Why scheduled task, not NSSM?
REM   NapCat is a GUI/Electron app. NSSM services run in
REM   Session 0 (no desktop). A scheduled task that runs
REM   "only when user is logged on" launches NapCat in your
REM   interactive session so the QR code window can appear.
REM ==========================================================
setlocal

set NAPCAT_DIR=C:\Users\Administrator\Desktop\NapCat.Shell
set TASKNAME=NapCatAutoStart

REM Try the main exe first; fall back to the boot launcher.
set EXE=NapCat.Shell.exe
if not exist "%NAPCAT_DIR%\%EXE%" (
    set EXE=NapCatWinBootMain.exe
)

if not exist "%NAPCAT_DIR%\%EXE%" (
    echo [ERROR] Neither NapCat.Shell.exe nor NapCatWinBootMain.exe found under:
    echo         %NAPCAT_DIR%
    echo Edit NAPCAT_DIR / EXE at the top of this script.
    pause
    exit /b 1
)

echo Installing scheduled task "%TASKNAME%"...
echo   Target : "%NAPCAT_DIR%\%EXE%"
echo   Trigger: on user logon, highest privileges

REM /sc onlogon   = run when this user logs on
REM /rl highest   = run with highest privileges (Administrator)
REM /f            = force create (overwrite if exists)
schtasks /create /tn "%TASKNAME%" /tr "\"%NAPCAT_DIR%\%EXE%\"" /sc onlogon /rl highest /f
if errorlevel 1 (
    echo [ERROR] schtasks /create failed.
    pause
    exit /b 1
)

echo.
echo Done. Scheduled task "%TASKNAME%" is registered.
echo   Trigger now   : schtasks /run /tn "%TASKNAME%"
echo   View in GUI   : taskschd.msc  (look under Task Scheduler Library)
echo   Remove later  : schtasks /delete /tn "%TASKNAME%" /f
echo.
echo Notes:
echo   * First-time setup still requires a QR-code scan from the desktop.
echo   * After login, NapCat auto-starts and connects to bot on ws://127.0.0.1:8080.
echo   * Login session must be the Administrator account (matches /rl highest).
pause
endlocal
