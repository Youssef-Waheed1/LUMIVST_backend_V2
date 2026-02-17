"""
debug_weekly_unrounded.py
Same as debug_weekly but WITHOUT rounding closes before RSI calculation
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use minimal imports first to diagnose import issue
try:
    from app.core.database import SessionLocal
    from sqlalchemy import text
    from scripts.calculate_rsi_indicators import calculate_rsi_pinescript, convert_to_float
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def fetch_prices(db, symbol: str, target_date: date):
    query = text("""
        SELECT date, open, high, low, close
        FROM prices
        WHERE symbol = :symbol AND date <= :target_date
        ORDER BY date ASC
    """)
    rows = db.execute(query, {"symbol": symbol, "target_date": target_date}).fetchall()
    return rows


def make_df(rows, round_closes=True):
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].apply(convert_to_float)
    df.dropna(subset=['close'], inplace=True)
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    
    # Optional rounding
    if round_closes:
        df['close'] = df['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    
    return df


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/debug_weekly_unrounded.py SYMBOL YYYY-MM-DD")
        sys.exit(1)

    symbol = sys.argv[1]
    try:
        target_date = date.fromisoformat(sys.argv[2])
    except Exception:
        print("Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    db = SessionLocal()
    try:
        rows = fetch_prices(db, symbol, target_date)
        if not rows:
            print(f"No price rows found for {symbol} up to {target_date}")
            return

        print("\n" + "="*80)
        print(f"COMPARING ROUNDED vs UNROUNDED CLOSES FOR {symbol} on {target_date}")
        print("="*80)

        # Test BOTH rounded and unrounded
        for round_flag in [True, False]:
            mode = "ROUNDED" if round_flag else "UNROUNDED"
            
            df = make_df(rows, round_closes=round_flag)
            if df is None or df.empty:
                print(f"Not enough data ({mode})")
                continue

            # Resample to weekly
            df_w = df.resample('W-THU').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).dropna()

            closes_w = df_w['close'].tolist()
            rsi_w = calculate_rsi_pinescript(closes_w, 14)

            # Calculate SMA9 of RSI
            sma9_rsi_w = []
            for i in range(len(rsi_w)):
                if i < 8:
                    sma9_rsi_w.append(None)
                else:
                    window = [x for x in rsi_w[i-8:i+1] if x is not None]
                    if len(window) == 9:
                        sma9_rsi_w.append(sum(window) / 9)
                    else:
                        sma9_rsi_w.append(None)

            print(f"\n{'='*40}")
            print(f"MODE: {mode}")
            print(f"{'='*40}")
            print(f"Last 5 weekly closes: {closes_w[-5:]}")
            print(f"RSI(14) Weekly:       {rsi_w[-1]:.2f}")
            print(f"SMA9(RSI) Weekly:     {sma9_rsi_w[-1]:.2f if sma9_rsi_w[-1] else 'N/A'}")

        # Expected values
        print(f"\n{'='*40}")
        print("EXPECTED (from TradingView):")
        print(f"{'='*40}")
        print(f"RSI(14) Weekly:       61.38")
        print(f"SMA9(RSI) Weekly:     57.62")

    finally:
        db.close()


if __name__ == '__main__':
    main()
