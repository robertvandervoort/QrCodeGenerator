import qrcode
from PIL import Image
import pandas as pd
import zipfile
import io
from typing import Dict, List, Tuple, Union, ByteString, Optional
import base64


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
    
    # Filter out rows with empty or NaN URLs to be extra safe
    valid_df = df.dropna(subset=[url_column]).copy()
    valid_df = valid_df[valid_df[url_column].astype(str).str.strip() != '']
    
    for _, row in valid_df.iterrows():
        try:
            url = str(row[url_column])
            filename = str(row[filename_column])
            
            # Skip if URL is just whitespace
            if url.strip() == '':
                continue
                
            # Generate QR code
            img = create_qr_code(url, size=qr_size, border=qr_border, output_size=output_size)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            qr_codes.append((filename, img_bytes))
            
        except Exception as e:
            # Skip problematic rows but continue processing
            print(f"Error processing row: {e}")
            continue
    
    return qr_codes


def create_zip_file(qr_codes: List[Tuple[str, bytes]]) -> bytes:
    """
    Create a ZIP file containing all generated QR codes.
    
    Args:
        qr_codes: List of (filename, image_bytes) tuples
        
    Returns:
        bytes: ZIP file as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, img_bytes in qr_codes:
            zip_file.writestr(filename, img_bytes)
    
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
