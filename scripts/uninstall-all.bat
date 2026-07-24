@echo off
REM ==========================================================
REM Remove auto-start for QQ bot + NapCat.
REM   * Bot      - uninstalls the NSSM / sc Windows service.
REM   * NapCat   - deletes the onlogon scheduled task.
REM NapCat's QQ login session is NOT touched.
REM Encoding: ASCII for safe execution on zh-cn Windows.
REM ==========================================================
setlocal

pushd "%~dp0.."
set "PROJECT_DIR=%CD%"
popd

set "SERVICE_NAME=QQBot"
set "TASKNAME=NapCatAutoStart"

echo ===============================================
echo   Removing QQ bot + NapCat auto-start
echo ===============================================
echo.

echo [1/2] Removing bot Windows service "%SERVICE_NAME%"...
set "NSSM_EXE="
for /f "delims=" %%f in ('powershell -NoProfile -Command "try { (Get-ChildItem -LiteralPath '%PROJECT_DIR%\tools\nssm' -Filter 'nssm.exe' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.DirectoryName -match 'win64' } | Select-Object -First 1).FullName } catch { '' }"') do set "NSSM_EXE=%%f"
if defined NSSM_EXE (
    "%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1
    "%NSSM_EXE%" remove %SERVICE_NAME% confirm >nul 2>&1
    echo   - nssm cleanup attempted.
) else (
    echo   - nssm.exe not found, using sc fallback...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME% >nul 2>&1
)
sc query %SERVICE_NAME% >nul 2>&1
if errorlevel 1 (echo   - service no longer present.) else (echo   - WARN: service still present.)
echo.

echo [2/2] Removing scheduled task "%TASKNAME%"...
schtasks /delete /tn "%TASKNAME%" /f >nul 2>&1
if errorlevel 1 (
    echo   - task "%TASKNAME%" was not present (ok).
) else (
    echo   - task "%TASKNAME%" deleted.
)

echo.
echo Done. Manual run still works:
echo   cd %PROJECT_DIR%
echo   venv\Scripts\python.exe bot.py
echo.
echo Re-enable auto-start later with scripts\install-all.bat
pause
endlocal
