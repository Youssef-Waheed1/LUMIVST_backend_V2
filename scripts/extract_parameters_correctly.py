"""
Correct extraction of parameters from XBRL Excel files for all companies
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Data paths
DATA_DIR = Path("d:/Work/LUMIVST/backend/data/downloads")
OUTPUT_DIR = Path("d:/Work/LUMIVST/backend/parameters_analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_parameters_from_xls(file_path, num_rows=10):
    """
    Extract parameters from Excel file correctly.
    - Skip empty rows at the beginning
    - Use column 0 as parameter names
    """
    try:
        xls = pd.ExcelFile(file_path)
        data_structure = {}
        
        for sheet_name in xls.sheet_names[:1]:  # First sheet only
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='xlrd')
            
            # Find first non-empty row (skip empty rows at start)
            first_data_row = 0
            for idx, row in df.iterrows():
                if row.notna().sum() > 0:
                    first_data_row = idx
                    break
            
            # Extract parameters from column 0 (first column)
            parameters = []
            for idx in range(first_data_row, min(first_data_row + num_rows, len(df))):
                param_name = df.iloc[idx, 0]
                if pd.notna(param_name):
                    param_name = str(param_name).strip()
                    if param_name and len(param_name) > 2:
                        parameters.append(param_name)
            
            # Get all unique column indices with data (ignoring Unnamed)
            all_values = []
            for idx in range(first_data_row, len(df)):
                row = df.iloc[idx]
                for col_idx, val in enumerate(row):
                    if pd.notna(val):
                        all_values.append(col_idx)
            
            unique_columns = sorted(list(set(all_values)))
            
            data_structure[sheet_name] = {
                "parameters": parameters,
                "parameters_count": len(parameters),
                "columns_with_data": unique_columns,
                "columns_count": len(unique_columns),
                "total_rows": len(df),
                "first_data_row": first_data_row
            }
        
        return data_structure
    except Exception as e:
        print(f"Error: {e}")
        return {}

def main():
    print("=" * 80)
    print("Extracting Parameters Correctly from XBRL Files")
    print("=" * 80)
    
    companies_data = {}
    company_files_info = []
    
    # Get all company directories
    company_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir()])
    total_companies = len(company_dirs)
    
    print(f"\nTotal companies detected: {total_companies}\n")
    
    for idx, company_dir in enumerate(company_dirs, 1):
        company_code = company_dir.name
        
        # Search for first XBRL file
        xls_files = list(company_dir.glob("*.xls")) + list(company_dir.glob("*.xlsx"))
        
        if not xls_files:
            print(f"[{idx:3d}] {company_code}: No XBRL files")
            continue
        
        # Take first file
        first_file = sorted(xls_files)[0]
        
        print(f"[{idx:3d}] {company_code}: {first_file.name}")
        
        # Extract data correctly
        data_structure = extract_parameters_from_xls(first_file)
        
        if data_structure:
            companies_data[company_code] = {
                "file_name": first_file.name,
                "file_path": str(first_file),
                "data_structure": data_structure
            }
            
            # Store file information
            company_files_info.append({
                "company_code": company_code,
                "file_name": first_file.name,
                "file_path": str(first_file),
                "parameters_count": data_structure.get("Sheet0", {}).get("parameters_count", 0),
                "columns_count": data_structure.get("Sheet0", {}).get("columns_count", 0)
            })
        
        # Print progress every 50 companies
        if idx % 50 == 0:
            print(f"  Progress: {idx} of {total_companies}\n")
    
    # Save corrected data
    companies_data_path = OUTPUT_DIR / "companies_parameters_corrected.json"
    with open(companies_data_path, 'w', encoding='utf-8') as f:
        json.dump(companies_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved corrected parameters to: {companies_data_path}")
    
    # Create parameter statistics
    all_parameters = set()
    parameter_frequency = defaultdict(int)
    
    for company_code, company_data in companies_data.items():
        sheet_data = company_data["data_structure"].get("Sheet0", {})
        parameters = sheet_data.get("parameters", [])
        for param in parameters:
            all_parameters.add(param)
            parameter_frequency[param] += 1
    
    stats = {
        "total_companies_analyzed": len(companies_data),
        "total_unique_parameters": len(all_parameters),
        "all_parameters": sorted(list(all_parameters)),
        "parameter_frequency": sorted(parameter_frequency.items(), key=lambda x: x[1], reverse=True)[:50]
    }
    
    stats_path = OUTPUT_DIR / "parameters_statistics_corrected.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Saved statistics to: {stats_path}")
    
    print("\n" + "=" * 80)
    print("Extraction completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
