@echo off
setlocal enabledelayedexpansion

echo QR Code Generator for Spreadsheets - Windows Installer
echo ====================================================
echo.

:: Check if running in Replit environment
if defined REPL_ID (
    echo Detected Replit environment. Skipping virtual environment setup.
    echo Installing dependencies...
    pip install -r app_requirements.txt
    goto :launch
)

:: Check for Python installation
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or later from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create a virtual environment if not exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        echo Please ensure you have the 'venv' module installed.
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install dependencies
echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

:launch
echo.
echo Installation complete!
echo.
echo Starting QR Code Generator app...
echo (Close the terminal window to exit the application)
echo.

:: Launch the app
python -m streamlit run main.py

:: Deactivate virtual environment on exit
call venv\Scripts\deactivate.bat
endlocal