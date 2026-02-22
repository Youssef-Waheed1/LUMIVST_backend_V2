import requests
import json
import sys
import os

# API Configuration
API_URL = "http://localhost:8000/api/ingest/official-reports"
# Determine absolute path to data file
script_dir = os.path.dirname(os.path.abspath(__file__))
# Assumes script is in backend/scripts, so we go .. -> data
JSON_FILE_PATH = os.path.join(script_dir, "..", "data", "scrape_financial_reports.json")

def ingest_data(symbol, language='en'):
    print(f"📂 Reading data from {JSON_FILE_PATH}...")
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ File {JSON_FILE_PATH} not found. Please run the scraper first.")
        return

    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)

    payload = {
        "symbol": str(symbol),
        "language": language,
        "data": scraped_data
    }
    
    lang_label = "العربية" if language == 'ar' else "English"
    print(f"🚀 Sending data to API for Symbol: {symbol} (Language: {lang_label})...")
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        print("✅ Success! Server Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        print("\n⏳ The server is now downloading files in the background. Check your S3 bucket/Database in a few seconds.")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response is not None:
            print(f"Details: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Ingest scraped reports JSON via API')
    parser.add_argument('symbol', type=str, help='Company Symbol', nargs='?') # Positional for backward compatibility
    parser.add_argument('--symbol', dest='flag_symbol', type=str, help='Company Symbol')
    parser.add_argument('lang', type=str, help='Language (en/ar)', nargs='?') # Positional for backward compatibility
    parser.add_argument('--lang', dest='flag_lang', type=str, choices=['en', 'ar'], help='Language (en/ar)')
    
    args = parser.parse_args()
    
    final_symbol = args.flag_symbol or args.symbol
    final_lang = args.flag_lang or args.lang or 'en'

    if not final_symbol:
        print("⚠️  Usage: python scripts/ingest_reports.py <SYMBOL> [--lang ar]")
        sys.exit(1)
        
    ingest_data(final_symbol, language=final_lang)
