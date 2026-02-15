"""
Extract ONLY the actual parameter names from XBRL Excel files
"""

import os
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Data paths
DATA_DIR = Path("d:/Work/LUMIVST/backend/data/downloads")
OUTPUT_DIR = Path("d:/Work/LUMIVST/backend/parameters_analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_parameter_names(file_path):
    """
    Extract ONLY parameter names from column 0 of Excel file.
    """
    try:
        df = pd.read_excel(file_path, sheet_name=0, header=None, engine='xlrd')
        
        # Find first non-empty row (skip empty rows at start)
        first_data_row = 0
        for idx, row in df.iterrows():
            if row.notna().sum() > 0:
                first_data_row = idx
                break
        
        # Extract ONLY parameter names from column 0
        parameters = []
        for idx in range(first_data_row, len(df)):
            param_name = df.iloc[idx, 0]
            if pd.notna(param_name):
                param_name = str(param_name).strip()
                if param_name and len(param_name) > 2:
                    parameters.append(param_name)
        
        return parameters
    except Exception as e:
        return []

def main():
    print("=" * 80)
    print("Extracting Parameter Names from XBRL Files")
    print("=" * 80)
    
    companies_parameters = {}
    all_unique_parameters = set()
    parameter_frequency = defaultdict(int)
    
    # Get all company directories
    company_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir()])
    total_companies = len(company_dirs)
    
    print(f"\nProcessing {total_companies} companies...\n")
    
    for idx, company_dir in enumerate(company_dirs, 1):
        company_code = company_dir.name
        
        # Search for first XBRL file
        xls_files = list(company_dir.glob("*.xls")) + list(company_dir.glob("*.xlsx"))
        
        if not xls_files:
            continue
        
        # Take first file
        first_file = sorted(xls_files)[0]
        
        # Extract parameter names
        parameters = extract_parameter_names(first_file)
        
        if parameters:
            companies_parameters[company_code] = {
                "file_name": first_file.name,
                "parameters": parameters,
                "count": len(parameters)
            }
            
            # Track statistics
            for param in parameters:
                all_unique_parameters.add(param)
                parameter_frequency[param] += 1
        
        print(f"[{idx:3d}/{total_companies}] {company_code}: {len(parameters):4d} parameters")
    
    # Save companies with their parameters
    companies_path = OUTPUT_DIR / "companies_parameters_only.json"
    with open(companies_path, 'w', encoding='utf-8') as f:
        json.dump(companies_parameters, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to: {companies_path}")
    
    # Create statistics
    stats = {
        "total_companies": len(companies_parameters),
        "total_unique_parameters": len(all_unique_parameters),
        "all_parameters": sorted(list(all_unique_parameters)),
        "parameter_frequency": sorted(parameter_frequency.items(), key=lambda x: x[1], reverse=True)
    }
    
    stats_path = OUTPUT_DIR / "parameters_frequency.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Saved statistics to: {stats_path}")
    
    # Create CSV for easy comparison
    csv_path = OUTPUT_DIR / "parameters_per_company.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("Company_Code,File_Name,Parameter_Count,Parameters\n")
        for company_code in sorted(companies_parameters.keys()):
            data = companies_parameters[company_code]
            params_str = " | ".join(data["parameters"])
            f.write(f'{company_code},{data["file_name"]},{data["count"]},"{params_str}"\n')
    
    print(f"Saved CSV to: {csv_path}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Companies: {len(companies_parameters)}")
    print(f"Total Unique Parameters: {len(all_unique_parameters)}")
    print(f"\nTop 20 Most Common Parameters:")
    for i, (param, count) in enumerate(stats['parameter_frequency'][:20], 1):
        pct = (count / len(companies_parameters)) * 100
        print(f"  {i:2d}. {param[:60]:<60} ({count:3d} companies, {pct:5.1f}%)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
