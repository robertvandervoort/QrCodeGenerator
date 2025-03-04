import pandas as pd
import re
from io import BytesIO
from typing import List, Dict, Tuple, Optional, Union, Set
from utils.logging_utils import logger, log_dataframe_info


def read_file(uploaded_file) -> Dict:
    """
    Read an uploaded file (Excel or CSV) and return a dictionary of dataframes.
    
    Args:
        uploaded_file: The uploaded file object from Streamlit
        
    Returns:
        Dict: Dictionary with sheet names as keys and dataframes as values
    """
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension in ['xls', 'xlsx', 'xlsm']:
        # For Excel files, read all sheets
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        sheets_data = {}
        
        for sheet in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            if not df.empty:
                sheets_data[sheet] = df
        
        return sheets_data
    
    elif file_extension == 'csv':
        # For CSV files, there's only one sheet
        df = pd.read_csv(uploaded_file)
        return {'Sheet1': df}
    
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")


def detect_url_columns(df: pd.DataFrame, sample_rows: int = 5) -> List[str]:
    """
    Detect columns that likely contain URLs.
    
    Args:
        df: DataFrame to analyze
        sample_rows: Number of rows to sample for detection
        
    Returns:
        List[str]: List of column names that contain URLs
    """
    url_columns = []
    url_pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    # Check each column
    for col in df.columns:
        # Get the first few rows of non-null values
        sample_values = df[col].dropna().head(sample_rows).astype(str)
        
        # Skip if sample is empty
        if len(sample_values) == 0:
            continue
        
        # Check if most values match URL pattern
        url_count = sum(1 for value in sample_values if url_pattern.match(value))
        
        # If at least 60% of the values appear to be URLs, consider it a URL column
        if url_count / len(sample_values) >= 0.6:
            url_columns.append(col)
    
    return url_columns


def validate_filename_parts(df: pd.DataFrame, selected_columns: List[str], separator: str) -> Tuple[bool, str]:
    """
    Validate if the selected columns and separator will create valid filenames.
    
    Args:
        df: DataFrame with the data
        selected_columns: Columns selected for filename construction
        separator: Character to separate column values in filenames
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Check if separator is valid for filenames
    invalid_chars = r'<>:"/\|?*'
    if separator in invalid_chars:
        return False, f"Separator contains invalid filename character: '{separator}'"
    
    # Sample a few rows to check filename validity
    sample_size = min(5, len(df))
    
    for i in range(sample_size):
        filename_parts = []
        for col in selected_columns:
            if col in df.columns:
                value = str(df.iloc[i][col])
                # Replace invalid filename characters
                for char in invalid_chars:
                    value = value.replace(char, '-')
                filename_parts.append(value)
        
        test_filename = separator.join(filename_parts) + '.png'
        if len(test_filename) > 255:
            return False, f"Generated filename exceeds 255 characters: '{test_filename[:50]}...'"
    
    return True, ""


def prepare_dataframe(df: pd.DataFrame, url_column: str, filename_columns: List[str], separator: str) -> pd.DataFrame:
    """
    Prepare a dataframe for QR code generation by adding a filename column.
    Filter out rows with empty or NaN values in the URL column.
    
    Args:
        df: Source dataframe
        url_column: Column name containing URL data
        filename_columns: Columns to use for filename construction
        separator: Character to separate values in filenames
        
    Returns:
        pd.DataFrame: Processed dataframe with filename column and filtered rows
    """
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Log input dataframe info
    log_dataframe_info(processed_df, "Original dataframe")
    logger.info(f"URL column: {url_column}, Filename columns: {filename_columns}, Separator: '{separator}'")
    
    # Filter out rows with empty or NaN URLs
    original_count = len(processed_df)
    processed_df = processed_df.dropna(subset=[url_column])
    after_nan_count = len(processed_df)
    if original_count > after_nan_count:
        logger.info(f"Dropped {original_count - after_nan_count} rows with NaN values in URL column '{url_column}'")
    
    # Filter empty strings
    processed_df = processed_df[processed_df[url_column].astype(str).str.strip() != '']
    after_empty_count = len(processed_df)
    if after_nan_count > after_empty_count:
        logger.info(f"Dropped {after_nan_count - after_empty_count} rows with empty strings in URL column '{url_column}'")
    
    # Create a helper function to safely convert cell values
    def safe_str_value(value):
        if pd.isna(value):
            return "missing"  # Replace NaN with a descriptive placeholder
        s = str(value)
        return s if s.strip() != '' else "empty"  # Replace empty strings
    
    # Create filename column with safe value conversion
    logger.info("Creating filename column with safe value conversion")
    processed_df['generated_filename'] = processed_df.apply(
        lambda row: separator.join(safe_str_value(row[col]) for col in filename_columns) + '.png', 
        axis=1
    )
    
    # Sanitize filenames by replacing invalid characters
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        processed_df['generated_filename'] = processed_df['generated_filename'].str.replace(char, '-')
    
    # Replace 'nan' in filenames with 'missing'
    processed_df['generated_filename'] = processed_df['generated_filename'].str.replace('nan', 'missing')
    
    # Log filenames that still contain 'nan' after replacement
    nan_filenames = processed_df[processed_df['generated_filename'].str.contains('nan')]
    if not nan_filenames.empty:
        logger.warning(f"Found {len(nan_filenames)} filenames still containing 'nan' after replacement")
        logger.warning(f"Sample filenames: {nan_filenames['generated_filename'].head(3).tolist()}")
    
    # Check for duplicate filenames
    filename_counts = processed_df['generated_filename'].value_counts()
    duplicates = filename_counts[filename_counts > 1]
    if not duplicates.empty:
        logger.warning(f"Found {len(duplicates)} duplicate filenames")
        for filename, count in duplicates.items():
            logger.warning(f"Filename '{filename}' appears {count} times")
        
        # Add a unique suffix to duplicate filenames
        dup_mask = processed_df['generated_filename'].duplicated(keep=False)
        processed_df.loc[dup_mask, 'generated_filename'] = processed_df.loc[dup_mask].apply(
            lambda x: x['generated_filename'].replace('.png', f'_{pd.util.hash_pandas_object(x).sum()}.png'),
            axis=1
        )
        logger.info("Added unique suffixes to duplicate filenames")
    
    # Keep only necessary columns
    processed_df = processed_df[[url_column, 'generated_filename']]
    
    # Log final dataframe info
    log_dataframe_info(processed_df, "Final processed dataframe")
    
    return processed_df
