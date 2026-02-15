
import csv
from pathlib import Path

def test_csv_loading():
    # Simulate path resolution as it is in the backend/app/api/routes/prices.py
    # backend/app/api/routes/prices.py -> .parent.parent.parent.parent -> backend/
    
    # But here we are in backend/scripts/
    # so .parent -> backend/
    
    base_dir = Path(__file__).resolve().parent.parent
    csv_path = base_dir / "company_symbols.csv"
    
    print(f"Looking for CSV at: {csv_path}")
    
    if not csv_path.exists():
        print("❌ CSV File not found!")
        return

    tv_mapping = {}
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Print headers to verify
            print(f"headers: {reader.fieldnames}")
            
            count = 0
            for row in reader:
                sym = str(row.get('Symbol', '')).strip()
                tv_sym = str(row.get('symbol on tradingView', '')).strip()
                if sym and tv_sym:
                    tv_mapping[sym] = tv_sym
                    count += 1
                    if count <= 5:
                        print(f"Sample: {sym} -> {tv_sym}")
            
            print(f"✅ Loaded {len(tv_mapping)} symbols.")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")

if __name__ == "__main__":
    test_csv_loading()
