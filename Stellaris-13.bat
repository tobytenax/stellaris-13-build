@echo off
title Stellaris-13
echo.
echo   Starting Stellaris-13...
echo.
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where python3 >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo  Python is not installed. Opening download page...
        start https://www.python.org/downloads/
        echo  Install Python, check "Add to PATH", then run this again.
        pause
        exit /b 1
    ) else ( set PYTHON=python3 )
) else ( set PYTHON=python )
cd /d "%~dp0"
if not exist ".deps_installed" (
    echo  Installing dependencies (first run only)...
    %PYTHON% -m pip install -r requirements.txt --quiet 2>nul
    if %ERRORLEVEL% NEQ 0 %PYTHON% -m pip install -r requirements.txt --quiet --break-system-packages 2>nul
    echo. > .deps_installed
)
echo  Opening browser...
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:13013"
%PYTHON% app.py
pause
