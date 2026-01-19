import subprocess
import sys
import time
import os

# List of symbols to process
SYMBOLS = ['4250', '4300', '4310', '4320', '4321', '4322', '4323', '4324', '4325', '4326', '4327']

# Paths to scripts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAN_SCRIPT = os.path.join(BASE_DIR, "clean_company_reports.py")
GENERATE_JSON_SCRIPT = os.path.join(BASE_DIR, "generate_json_from_local.py")
INGEST_SCRIPT = os.path.join(BASE_DIR, "ingest_reports.py")

# Python interpreter
PYTHON_EXE = sys.executable

def run_command(command, description):
    print(f"🔄 Running: {description}...")
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=False)
        print(f"✅ {description} completed successfully.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        return False

def process_symbol(symbol):
    print(f"\n{'='*40}")
    print(f"🚀 Processing Symbol: {symbol}")
    print(f"{'='*40}")
    
    # 1. Clean Company Reports (Force delete Excel only)
    cmd_clean = [PYTHON_EXE, CLEAN_SCRIPT, symbol, '--excel-only', '--force']
    if not run_command(cmd_clean, f"Clean Excel reports for {symbol}"):
        return

    # 2. Generate JSON from Local Files (Reconstruct metadata)
    cmd_gen = [PYTHON_EXE, GENERATE_JSON_SCRIPT, symbol]
    if not run_command(cmd_gen, f"Generate JSON for {symbol}"):
        return

    # 3. Ingest Reports (Upload correct files)
    cmd_ingest = [PYTHON_EXE, INGEST_SCRIPT, symbol]
    if not run_command(cmd_ingest, f"Ingest reports for {symbol}"):
        return

    print(f"🎉 Fully processed {symbol}!")

if __name__ == "__main__":
    print(f"📋 Batch processing for symbols: {SYMBOLS}")
    print("⚠️  Ensure your backend server is running for the Ingest step!")
    
    # Small delay to let user read warning
    time.sleep(2)
    
    for symbol in SYMBOLS:
        process_symbol(symbol)
        
    print("\n✅✅✅ All symbols processed! ✅✅✅")
