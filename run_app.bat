@echo off
setlocal enabledelayedexpansion

:: Check if running in Replit environment
if defined REPL_ID (
    echo Detected Replit environment. Launching directly...
    python -m streamlit run main.py
    exit /b 0
)

:: Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found. Please run install_windows.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment and run app
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Starting QR Code Generator app...
echo (Close the terminal window to exit the application)
echo.

:: Launch the app
python -m streamlit run main.py

:: Deactivate virtual environment on exit
call venv\Scripts\deactivate.bat
endlocal