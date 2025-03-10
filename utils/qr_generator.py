import qrcode
from PIL import Image
import pandas as pd
import zipfile
import io
import re
import os
from typing import Dict, List, Tuple, Union, ByteString, Optional
import base64
from utils.logging_utils import logger, log_dataframe_info, log_row_data, log_qr_generation_summary


def create_qr_code(url: str, size: int = 10, border: int = 4, output_size: Optional[int] = None) -> Image.Image:
    """
    Create a QR code image from a URL.
    
    Args:
        url: The URL to encode in the QR code
        size: Size of the QR code box (1-40)
        border: Border width in modules
        output_size: Final output image size in pixels (if specified, will resize the image)
        
    Returns:
        PIL.Image: QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize image if output_size is specified
    if output_size and output_size > 0:
        img = img.resize((output_size, output_size), Image.LANCZOS)
        
    return img


def generate_qr_codes(df: pd.DataFrame, url_column: str, 
                      filename_column: str = 'generated_filename',
                      qr_size: int = 10, qr_border: int = 4,
                      output_size: Optional[int] = None) -> List[Tuple[str, bytes]]:
    """
    Generate QR codes for all URLs in the dataframe.
    
    Args:
        df: DataFrame containing URLs and filenames
        url_column: Name of column containing URLs
        filename_column: Name of column containing filenames
        qr_size: Size of the QR code modules
        qr_border: Border width in modules
        output_size: Final output image size in pixels (optional)
        
    Returns:
        List[Tuple[str, bytes]]: List of (filename, image_bytes) tuples
    """
    qr_codes = []
    
    # Log initial dataframe info
    log_dataframe_info(df, "Original dataframe before filtering")
    logger.info(f"Generating QR codes with parameters: qr_size={qr_size}, qr_border={qr_border}, output_size={output_size}")
    
    # Check data types and log URL column data type
    logger.info(f"URL column '{url_column}' data type: {df[url_column].dtype}")
    
    # Log detailed information about URL column to debug Excel formula issues
    logger.info("Examining URL column data to check for Excel formulas or dynamic content:")
    for idx, value in df[url_column].head(10).items():
        url_str = str(value)
        starts_with_http = url_str.lower().startswith('http')
        url_length = len(url_str)
        logger.info(f"Row {idx} URL: type={type(value).__name__}, length={url_length}, starts_with_http={starts_with_http}")
        logger.info(f"  Value: {url_str[:100]}{'...' if url_length > 100 else ''}")
        
    # Filter out rows with empty or NaN URLs to be extra safe
    valid_df = df.dropna(subset=[url_column]).copy()
    logger.info(f"After dropping NaN values in {url_column}: {len(valid_df)} rows remaining")
    
    # Filter out empty strings
    valid_df = valid_df[valid_df[url_column].astype(str).str.strip() != '']
    logger.info(f"After filtering empty strings in {url_column}: {len(valid_df)} rows remaining")
    
    # Check for URLs that don't start with http/https - might be Excel formulas not evaluating correctly
    non_http_urls = valid_df[~valid_df[url_column].astype(str).str.lower().str.startswith(('http://', 'https://'))]
    if not non_http_urls.empty:
        logger.warning(f"Found {len(non_http_urls)} URLs that don't start with http:// or https://")
        for idx, row in non_http_urls.head(5).iterrows():
            logger.warning(f"Row {idx} has non-HTTP URL: {str(row[url_column])}")
    
    # Check for problematic filename patterns that would be filtered later
    problematic_patterns = ['missing_missing', 'nan_nan', 'item_item', 'empty_empty']
    for pattern in problematic_patterns:
        matches = valid_df[valid_df[filename_column].astype(str).str.contains(pattern, case=False)]
        if not matches.empty:
            logger.warning(f"Found {len(matches)} rows with problematic filename pattern '{pattern}'")
            # For each matching row, log the raw URL value to help diagnose the issue
            for idx, row in matches.head(5).iterrows():
                url_value = row[url_column]
                logger.warning(f"Row {idx} with '{pattern}' in filename has URL: {url_value} (type: {type(url_value).__name__})")
    
    # Log filename info
    if filename_column in valid_df.columns:
        # Check for NaN or problematic values in filename column
        nan_filenames = valid_df[valid_df[filename_column].isna()].shape[0]
        if nan_filenames > 0:
            logger.warning(f"Found {nan_filenames} rows with NaN values in filename column '{filename_column}'")
        
        # Check for duplicate filenames
        filename_counts = valid_df[filename_column].astype(str).value_counts()
        duplicates = filename_counts[filename_counts > 1]
        if not duplicates.empty:
            logger.warning(f"Found duplicate filenames: {duplicates.to_dict()}")
    
    # Generate QR codes
    generated_filenames = []
    row_count = len(valid_df)
    
    for i, (index, row) in enumerate(valid_df.iterrows()):
        try:
            url = str(row[url_column])
            filename = str(row[filename_column])
            
            # Log the row data we're processing
            if i < 5 or i == row_count - 1:  # Log first 5 and last row
                log_row_data(row, index, f"Processing row {i+1}/{row_count}")
            elif i % 20 == 0:  # Log every 20th row
                logger.info(f"Processing row {i+1}/{row_count}")
            
            # Skip problematic filenames
            if any(pattern in filename.lower() for pattern in problematic_patterns):
                logger.warning(f"Row {index}: Skipping file with problematic filename pattern: {filename}")
                continue
            
            # Skip if filename contains 'nan' (could happen with str conversion of NaN)
            if 'nan' in filename.lower():
                logger.warning(f"Row {index}: Skipping file with NaN in filename: {filename}")
                continue
                
            # Skip if URL is just whitespace
            if url.strip() == '':
                logger.warning(f"Row {index}: Empty URL after stripping whitespace")
                continue
            
            # Skip if URL doesn't start with http:// or https:// 
            # This is optional - comment this out if you have valid URLs that don't start with http
            if not url.lower().startswith(('http://', 'https://')):
                logger.warning(f"Row {index}: URL doesn't start with http:// or https://: {url}")
                # We're not skipping these URLs as they may be valid formula results in Excel
                # If you want to skip them, uncomment the next line
                # continue
                
            # Generate QR code
            logger.info(f"Generating QR code for URL: {url[:50]}..." if len(url) > 50 else f"Generating QR code for URL: {url}")
            img = create_qr_code(url, size=qr_size, border=qr_border, output_size=output_size)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Keep track of generated filenames
            generated_filenames.append(filename)
            qr_codes.append((filename, img_bytes))
            logger.info(f"Successfully generated QR code: {filename}")
            
        except Exception as e:
            # Log the error with more details
            logger.error(f"Error processing row {index}:", exc_info=True)
            logger.error(f"Row data: URL={row.get(url_column, 'N/A')}, filename={row.get(filename_column, 'N/A')}")
            continue
    
    # Log summary information
    log_qr_generation_summary(
        total_rows=len(df),
        valid_rows=len(valid_df),
        qr_codes_generated=len(qr_codes),
        output_filenames=generated_filenames
    )
    
    return qr_codes


def create_zip_file(qr_codes: List[Tuple[str, bytes]]) -> bytes:
    """
    Create a ZIP file containing all generated QR codes.
    Handles potential duplicate filenames by adding a unique index.
    
    Args:
        qr_codes: List of (filename, image_bytes) tuples
        
    Returns:
        bytes: ZIP file as bytes
    """
    zip_buffer = io.BytesIO()
    
    # Track filenames to handle duplicates
    seen_filenames = {}
    skipped_files = 0
    
    # Check for problematic filenames
    problematic_patterns = ['missing_missing', 'nan_nan', 'item_item', 'empty_empty']
    problematic_count = sum(1 for filename, _ in qr_codes if any(pattern in filename.lower() for pattern in problematic_patterns))
    if problematic_count > 0:
        logger.warning(f"Found {problematic_count} filenames with problematic patterns (e.g., missing_missing)")
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, img_bytes in qr_codes:
            # Skip problematic filenames
            if any(pattern in filename.lower() for pattern in problematic_patterns):
                skipped_files += 1
                logger.warning(f"Skipping file with problematic filename pattern: {filename}")
                continue
            
            # Skip any filenames containing 'nan'
            if 'nan' in filename.lower():
                skipped_files += 1
                logger.warning(f"Skipping file with 'nan' in filename: {filename}")
                continue
                
            # Handle duplicate filenames
            if filename in seen_filenames:
                seen_filenames[filename] += 1
                base_name, ext = filename.rsplit('.', 1)
                unique_filename = f"{base_name}_{seen_filenames[filename]}.{ext}"
                logger.warning(f"Duplicate filename: '{filename}' renamed to '{unique_filename}'")
                filename = unique_filename
            else:
                seen_filenames[filename] = 1
            
            # Add to zip file
            try:
                zip_file.writestr(filename, img_bytes)
                logger.info(f"Added file to ZIP: {filename}")
            except Exception as e:
                logger.error(f"Error adding {filename} to ZIP: {str(e)}")
                skipped_files += 1
    
    # Log summary
    logger.info(f"ZIP file created with {len(seen_filenames)} QR codes")
    if skipped_files > 0 or len(seen_filenames) != len(qr_codes):
        total_skipped = len(qr_codes) - len(seen_filenames)
        logger.warning(f"Note: {total_skipped} files were skipped or renamed due to duplicates or invalid names")
        logger.warning(f"Skipped files (problematic patterns): {skipped_files}")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def get_image_download_link(img_bytes: bytes, filename: str) -> str:
    """
    Generate an HTML download link for a single image.
    
    Args:
        img_bytes: Image data as bytes
        filename: Name for the downloaded file
        
    Returns:
        str: HTML link for downloading the image
    """
    b64_img = base64.b64encode(img_bytes).decode()
    href = f'<a href="data:image/png;base64,{b64_img}" download="{filename}">Download {filename}</a>'
    return href
