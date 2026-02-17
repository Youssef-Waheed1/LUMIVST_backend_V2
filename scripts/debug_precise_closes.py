"""
debug_precise_closes.py
Print exact closes with full precision
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.database import SessionLocal
from sqlalchemy import text
from scripts.calculate_rsi_indicators import convert_to_float


def fetch_prices(db, symbol: str, target_date: date):
    query = text("""
        SELECT date, open, high, low, close
        FROM prices
        WHERE symbol = :symbol AND date <= :target_date
        ORDER BY date ASC
    """)
    rows = db.execute(query, {"symbol": symbol, "target_date": target_date}).fetchall()
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
    return df


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/debug_precise_closes.py SYMBOL YYYY-MM-DD")
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

        df = make_df(rows)
        if df is None or df.empty:
            print("Not enough data")
            return

        print("\n" + "="*80)
        print(f"LAST 15 DAILY CLOSES (Full Precision)")
        print("="*80)
        for idx, (date_val, row) in enumerate(df.tail(15).iterrows(), 1):
            print(f"{idx:2d}. {date_val.date()}: {row['close']:.10f}")

        # Resample to weekly
        df_w = df.resample('W-THU').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        print("\n" + "="*80)
        print(f"LAST 10 WEEKLY CLOSES (Full Precision)")
        print("="*80)
        for idx, (date_val, row) in enumerate(df_w.tail(10).iterrows(), 1):
            print(f"{idx:2d}. {date_val.date()}: {row['close']:.10f}")

        print("\n" + "="*80)
        print("LAST 5 WEEKLY BARS (Full Details)")
        print("="*80)
        for idx, (date_val, row) in enumerate(df_w.tail(5).iterrows(), 1):
            print(f"\nWeek {idx}: {date_val.date()}")
            print(f"  O: {row['open']:.10f}")
            print(f"  H: {row['high']:.10f}")
            print(f"  L: {row['low']:.10f}")
            print(f"  C: {row['close']:.10f}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
