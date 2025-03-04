import qrcode
from PIL import Image
import pandas as pd
import zipfile
import io
from typing import Dict, List, Tuple, Union, ByteString, Optional
import base64


def create_qr_code(url: str, size: int = 10, border: int = 4) -> Image.Image:
    """
    Create a QR code image from a URL.
    
    Args:
        url: The URL to encode in the QR code
        size: Size of the QR code (1-40)
        border: Border width in modules
        
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
    return img


def generate_qr_codes(df: pd.DataFrame, url_column: str, 
                      filename_column: str = 'generated_filename') -> List[Tuple[str, bytes]]:
    """
    Generate QR codes for all URLs in the dataframe.
    
    Args:
        df: DataFrame containing URLs and filenames
        url_column: Name of column containing URLs
        filename_column: Name of column containing filenames
        
    Returns:
        List[Tuple[str, bytes]]: List of (filename, image_bytes) tuples
    """
    qr_codes = []
    
    for _, row in df.iterrows():
        url = row[url_column]
        filename = row[filename_column]
        
        # Skip empty URLs
        if pd.isna(url) or url == '':
            continue
            
        # Generate QR code
        img = create_qr_code(url)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        qr_codes.append((filename, img_bytes))
    
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
