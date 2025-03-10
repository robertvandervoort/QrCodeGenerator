import streamlit as st
import pandas as pd
import io
import base64
import zipfile
from typing import List, Dict, Tuple, Optional
import os
from PIL import Image

# Import utility modules
from utils.file_handler import (
    read_file, 
    detect_url_columns, 
    validate_filename_parts,
    prepare_dataframe
)
from utils.qr_generator import (
    create_qr_code,
    generate_qr_codes,
    create_zip_file,
    get_image_download_link
)
from utils.logging_utils import logger, log_dataframe_info, log_qr_generation_summary, set_debug_mode

# Initialize session state variables if they don't exist
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Page configuration
st.set_page_config(
    page_title="QR Code Generator",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': 'https://github.com/robertvandervoort/QrCodeGenerator/readme.md',
        'Report a bug': "https://github.com/robertvandervoort/QrCodeGenerator/issues/new",
        'About': "# QR Code Generator\n"
                "A tool to generate QR codes from individual URLs or from spreadsheet data.\n\n"
                "Version: 1.1.0"
    }
)

# Initialize the debug mode from URL parameters if available
try:
    query_params = st.query_params
    if "debug" in query_params:
        debug_value = query_params["debug"] == "true"
        st.session_state.debug_mode = debug_value
        set_debug_mode(debug_value)
except:
    # Fallback for older Streamlit versions
    pass

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .download-link {
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
        background-color: #f5f5f5;
    }
    h1, h2, h3 {
        color: #2C3E50;
    }
    .stButton button {
        width: 100%;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stSelectbox label, .stMultiselect label {
        font-weight: bold;
        color: #2C3E50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'sheets_data' not in st.session_state:
    st.session_state.sheets_data = {}
if 'selected_sheet' not in st.session_state:
    st.session_state.selected_sheet = None
if 'url_columns' not in st.session_state:
    st.session_state.url_columns = []
if 'current_df' not in st.session_state:
    st.session_state.current_df = None
if 'qr_codes' not in st.session_state:
    st.session_state.qr_codes = []
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'qr_size' not in st.session_state:
    st.session_state.qr_size = 10
if 'qr_border' not in st.session_state:
    st.session_state.qr_border = 4
if 'output_resolution' not in st.session_state:
    st.session_state.output_resolution = ""

# Title and introduction
st.title("QR Code Generator")
st.write("""
Generate QR codes from URLs in spreadsheet data or quickly create a single QR code.
""")

# Quick Single URL QR Code Generator
st.subheader("✨ Quick Single URL Generator")
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        quick_url = st.text_input("Enter URL", placeholder="https://example.com", help="Enter any URL to create a QR code instantly")
    
    with col2:
        qr_size_quick = st.number_input("Module Size", min_value=5, max_value=20, value=10, help="Size of each individual QR code module/square in pixels")
    
    # Advanced options expander
    with st.expander("Advanced Options", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            qr_border_quick = st.slider("Border Width", min_value=0, max_value=8, value=4, help="Width of white border around QR code")
        with col2:
            output_res_quick = st.number_input("Output Resolution", min_value=0, value=250, step=10, help="Final output image size in pixels (width & height). Controls the overall size of the QR code image regardless of module size.")
    
    if quick_url:
        if not quick_url.lower().startswith(('http://', 'https://')):
            quick_url = "https://" + quick_url
        
        # Parse output resolution
        output_size_quick = None
        if output_res_quick > 0:
            output_size_quick = output_res_quick
        
        # Generate QR code
        qr_img = create_qr_code(quick_url, size=qr_size_quick, border=qr_border_quick, output_size=output_size_quick)
        qr_img_bytes = io.BytesIO()
        qr_img.save(qr_img_bytes, format='PNG')
        qr_img_bytes = qr_img_bytes.getvalue()
        
        # Display QR code
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(qr_img_bytes, width=250)
        with col2:
            st.markdown("#### Download Options")
            # Create filename from URL
            domain = quick_url.replace('https://', '').replace('http://', '').split('/')[0]
            filename = f"qr_{domain}.png"
            
            # Download button
            st.download_button(
                label="Download QR Code",
                data=qr_img_bytes,
                file_name=filename,
                mime="image/png",
            )
            # HTML link (for more compatibility)
            st.markdown(get_image_download_link(qr_img_bytes, filename), unsafe_allow_html=True)

st.divider()  # Divider between quick generator and batch processing

# Batch processing introduction
st.subheader("📊 Spreadsheet Batch Processing")
st.write("""
Upload an Excel spreadsheet or CSV file to generate QR codes from URLs in the data.
The application will automatically detect columns containing URLs and allow you
to select which columns to use for naming the output files.
""")

# Sidebar for file upload and options
with st.sidebar:
    st.header("Upload & Options")
    
    uploaded_file = st.file_uploader("Upload Excel or CSV file", 
                                    type=["xlsx", "xls", "csv"],
                                    help="Upload a spreadsheet containing URLs to generate QR codes")
    
    # Process uploaded file
    if uploaded_file and (st.session_state.uploaded_file is None or 
                         uploaded_file.name != st.session_state.uploaded_file.name):
        try:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.sheets_data = read_file(uploaded_file)
            st.session_state.selected_sheet = None
            st.session_state.url_columns = []
            st.session_state.current_df = None
            st.session_state.qr_codes = []
            st.success(f"File '{uploaded_file.name}' loaded successfully!")
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    
    # Sheet selection (for Excel files)
    if st.session_state.sheets_data:
        sheet_names = list(st.session_state.sheets_data.keys())
        
        if len(sheet_names) > 1:  # Only show if multiple sheets exist
            selected_sheet = st.selectbox(
                "Select Sheet", 
                options=sheet_names,
                help="Choose which sheet in the Excel file to process"
            )
        else:
            selected_sheet = sheet_names[0]
        
        # Update current dataframe when sheet changes
        if selected_sheet != st.session_state.selected_sheet:
            st.session_state.selected_sheet = selected_sheet
            st.session_state.current_df = st.session_state.sheets_data[selected_sheet]
            st.session_state.url_columns = detect_url_columns(st.session_state.current_df)
            st.session_state.qr_codes = []
    
    # QR code options
    if st.session_state.current_df is not None:
        st.write("---")
        st.header("QR Code Options")
        
        # Update session state with the slider values
        st.session_state.qr_size = st.slider("Module Size", 
                           min_value=1, max_value=20, value=st.session_state.qr_size, 
                           help="Size of each individual QR code module/square in pixels")
        
        st.session_state.qr_border = st.slider("Border Width", 
                             min_value=0, max_value=10, value=st.session_state.qr_border,
                             help="Width of the QR code border in modules")
        
        st.session_state.output_resolution = st.text_input(
            "Output Resolution (pixels)", 
            value=st.session_state.output_resolution, 
            placeholder="e.g., 250 for 250x250 pixels",
            help="Final output image size in pixels (width & height). Controls the overall size of the QR code image regardless of module size."
        )
    
    # Add debug mode section at the bottom of the sidebar
    st.write("---")
    st.header("Debug Options")
    
    # Add explanatory text
    st.info("""
    Debug mode increases logging verbosity to help troubleshoot issues with file processing and QR code generation.
    When enabled, detailed logs will be written to the console with information about data processing, URL validation, and QR code creation.
    """)
    
    # Create a debug mode checkbox in the sidebar
    debug_checkbox = st.checkbox("Enable Debug Mode", value=st.session_state.debug_mode, 
                     help="Show detailed logs in the console for troubleshooting")
    
    if debug_checkbox != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_checkbox
        set_debug_mode(debug_checkbox)
        
        # Show a notification if the debug mode changed
        if debug_checkbox:
            st.success("Debug mode enabled")
        else:
            st.success("Debug mode disabled")
        
        # Update URL parameter
        try:
            st.query_params.debug = "true" if debug_checkbox else "false"
        except:
            # Fallback for older Streamlit versions
            pass

# Main area - Show data and generate QR codes
if st.session_state.current_df is not None:
    # Display dataset info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dataset Information")
        st.write(f"Sheet: **{st.session_state.selected_sheet}**")
        st.write(f"Rows: **{len(st.session_state.current_df)}**")
        st.write(f"Columns: **{len(st.session_state.current_df.columns)}**")
    
    with col2:
        if st.session_state.url_columns:
            st.subheader("Detected URL Columns")
            st.write(", ".join(st.session_state.url_columns))
        else:
            st.warning("No URL columns automatically detected. Please select manually.")
    
    # Display data preview
    with st.expander("Data Preview", expanded=True):
        st.dataframe(st.session_state.current_df.head(5), use_container_width=True)
    
    # QR Code generation form
    st.write("---")
    st.subheader("Configure QR Code Generation")
    
    with st.form("qr_code_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # URL column selection
            all_columns = list(st.session_state.current_df.columns)
            suggested_url_column = st.session_state.url_columns[0] if st.session_state.url_columns else None
            
            url_column = st.selectbox(
                "Select URL Column", 
                options=all_columns,
                index=all_columns.index(suggested_url_column) if suggested_url_column else 0,
                help="Column containing URLs for QR code generation"
            )
        
        with col2:
            # Filename columns selection
            filename_columns = st.multiselect(
                "Select Columns for Filename", 
                options=all_columns,
                default=[all_columns[0]] if all_columns else [],
                help="Columns to use for constructing output filenames"
            )
        
        # Separator for filename parts
        separator = st.text_input(
            "Filename Separator", 
            value="_",
            max_chars=3,
            help="Character(s) to separate filename parts"
        )
        
        # Submit button
        submitted = st.form_submit_button("Generate QR Codes", use_container_width=True)
        
        if submitted:
            if not filename_columns:
                st.error("Please select at least one column for filename construction.")
            else:
                # Validate filename parts will create valid filenames
                is_valid, error_message = validate_filename_parts(
                    st.session_state.current_df, 
                    filename_columns, 
                    separator
                )
                
                if not is_valid:
                    st.error(error_message)
                else:
                    # Prepare data for QR code generation
                    processed_df = prepare_dataframe(
                        st.session_state.current_df,
                        url_column,
                        filename_columns,
                        separator
                    )
                    
                    # Generate QR codes with progress bar
                    st.write("Generating QR codes...")
                    progress_bar = st.progress(0)
                    qr_codes = []
                    
                    # Calculate batch size for progress updates
                    total_rows = len(processed_df)
                    
                    # Parse output resolution
                    output_size = None
                    if st.session_state.output_resolution and st.session_state.output_resolution.strip():
                        try:
                            output_size = int(st.session_state.output_resolution.strip())
                        except ValueError:
                            st.warning(f"Invalid output resolution '{st.session_state.output_resolution}'. Using default size.")
                    
                    # Check how many rows were filtered out due to empty URL values
                    total_rows = len(st.session_state.current_df)
                    valid_rows = len(processed_df)
                    skipped_rows = total_rows - valid_rows
                    
                    # Generate QR codes
                    qr_codes = generate_qr_codes(
                        processed_df, 
                        url_column, 
                        qr_size=st.session_state.qr_size, 
                        qr_border=st.session_state.qr_border,
                        output_size=output_size
                    )
                    st.session_state.qr_codes = qr_codes
                    progress_bar.progress(100)
                    
                    # Success message with info about skipped rows
                    st.success(f"Generated {len(qr_codes)} QR codes successfully!")
                    
                    # Show info about skipped rows if any
                    if skipped_rows > 0:
                        st.info(f"Note: {skipped_rows} rows were skipped because they contained empty or invalid URL data.")

    # Display generated QR codes
    if st.session_state.qr_codes:
        st.write("---")
        st.subheader("Generated QR Codes")
        
        # Create download button for zip file
        zip_data = create_zip_file(st.session_state.qr_codes)
        
        # Count actual files in the ZIP
        actual_files = 0
        try:
            zip_buffer = io.BytesIO(zip_data)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                # List all files in the ZIP
                file_list = zip_ref.namelist()
                actual_files = len(file_list)
                logger.info(f"Files in ZIP archive: {actual_files}")
                
                # Log the first few filenames
                if file_list:
                    logger.info(f"First 5 files in ZIP: {file_list[:5]}")
                
                # Check for potential issues
                if actual_files != len(st.session_state.qr_codes):
                    logger.warning(f"ZIP contains {actual_files} files but generated {len(st.session_state.qr_codes)} QR codes")
        except Exception as e:
            logger.error(f"Error analyzing ZIP file: {str(e)}")
        
        # Show detailed info to user
        st.info(f"QR Codes Generated: {len(st.session_state.qr_codes)} | Files in ZIP: {actual_files}")
        if actual_files < len(st.session_state.qr_codes):
            st.warning(f"Note: {len(st.session_state.qr_codes) - actual_files} QR codes were skipped or merged due to duplicate or invalid filenames.")
        
        # Create a download button for the ZIP file
        st.download_button(
            label=f"Download All {actual_files} QR Codes as ZIP",
            data=zip_data,
            file_name="qr_codes.zip",
            mime="application/zip",
            help="Download all generated QR codes in a single ZIP file",
            use_container_width=True
        )
        
        # Display individual QR codes with preview
        st.write("### Individual QR Codes")
        
        # Display in a grid (3 columns)
        cols = st.columns(3)
        
        for i, (filename, img_bytes) in enumerate(st.session_state.qr_codes[:9]):  # Show first 9 QR codes
            with cols[i % 3]:
                # Display QR code image
                b64_img = base64.b64encode(img_bytes).decode()
                st.image(img_bytes, caption=filename, width=150)
                
                # Create download link for individual QR code
                st.markdown(
                    f'<div class="download-link">{get_image_download_link(img_bytes, filename)}</div>',
                    unsafe_allow_html=True
                )
        
        # Show a message if there are more QR codes
        if len(st.session_state.qr_codes) > 9:
            st.info(f"Showing 9 of {len(st.session_state.qr_codes)} QR codes. Download the ZIP file to get all codes.")

else:
    # Show instructions for batch processing
    st.info("""
    ### How to use Spreadsheet Batch Processing:
    
    1. Upload an Excel (.xlsx, .xls) or CSV file using the sidebar
    2. Select a sheet (for Excel files with multiple sheets)
    3. Choose the column containing URLs for QR code generation
    4. Select columns to use for naming the output files
    5. Set a separator character for the filename parts
    6. Click "Generate QR Codes" to create your QR codes
    7. Download individual QR codes or all as a ZIP file
    
    This application automatically detects columns containing URLs to help you get started.
    """
    )

# Footer
st.write("---")

# Copyright footer
st.markdown("""
<div style="text-align: center; color: #888;">
    Built with Streamlit • QR Code Generator for URLs and Spreadsheet Data
</div>
""", unsafe_allow_html=True)
