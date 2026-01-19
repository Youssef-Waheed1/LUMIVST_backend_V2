import os
import sys
import pandas as pd
import json

def parse_xbrl_file(file_path):
    """
    Parses a single XBRL Excel file and returns a dictionary of metrics.
    Assumes standard Tadawul XBRL format.
    """
    try:
        # Tadawul XBRL files usually have data in the first sheet
        # Metrics are often in column A, values in column B/C/D depending on period
        # This logic will need REFINEMENT based on examining the actual file content printed earlier
        
        df = pd.read_excel(file_path)
        
        # Simple extraction strategy:
        # Convert to dictionary { "Metric Name": Value }
        # We need to identify which column holds the values. 
        # Usually 'Current Period' values are what we want.
        
        # Let's clean the dataframe first
        df = df.dropna(how='all') # Drop empty rows
        
        data = {}
        
        df = df.dropna(how='all') # Drop empty rows
        
        print(f"\n--- FILE: {os.path.basename(file_path)} ---")
        print(f"Columns: {df.columns.tolist()}")
        print(df.head(10).to_string())
        print("-------------------------------------------\n")

        return {"status": "inspected"}

    except Exception as e:
        return {"status": "error", "error": str(e), "path": file_path}

def process_company_xbrl(symbol):
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "downloads", symbol)
    
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found for {symbol}")
        return

    print(f"🔍 Scanning {data_dir} for cleaned XLS files...")
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.xls') or f.endswith('.xlsx')]
    
    results = []
    
    for file in files:
        if "XBRL" not in file:
            continue
            
        full_path = os.path.join(data_dir, file)
        print(f"📊 Parsing {file}...")
        
        metrics = parse_xbrl_file(full_path)
        results.append(metrics)
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/parse_xbrl_data.py <SYMBOL>")
    else:
        process_company_xbrl(sys.argv[1])
