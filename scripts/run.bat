@echo off
cd /d "%~dp0.."

REM Activate the virtual environment
if not exist venv\Scripts\activate.bat (
    echo ERROR: Setup has not been run yet.
    echo Please double-click setup.bat first.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM Check config exists
if not exist config\config.yaml (
    echo.
    echo No config found. Have you run setup.bat?
    echo.
    echo 1. Run setup.bat first (installs dependencies + wizard)
    echo 2. Or copy config\config.example.yaml to config\config.yaml
    echo    and fill in your settings.
    echo.
    pause
    exit /b 1
)

echo Generating your Director of Football report...
echo.

python -m fm_copilot --open
if errorlevel 1 (
    echo.
    echo Something went wrong. See the message above.
    echo.
    echo If you see "squad file not found": export squad.html from FM24
    echo and save it to the data_uploads folder. See VIEW-SETUP.md.
    echo.
    pause
    exit /b 1
)

pause
