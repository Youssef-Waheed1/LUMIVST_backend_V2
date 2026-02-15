"""
Create a comprehensive comparison report of parameters across all companies
"""

import json
import csv
from pathlib import Path
from collections import defaultdict

# Load the detailed data
data_dir = Path("d:/Work/LUMIVST/backend/parameters_analysis")
companies_data_path = data_dir / "companies_detailed_data.json"

with open(companies_data_path, 'r', encoding='utf-8') as f:
    companies_data = json.load(f)

# Create comprehensive reports
print("Creating comprehensive comparison reports...")

# Report 1: All parameters by company (wide format for easy comparison)
output_csv_path = data_dir / "companies_parameters_comparison.csv"

# Collect all unique columns
all_columns = set()
for company_code, company_data in companies_data.items():
    for sheet_name, sheet_data in company_data["data_structure"].items():
        all_columns.update(sheet_data["columns"])

all_columns = sorted(list(all_columns))

# Write CSV with wide format (companies as rows, columns as columns)
with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    # Header
    header = ["Company_Code", "File_Name", "Column_Count"] + all_columns
    writer.writerow(header)
    
    # Data rows
    for company_code in sorted(companies_data.keys()):
        company_data = companies_data[company_code]
        sheet_data = company_data["data_structure"].get("Sheet0", {})
        
        row = [
            company_code,
            company_data["file_name"],
            len(sheet_data.get("columns", []))
        ]
        
        # Add presence of each column (X for present, empty for missing)
        company_columns = set(sheet_data.get("columns", []))
        for col in all_columns:
            row.append("X" if col in company_columns else "")
        
        writer.writerow(row)

print(f"Saved parameters comparison CSV: {output_csv_path}")

# Report 2: Group companies by column count pattern
group_by_column_count = defaultdict(list)
for company_code, company_data in companies_data.items():
    sheet_data = company_data["data_structure"].get("Sheet0", {})
    col_count = len(sheet_data.get("columns", []))
    group_by_column_count[col_count].append({
        "company_code": company_code,
        "file_name": company_data["file_name"],
        "columns": sheet_data.get("columns", [])
    })

# Save grouping report
grouping_report_path = data_dir / "companies_grouped_by_column_count.json"
with open(grouping_report_path, 'w', encoding='utf-8') as f:
    output_data = {}
    for col_count in sorted(group_by_column_count.keys()):
        companies = group_by_column_count[col_count]
        output_data[f"Column_Count_{col_count}"] = {
            "total_companies": len(companies),
            "companies": [c["company_code"] for c in companies]
        }
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"Saved grouping report: {grouping_report_path}")

# Report 3: Detailed parameters list by company
detailed_report_path = data_dir / "companies_parameters_detailed.json"
detailed_output = {}
for company_code in sorted(companies_data.keys()):
    company_data = companies_data[company_code]
    sheet_data = company_data["data_structure"].get("Sheet0", {})
    
    detailed_output[company_code] = {
        "file_name": company_data["file_name"],
        "columns": sheet_data.get("columns", []),
        "column_count": len(sheet_data.get("columns", [])),
        "data_types": sheet_data.get("dtypes", {})
    }

with open(detailed_report_path, 'w', encoding='utf-8') as f:
    json.dump(detailed_output, f, ensure_ascii=False, indent=2)

print(f"Saved detailed parameters report: {detailed_report_path}")

# Report 4: Statistics summary
stats_report_path = data_dir / "parameters_statistics.json"
column_frequency = defaultdict(int)
for company_code, company_data in companies_data.items():
    sheet_data = company_data["data_structure"].get("Sheet0", {})
    for col in sheet_data.get("columns", []):
        column_frequency[col] += 1

stats_output = {
    "total_companies_analyzed": len(companies_data),
    "total_unique_parameters": len(all_columns),
    "column_count_distribution": dict(sorted(group_by_column_count.items(), key=lambda x: x[0])),
    "parameter_frequency": {
        "most_common": sorted(column_frequency.items(), key=lambda x: x[1], reverse=True)[:20],
        "least_common": sorted(column_frequency.items(), key=lambda x: x[1])[:20]
    },
    "all_parameters": sorted(all_columns)
}

with open(stats_report_path, 'w', encoding='utf-8') as f:
    json.dump(stats_output, f, ensure_ascii=False, indent=2)

print(f"Saved statistics report: {stats_report_path}")

print("\n" + "=" * 80)
print("All reports generated successfully!")
print("=" * 80)
print(f"\nReports location: {data_dir}")
print("\nGenerated files:")
print(f"  1. companies_parameters_comparison.csv - Easy comparison of all parameters")
print(f"  2. companies_grouped_by_column_count.json - Companies grouped by column count")
print(f"  3. companies_parameters_detailed.json - Detailed parameters per company")
print(f"  4. parameters_statistics.json - Statistics and frequency analysis")
