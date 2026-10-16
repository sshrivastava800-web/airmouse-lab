@echo off
setlocal
cd /d "%~dp0"
echo AIR MOUSE LAB - setup and launch
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3.11 -m venv .venv
) else (
    python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo Could not create Python environment. Install Python 3.11 and retry.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependencies could not be installed. Check Python version and internet connection.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m airmouse
pause
