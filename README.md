# QR Code Generator for Spreadsheet Data

A web-based application that processes Excel/CSV files to generate QR codes from URL data, with customizable file naming based on column data.

## Features

- Upload Excel (.xlsx, .xls) or CSV files
- Automatic detection of URL columns in spreadsheets
- Custom QR code size, border width, and resolution
- Create unique filenames using data from multiple columns
- Download individual QR codes or as a ZIP archive
- Debug mode for troubleshooting

## Requirements

- Python 3.8 or higher
- Dependencies listed in `app_requirements.txt`

## Installation

### Windows

1. Download or clone this repository
2. Double-click the `install_windows.bat` file
3. The installer will:
   - Check for Python installation
   - Create a virtual environment (if not in Replit)
   - Install required dependencies
   - Launch the application in your default browser

### Linux/Mac

1. Download or clone this repository
2. Open Terminal in the project directory
3. Run the following commands:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
4. The installer will:
   - Check for Python installation
   - Create a virtual environment (if not in Replit)
   - Install required dependencies
   - Launch the application in your default browser

## Manual Installation

If you prefer to install manually:

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r app_requirements.txt
   ```

4. Run the application:
   ```bash
   streamlit run main.py
   ```

## Usage

1. Upload an Excel (.xlsx, .xls) or CSV file using the sidebar
2. Select a sheet (for Excel files with multiple sheets)
3. Choose the column containing URLs for QR code generation
4. Select columns to use for naming the output files
5. Set a separator character for the filename parts
6. Click "Generate QR Codes" to create your QR codes
7. Download individual QR codes or all as a ZIP file

## Debug Mode

If you encounter issues with file processing or QR code generation, you can enable Debug Mode from the bottom of the sidebar. This will provide more detailed logs in the console for troubleshooting.

## Report Bugs or Get Help

- [Report a bug](https://github.com/robertvandervoort/QrCodeGenerator/issues/new)
- [Get help](https://github.com/robertvandervoort/QrCodeGenerator/readme.md)