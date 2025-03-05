#!/bin/bash

echo "QR Code Generator for Spreadsheets - Installer"
echo "=============================================="
echo ""

# Check if running in Replit environment
if [ -n "$REPL_ID" ]; then
    echo "Detected Replit environment. Skipping virtual environment setup."
    echo "Installing dependencies..."
    pip install -r app_requirements.txt
    # Jump to launch section
    launch_app=true
else
    # Check for Python installation
    if ! command -v python3 &> /dev/null; then
        echo "Python 3 is not installed or not in PATH."
        echo "Please install Python 3.8 or later from your package manager or https://www.python.org/downloads/"
        exit 1
    fi

    # Create a virtual environment if not exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo "Failed to create virtual environment."
            echo "Please ensure you have the 'venv' module installed."
            exit 1
        fi
    fi

    # Activate virtual environment and install dependencies
    echo "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "Failed to activate virtual environment."
        exit 1
    fi

    echo "Installing dependencies..."
    pip install -r app_requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies."
        exit 1
    fi
    
    launch_app=true
fi

if [ "$launch_app" = true ]; then
    echo ""
    echo "Installation complete!"
    echo ""
    echo "Starting QR Code Generator app..."
    echo "(Press Ctrl+C to exit the application)"
    echo ""

    # Launch the app
    python -m streamlit run main.py
    
    # Deactivate virtual environment on exit if not in Replit
    if [ -z "$REPL_ID" ]; then
        deactivate
    fi
fi