@echo off
cd /d "%~dp0.."
echo ========================================
echo   FM Save Copilot - First Time Setup
echo ========================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo.
    echo Please install Python from python.org/downloads
    echo IMPORTANT: tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo Setting up... this takes a minute.
python -m venv venv
call venv\Scripts\activate.bat
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo.
echo Setup complete!
echo.

REM Offer to run the config wizard
set /p RUNWIZARD="Configure your club now? [Y/n]: "
if /i "%RUNWIZARD%"=="n" goto end
python scripts\setup_wizard.py

:end
echo.
echo You're ready. Double-click run.bat to generate a report.
echo.
pause
