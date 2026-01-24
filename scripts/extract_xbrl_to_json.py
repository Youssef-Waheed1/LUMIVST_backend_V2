import os
import sys
import pandas as pd
import json
import asyncio
import boto3
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = "lumivst-reports" # Or whatever bucket name

def clean_key(text):
    if not isinstance(text, str): return f"unknown_{text}"
    # Remove brackets, trim, lowercase, replace spaces with underscore
    text = text.split('[')[0] # Remove [abstract] etc
    text = text.split('|')[0] # Remove | ISIN code
    clean = "".join(c if c.isalnum() else "_" for c in text)
    clean = clean.lower().strip("_")
    while "__" in clean: clean = clean.replace("__", "_")
    return clean

def parse_excel_file(file_path):
    """Parses a single XBRL Excel file and returns a LIST of metrics to preserve order and duplicates."""
    try:
        # Read Excel - Column 0 is Label, Column 1 is Current Value
        # fillna('') ensures we don't drop empty cells immediately
        df = pd.read_excel(file_path, header=None).fillna('')
        
        data = []
        
        for index, row in df.iterrows():
            label = str(row[0]).strip()
            raw_value = row[1]
            
            # Skip completely empty rows (if both label and value are empty)
            if not label and (raw_value == '' or pd.isna(raw_value)):
                continue
            
            # Generate key for reference, but we won't use it for uniqueness
            key = clean_key(label)
            
            # Value handling
            val = None
            if raw_value is not None and raw_value != '':
                try:
                    val = float(raw_value)
                except:
                    val = str(raw_value).strip()
            
            # Append everything, even if val is None
            data.append({
                "row_id": index + 1,       # Preserve Excel row number
                "key": key,                # Snake_case key for searching
                "label": label,            # Original Display Label
                "value": val               # The value (or None)
            })
            
        return data
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return []

def extract_for_symbol(symbol):
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "downloads", str(symbol))
    
    if not os.path.exists(base_dir):
        print(f"⚠️ No downloads found for {symbol}")
        return None

    all_financials = {}

    print(f"📂 Processing {symbol}...")
    
    files = [f for f in os.listdir(base_dir) if f.endswith('.xls') or f.endswith('.xlsx')]
    
    for filename in files:
        if "XBRL" not in filename: continue # Focus on XBRL files
        
        # Parse info from filename: 2024_XBRL_Annual.xls
        parts = os.path.splitext(filename)[0].split('_')
        year = parts[0]
        period = parts[-1]
        
        period_key = f"{year}_{period}" # e.g. 2024_Annual or 2025_Q3
        
        file_path = os.path.join(base_dir, filename)
        metrics = parse_excel_file(file_path)
        
        if metrics:
            all_financials[period_key] = metrics
            print(f"   ✅ Parsed {filename} -> {len(metrics)} metrics")

    return all_financials

async def upload_json_to_r2(symbol, data):
    if not data: return
    
    session = boto3.session.Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
    
    # Save locally first
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", f"{symbol}_financials.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # Upload
    key = f"{symbol}/financials.json"
    print(f"☁️ Uploading to R2: {key}...")
    try:
        with open(json_path, "rb") as f:
            s3.upload_fileobj(f, S3_BUCKET_NAME, key, ExtraArgs={'ContentType': "application/json"})
        print(f"✅ Upload Complete: {S3_ENDPOINT}/{S3_BUCKET_NAME}/{key}")
    except Exception as e:
        print(f"❌ Upload Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_xbrl_to_json.py <SYMBOL>")
        sys.exit(1)
        
    symbol = sys.argv[1]
    data = extract_for_symbol(symbol)
    
    if data:
        asyncio.run(upload_json_to_r2(symbol, data))
    else:
        print("❌ No data extracted.")
