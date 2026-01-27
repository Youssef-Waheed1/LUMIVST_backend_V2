import os
import sys
import subprocess
from pathlib import Path

def process_all_downloads():
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    downloads_dir = os.path.join(backend_dir, "data", "downloads")
    
    # Scripts to run
    update_script = os.path.join(script_dir, "update_json_with_downloads.py")
    ingest_script = os.path.join(script_dir, "ingest_reports.py")
    
    if not os.path.exists(downloads_dir):
        print(f"❌ Downloads directory not found: {downloads_dir}")
        return

    # Get all subdirectories (symbols)
    symbols = [d for d in os.listdir(downloads_dir) if os.path.isdir(os.path.join(downloads_dir, d))]
    
    print(f"🚀 Found {len(symbols)} companies to process: {', '.join(symbols)}")
    print("="*60)
    
    for symbol in symbols:
        print(f"\n🔄 Processing Symbol: {symbol}")
        
        # 1. Run Update JSON
        print(f"   📋 [1/2] Updating JSON links...")
        try:
            subprocess.run([sys.executable, update_script, "--symbol", symbol], check=True)
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error updating JSON for {symbol}: {e}")
            continue
            
        # 2. Run Ingest
        print(f"   📤 [2/2] Ingesting to API...")
        try:
            subprocess.run([sys.executable, ingest_script, symbol], check=True)
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error ingesting {symbol}: {e}")
            continue
            
        print(f"   ✅ Completed {symbol}")
        print("-" * 40)

    print("\n🎉 All processing complete!")

if __name__ == "__main__":
    process_all_downloads()
