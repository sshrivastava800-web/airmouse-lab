@echo off
setlocal
cd /d "%~dp0"
echo AIR MOUSE LAB - Python 3.15 setup and launch

echo Checking for Python 3.15...
where py >nul 2>nul
if not errorlevel 1 (
    py -3.15 --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.15"
        goto :setup
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 15) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        goto :setup
    )
)
echo ERROR: Python 3.15 was not found.
echo Install the current 64-bit Python from https://www.python.org/downloads/
pause
exit /b 1

:setup
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 15) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo Removing old project virtual environment...
        rmdir /s /q ".venv"
    )
)
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :python_error
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :dependency_error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :dependency_error
".venv\Scripts\python.exe" -m airmouse
if errorlevel 1 echo AirMouse Lab closed with an error.
pause
exit /b 0

:python_error
echo ERROR: Could not create a Python 3.15 environment.
pause
exit /b 1
:dependency_error
echo ERROR: Dependencies could not be installed. Check internet and Python 3.15 package compatibility.
pause
exit /b 1
