"""
test_rsi_starting_point.py
اختبر RSI مع نقاط بداية مختلفة
"""

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
        print("Usage: python scripts/test_rsi_starting_point.py SYMBOL YYYY-MM-DD")
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

        # Resample to weekly
        df_w = df.resample('W-THU').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        closes_w = df_w['close'].tolist()

        print("\n" + "="*80)
        print(f"RSI CALCULATION WITH DIFFERENT STARTING POINTS")
        print("="*80)
        print(f"Total weekly candles: {len(closes_w)}")
        print(f"Last 10 weekly closes: {closes_w[-10:]}")

        # Test with full dataset
        print(f"\n1. CURRENT (using all {len(closes_w)} candles):")
        rsi_full = calculate_rsi_pinescript(closes_w, 14)
        print(f"   Last RSI: {rsi_full[-1]:.2f}")

        # Test with last 200 candles
        max_lookback = min(200, len(closes_w))
        print(f"\n2. Using last {max_lookback} candles:")
        rsi_200 = calculate_rsi_pinescript(closes_w[-max_lookback:], 14)
        print(f"   Last RSI: {rsi_200[-1]:.2f}")

        # Test with last 100 candles
        max_lookback = min(100, len(closes_w))
        print(f"\n3. Using last {max_lookback} candles:")
        rsi_100 = calculate_rsi_pinescript(closes_w[-max_lookback:], 14)
        print(f"   Last RSI: {rsi_100[-1]:.2f}")

        # Test with different periods starting from different weeks backwards
        print(f"\n4. Using progressively FEWER leading candles (trim first N):")
        for trim_count in [10, 20, 30, 40, 50]:
            if trim_count < len(closes_w):
                trimmed_closes = closes_w[trim_count:]
                rsi_trimmed = calculate_rsi_pinescript(trimmed_closes, 14)
                print(f"   Skip first {trim_count:2d} candles (start from week {trim_count}): RSI={rsi_trimmed[-1]:.2f}")

        print(f"\n" + "="*80)
        print(f"Expected (TradingView): 61.38")
        print(f"Closest match so far: {rsi_full[-1]:.2f} (current implementation)")

    finally:
        db.close()


if __name__ == '__main__':
    main()
