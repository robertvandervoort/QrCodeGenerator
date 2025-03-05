#!/bin/bash

# Check if running in Replit environment
if [ -n "$REPL_ID" ]; then
    echo "Detected Replit environment. Launching directly..."
    python -m streamlit run main.py
    exit 0
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment and run app
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

echo "Starting QR Code Generator app..."
echo "(Press Ctrl+C to exit the application)"
echo ""

# Launch the app
python -m streamlit run main.py

# Deactivate virtual environment on exit
deactivate