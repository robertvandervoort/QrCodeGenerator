import logging
import sys
import pandas as pd
from typing import Any, Dict, List, Optional

# Set up basic logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger("qr_generator")

# Function to adjust logger level based on debug mode setting
def set_debug_mode(enabled: bool = False):
    """
    Set the debug mode for the application's logger.
    
    Args:
        enabled: If True, sets the logger to DEBUG level with verbose output.
                If False, sets the logger to INFO level with minimal output.
    """
    if enabled:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled - verbose logging activated")
    else:
        logger.setLevel(logging.WARNING)  # Only show warnings and errors in normal mode

def log_dataframe_info(df: pd.DataFrame, description: str) -> None:
    """
    Log information about a dataframe.
    
    Args:
        df: DataFrame to log information about
        description: Description of the dataframe
    """
    logger.info(f"{description} | Shape: {df.shape} | Columns: {list(df.columns)}")
    
    # Log value counts for NaN values in each column
    na_counts = df.isna().sum()
    if na_counts.sum() > 0:
        logger.info(f"NaN counts in {description}:")
        for col, count in na_counts.items():
            if count > 0:
                logger.info(f"  - {col}: {count} NaN values")

def log_row_data(row: pd.Series, row_index: int, description: str) -> None:
    """
    Log information about a specific row.
    
    Args:
        row: Series containing row data
        row_index: Index of the row in the original dataframe
        description: Description of the logging context
    """
    logger.info(f"{description} | Row {row_index}:")
    for col, value in row.items():
        logger.info(f"  - {col}: {value} (type: {type(value).__name__})")

def log_qr_generation_summary(
    total_rows: int, 
    valid_rows: int,
    qr_codes_generated: int,
    output_filenames: Optional[List[str]] = None
) -> None:
    """
    Log summary information about QR code generation.
    
    Args:
        total_rows: Total number of rows in the original dataframe
        valid_rows: Number of rows after filtering invalid/empty values
        qr_codes_generated: Number of QR codes successfully generated
        output_filenames: Optional list of generated filenames
    """
    logger.info(f"QR Code Generation Summary:")
    logger.info(f"  - Total rows in original data: {total_rows}")
    logger.info(f"  - Valid rows after filtering: {valid_rows}")
    logger.info(f"  - QR codes successfully generated: {qr_codes_generated}")
    
    if output_filenames:
        # Check for duplicates in filenames
        filename_counts = {}
        for filename in output_filenames:
            if filename in filename_counts:
                filename_counts[filename] += 1
            else:
                filename_counts[filename] = 1
        
        # Log duplicates if any
        duplicates = {f: c for f, c in filename_counts.items() if c > 1}
        if duplicates:
            logger.warning(f"Duplicate filenames detected:")
            for filename, count in duplicates.items():
                logger.warning(f"  - {filename}: appears {count} times")