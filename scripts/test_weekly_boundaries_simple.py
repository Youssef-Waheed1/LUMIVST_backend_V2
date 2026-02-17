"""
test_weekly_boundaries_simple.py
Test different weekly boundaries without complex imports
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import subprocess
import json
import tempfile

# Run debug_weekly.py with different boundaries by modifying it


def test_boundary(symbol: str, target_date: str, boundary: str):
    """Test a specific weekly boundary"""
    
    # Create a temporary script that tests one boundary
    script = f'''
import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.database import SessionLocal
from sqlalchemy import text
from scripts.calculate_rsi_indicators import calculate_rsi_pinescript, convert_to_float

def fetch_prices(db, symbol: str, target_date: date):
    query = text("""
        SELECT date, open, high, low, close
        FROM prices
        WHERE symbol = :symbol AND date <= :target_date
        ORDER BY date ASC
    """)
    rows = db.execute(query, {{"symbol": symbol, "target_date": target_date}}).fetchall()
    return rows

def make_df(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].apply(convert_to_float)
    df.dropna(subset=['close'], inplace=True)
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    df['close'] = df['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    return df

symbol = "{symbol}"
target_date = date.fromisoformat("{target_date}")
boundary = "{boundary}"

db = SessionLocal()
try:
    rows = fetch_prices(db, symbol, target_date)
    df = make_df(rows)
    df_w = df.resample(boundary).agg({{'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}}).dropna()
    closes_w = df_w['close'].tolist()
    rsi_w = calculate_rsi_pinescript(closes_w, 14)
    print(f"{{boundary}}|{{len(df_w)}}|{{rsi_w[-1] if rsi_w[-1] else 'None'}}")
finally:
    db.close()
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='.') as f:
        f.write(script)
        temp_file = f.name
    
    try:
        result = subprocess.run([sys.executable, temp_file], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"{boundary}|ERROR|{result.stderr.split(chr(10))[-2] if result.stderr else 'Unknown'}"
        return result.stdout.strip()
    finally:
        Path(temp_file).unlink()


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_weekly_boundaries_simple.py SYMBOL YYYY-MM-DD")
        sys.exit(1)

    symbol = sys.argv[1]
    target_date = sys.argv[2]
    expected_rsi = 61.38

    print("\n" + "="*80)
    print(f"TESTING WEEKLY BOUNDARIES FOR {symbol} on {target_date}")
    print("="*80)
    print(f"Expected RSI from TradingView: {expected_rsi}\n")

    boundaries = ['W-MON', 'W-TUE', 'W-WED', 'W-THU', 'W-FRI', 'W-SAT', 'W-SUN']
    
    results = []
    for boundary in boundaries:
        print(f"Testing {boundary}...", end=" ", flush=True)
        result = test_boundary(symbol, target_date, boundary)
        print(result)
        
        if '|ERROR|' not in result:
            parts = result.split('|')
            if len(parts) >= 3:
                try:
                    rsi_val = float(parts[2])
                    results.append((boundary, int(parts[1]), rsi_val))
                except:
                    pass

    print("\n" + "="*80)
    if results:
        results.sort(key=lambda x: abs(x[2] - expected_rsi))
        for boundary, candles, rsi in results:
            diff = rsi - expected_rsi
            print(f"{boundary}: RSI={rsi:.2f}  Diff={diff:+.2f}  Candles={candles}")
        print(f"\nClosest: {results[0][0]} with RSI={results[0][2]:.2f} (diff={results[0][2] - expected_rsi:+.2f})")


if __name__ == '__main__':
    main()
