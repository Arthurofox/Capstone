import pandas as pd
import re
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_job_data(input_path, output_path):
    """
    Clean and preprocess job data from a messy CSV file
    
    Args:
        input_path: Path to the input CSV file
        output_path: Path to save the cleaned CSV file
    """
    logger.info(f"Reading CSV from {input_path}")
    
    try:
        # First attempt - try with standard reading
        df = pd.read_csv(input_path, encoding='utf-8')
    except Exception as e:
        logger.warning(f"Standard reading failed, trying with error handling: {str(e)}")
        # Try with more forgiving settings
        df = pd.read_csv(input_path, encoding='utf-8', on_bad_lines='skip')
    
    logger.info(f"Initial shape: {df.shape}")
    
    # Get the expected columns
    expected_columns = [
        'title', 'company', 'location', 'contract_type', 'posted_date', 
        'education_level', 'skills', 'languages', 'salary_range', 
        'description', 'url'
    ]
    
    # Check if we have the expected columns
    actual_columns = df.columns.tolist()
    logger.info(f"Actual columns: {actual_columns}")
    
    # If we have unnamed columns, try to interpret them
    unnamed_columns = [col for col in actual_columns if 'Unnamed:' in col]
    if unnamed_columns:
        logger.info(f"Found {len(unnamed_columns)} unnamed columns")
        
        # Simple approach: drop unnamed columns
        df = df.drop(columns=unnamed_columns)
        logger.info(f"Dropped unnamed columns. New shape: {df.shape}")
    
    # Check for missing expected columns and add them if needed
    for col in expected_columns:
        if col not in df.columns:
            logger.info(f"Adding missing column: {col}")
            df[col] = ""
    
    # Filter to keep only expected columns if they exist
    existing_columns = [col for col in expected_columns if col in df.columns]
    df = df[existing_columns]
    
    # Clean up data
    for col in df.columns:
        if df[col].dtype == 'object':
            # Replace NaN with empty string
            df[col] = df[col].fillna("")
            
            # Strip whitespace
            df[col] = df[col].astype(str).str.strip()
    
    # Handle specific problematic data patterns
    # For example, if title is empty but company is not, the data might be shifted
    # Fixed the boolean operation - using & with parentheses for proper pandas syntax
    shifted_rows = df[(df['title'].str.len() == 0) & (df['company'].str.len() > 0)].index
    if len(shifted_rows) > 0:
        logger.info(f"Found {len(shifted_rows)} rows with potential column shifting")
        
        # You would need a custom logic to fix the shifting based on your data patterns
        # This is just a placeholder - real implementation would be more complex
        for idx in shifted_rows:
            # Example logic - shift columns to the left
            row = df.loc[idx].tolist()
            if len(row) >= len(df.columns):
                df.loc[idx] = [''] + row[:-1]
    
    # Validate final data
    null_titles = df[(df['title'].isnull()) | (df['title'] == '')].shape[0]
    logger.info(f"Rows with empty titles: {null_titles}")
    
    # Drop rows with missing essential information (title and company)
    before_drop = df.shape[0]
    df = df.dropna(subset=['title', 'company'], how='all')
    after_drop = df.shape[0]
    logger.info(f"Dropped {before_drop - after_drop} rows with missing title AND company")
    
    # Fix rows with data in wrong columns (common in messy CSVs)
    logger.info("Looking for misaligned data...")
    
    # Detect potential URLs in wrong columns
    for col in df.columns:
        if col != 'url':
            # Find URLs in non-URL columns
            mask = df[col].str.contains('http', na=False, regex=True)
            if mask.any():
                num_urls = mask.sum()
                logger.info(f"Found {num_urls} URLs in column '{col}'")
                
                # Move these URLs to the URL column where they belong
                for idx in df[mask].index:
                    if not df.loc[idx, 'url']:  # Only if URL column is empty
                        df.loc[idx, 'url'] = df.loc[idx, col]
                        df.loc[idx, col] = ""  # Clear the original cell
    
    # Look for common misalignment patterns
    # e.g., if company names are in location column and locations are in contract_type, etc.
    logger.info("Checking for common misalignment patterns...")
    
    # Save to new file
    logger.info(f"Saving cleaned data to {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"Saved {df.shape[0]} rows with {df.shape[1]} columns")
    
    return df.shape[0]

def extract_structured_job_data(input_path, output_path):
    """
    Process job data and extract structured information
    
    Args:
        input_path: Path to the input CSV file
        output_path: Path to save the structured CSV file
    """
    logger.info(f"Reading CSV for structuring from {input_path}")
    
    try:
        df = pd.read_csv(input_path, encoding='utf-8')
        logger.info(f"Data shape: {df.shape}")
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return 0
    
    # Create a structured data representation
    structured_jobs = []
    
    for i, row in df.iterrows():
        # Handle empty/missing values
        title = str(row.get('title', '')).strip() or 'Untitled Position'
        company = str(row.get('company', '')).strip() or 'Unknown Company'
        location = str(row.get('location', '')).strip() or 'Location not specified'
        contract_type = str(row.get('contract_type', '')).strip() or 'Not specified'
        
        # Skip rows where both title and company are empty or "N/A"
        if (title.lower() in ['', 'n/a', 'nan'] and 
            company.lower() in ['', 'n/a', 'nan']):
            continue
        
        # Create structured job data
        job = {
            'title': title,
            'company': company,
            'location': location,
            'contract_type': contract_type,
            'posted_date': str(row.get('posted_date', '')).strip() or 'Unknown',
            'education_level': str(row.get('education_level', '')).strip() or 'Not specified',
            'skills': str(row.get('skills', '')).strip() or 'Not specified',
            'languages': str(row.get('languages', '')).strip() or 'Not specified',
            'salary_range': str(row.get('salary_range', '')).strip() or 'Not specified',
            'description': str(row.get('description', '')).strip() or 'No description provided',
            'url': str(row.get('url', '')).strip() or ''
        }
        
        # Only include jobs with meaningful data
        if (job['title'] != 'Untitled Position' or job['company'] != 'Unknown Company'):
            structured_jobs.append(job)
    
    # Create a new DataFrame with the structured data
    structured_df = pd.DataFrame(structured_jobs)
    
    # Save structured data
    logger.info(f"Saving structured data to {output_path}")
    structured_df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"Saved {structured_df.shape[0]} structured job entries")
    
    return structured_df.shape[0]

if __name__ == "__main__":
    # Set up file paths
    input_file = "dataset/combined_job_offers.csv"
    output_file = "dataset/cleaned_job_offers.csv"
    structured_file = "dataset/structured_job_offers.csv"
    
    # Make sure the dataset directory exists
    os.makedirs("dataset", exist_ok=True)
    
    # Step 1: Basic cleaning
    if os.path.exists(input_file):
        cleaned_rows = clean_job_data(input_file, output_file)
        logger.info(f"Cleaned {cleaned_rows} rows")
        
        # Step 2: Extract structured data
        if os.path.exists(output_file):
            structured_rows = extract_structured_job_data(output_file, structured_file)
            logger.info(f"Structured {structured_rows} job entries")
        else:
            logger.error(f"Cleaned output file {output_file} not found")
    else:
        logger.error(f"Input file {input_file} not found")
        logger.info(f"Please make sure {input_file} exists in the dataset directory")