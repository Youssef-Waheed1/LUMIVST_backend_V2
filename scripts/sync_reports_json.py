import json
import os
import argparse
from pathlib import Path

def sync_reports(json_path: str, downloads_root: str, symbol: str = None):
    """
    Syncs the scrape_financial_reports.json file with actual files on disk.
    If a file exists on disk but is missing in JSON, it updates the JSON entry.
    """
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"❌ Error: JSON file not found at {json_path}")
        return

    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return

    updated_count = 0
    
    # Iterate through categories (Financial Statements, XBRL, ...)
    for category, records in data.items():
        print(f"\n🔍 Checking {category}...")
        
        for record in records:
            # Skip if already valid
            if record.get('local_path') and os.path.exists(record['local_path']):
                continue

            # Check logic based on expected file pattern if local_path is missing or invalid
            # We assume a standard naming convention based on scraping logs:
            # "{year}_{file_type}_{period}.{ext}" e.g., "2022_XBRL_Q2.xls"
            
            year = record.get('year')
            period = record.get('period')
            
            if not year or not period:
                continue

            # Construct expected filename patterns to search for
            # 1. Standard pattern from scraper
            file_type_map = {
                "XBRL": "XBRL",
                "Financial Statements": "Financial_Statements",
                "Board Report": "Board_Report", 
                "ESG Report": "ESG_Report"
            }
            
            cat_prefix = file_type_map.get(category, category)
            
            # Extensions to check
            extensions = ['.pdf', '.xls', '.xlsx']
            
            # If symbol provided, check only that folder, otherwise would need logic to iterate all folders
            # Since the current JSON seems to be PER SYMBOL (from the example 1201), we assume single company JSON
            # However, looking at the JSON structure provided, it doesn't explicitly Key by symbol at root.
            # But the 'local_path' examples show `.../downloads/1201/...`
            # So if symbol arg is not provided, we try to infer from existing paths or scan all subdirs
            
            target_symbol = symbol
            if not target_symbol:
                # Try to infer from first valid record
                for r in records:
                    if r.get('local_path'):
                        parts = Path(r['local_path']).parts
                        if 'downloads' in parts:
                            idx = parts.index('downloads')
                            if idx + 1 < len(parts):
                                target_symbol = parts[idx+1]
                                break
                if not target_symbol:
                    # Default/Fallback if completely empty JSON or new
                    print("⚠️ Could not infer symbol from JSON. Please provide --symbol argument.")
                    continue

            company_dir = Path(downloads_root) / str(target_symbol)
            if not company_dir.exists():
                print(f"⚠️ Directory not found for symbol {target_symbol}: {company_dir}")
                continue

            # Search in directory for matching file
            found_file = None
            
            # Pattern 1: Exact match expected by scraper e.g. "2022_XBRL_Q2.xls"
            expected_name_base = f"{year}_{cat_prefix}_{period}"
            
            # Try finding a file that starts with this pattern (ignoring case potentially)
            for file_path in company_dir.iterdir():
                if file_path.is_file() and file_path.stem.lower() == expected_name_base.lower():
                    found_file = file_path
                    break
            
            # If found, update JSON
            if found_file:
                # Update record
                old_status = "Pending/Failed" if not record.get('local_path') else "Broken Link"
                
                record['local_path'] = str(found_file.absolute())
                record['file_type'] = 'excel' if found_file.suffix.lower() in ['.xls', '.xlsx'] else 'pdf'
                # If URL is null, we can't really fix it, but at least we have the file
                
                print(f"   ✅ Fixed: {year} {period} -> Found {found_file.name}")
                updated_count += 1

    if updated_count > 0:
        # Save updates
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"\n💾 Successfully synced {updated_count} files to JSON.")
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
    else:
        print("\n✨ No missing files found on disk to sync. JSON is up to date with disk content.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync scrape_financial_reports.json with actual disk files.")
    parser.add_argument("--json", default=r"D:\Work\LUMIVST\backend\data\scrape_financial_reports.json", help="Path to JSON file")
    parser.add_argument("--root", default=r"D:\Work\LUMIVST\backend\data\downloads", help="Root downloads directory")
    parser.add_argument("--symbol", help="Target company symbol (e.g. 8070)")
    
    args = parser.parse_args()
    
    sync_reports(args.json, args.root, args.symbol)
