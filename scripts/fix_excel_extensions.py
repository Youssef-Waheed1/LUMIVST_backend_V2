import os
import json
import shutil

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
JSON_PATH = os.path.join(DATA_DIR, "scrape_financial_reports.json")

def detect_signature(file_path):
    """Detect if file is XLS (OLE) or XLSX (ZIP) based on magic numbers."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            
        # OLE Compound File (XLS) signature: D0 CF 11 E0 A1 B1 1A E1
        if header.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
            return 'xls'
        
        # ZIP archive (XLSX) signature: 50 4B 03 04
        if header.startswith(b'\x50\x4B\x03\x04'):
            return 'xlsx'
            
        return 'unknown'
    except Exception:
        return 'error'

def fix_extensions():
    print(f"🔍 Scanning {DOWNLOADS_DIR} for mismatched extensions...")
    
    renamed_map = {} # old_path -> new_path
    
    # 1. Scan and Rename Files
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for file in files:
            if not file.lower().endswith('.xlsx'):
                continue
                
            full_path = os.path.join(root, file)
            real_type = detect_signature(full_path)
            
            if real_type == 'xls':
                new_name = file[:-4] + 'xls'
                new_path = os.path.join(root, new_name)
                
                try:
                    os.rename(full_path, new_path)
                    print(f"  ✅ Renamed: {file} -> {new_name} (It was actually an XLS file)")
                    renamed_map[full_path] = new_path
                except OSError as e:
                    print(f"  ❌ Failed to rename {file}: {e}")
            elif real_type == 'unknown':
                print(f"  ⚠️ Unknown format for: {file}")

    if not renamed_map:
        print("🎉 No extension mismatches found.")
        return

    # 2. Update JSON
    print(f"\n📝 Updating {JSON_PATH}...")
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        updated_count = 0
        for category, items in data.items():
            for item in items:
                local_path = item.get('local_path')
                if local_path and local_path in renamed_map:
                    item['local_path'] = renamed_map[local_path]
                    
                    # Also update url/filename in local_path if needed logic not required here 
                    # as ingestion uses the actual file content/mime detection usually
                    
                    # Update file_type field metadata if present
                    item['file_type'] = 'excel' # generic, but good to ensure
                    
                    updated_count += 1

        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Updated {updated_count} entries in JSON file.")
        
    except Exception as e:
        print(f"❌ Failed to update JSON: {e}")

if __name__ == "__main__":
    fix_extensions()
