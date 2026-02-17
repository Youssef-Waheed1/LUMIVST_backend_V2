"""
debug_week_feb05.py
Print detailed RSI and indicators for week 2026-02-05 specifically
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
from scripts.calculate_rsi_indicators import calculate_rsi_pinescript, calculate_sma, convert_to_float


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
    symbol = "1321"
    target_date = date(2026, 2, 5)  # ده الأسبوع الي في الصورة

    db = SessionLocal()
    try:
        rows = fetch_prices(db, symbol, target_date)
        if not rows:
            print(f"No price rows found")
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

        print("\n" + "="*80)
        print(f"ANALYSIS FOR WEEK ENDING 2026-02-05 (The one in the screenshot)")
        print("="*80)

        # Show the week
        print(f"\nWeekly candle for 2026-02-05:")
        week_row = df_w.loc[pd.Timestamp('2026-02-05')]
        print(f"  O: {week_row['open']:.2f}")
        print(f"  H: {week_row['high']:.2f}")
        print(f"  L: {week_row['low']:.2f}")
        print(f"  C: {week_row['close']:.2f}")

        # Calculate all indicators
        closes_w = df_w['close'].tolist()
        rsi_w = calculate_rsi_pinescript(closes_w, 14)
        rsi_3_w = calculate_rsi_pinescript(closes_w, 3)
        sma9_rsi_w = calculate_sma(rsi_w, 9)
        wma45_rsi_w = calculate_sma(rsi_w, 45)  # Using SMA instead of WMA for simplicity

        # Find index of 2026-02-05
        idx_date = list(df_w.index).index(pd.Timestamp('2026-02-05'))

        print(f"\nIndicator values for week ending 2026-02-05:")
        print(f"  RSI(14):       {rsi_w[idx_date]:.2f}")
        print(f"  RSI(3):        {rsi_3_w[idx_date]:.2f}")
        if sma9_rsi_w[idx_date]:
            print(f"  SMA9(RSI):     {sma9_rsi_w[idx_date]:.2f}")
        if wma45_rsi_w[idx_date]:
            print(f"  WMA45(RSI):    {wma45_rsi_w[idx_date]:.2f}")

        print(f"\n" + "="*80)
        print("COMPARISON WITH SCREENSHOT:")
        print("="*80)
        print(f"Screenshot shows: RS Score: 182.57")
        print(f"Python RSI(14): {rsi_w[idx_date]:.2f}")
        print(f"\nNote: 'RS Score' might be different from RSI!")
        print(f"It could be scaled differently or calculated differently")

    finally:
        db.close()


if __name__ == '__main__':
    main()
