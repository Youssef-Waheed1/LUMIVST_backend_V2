"""
debug_weekly.py
تطبع البيانات الأسبوعية والحسابات خطوة بخطوة للتحقق من الفترات والترتيب
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd
import numpy as np

# Ensure backend folder is on sys.path
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
    # Keep full precision - do NOT round, calculations need exact values
    return df


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/debug_weekly.py SYMBOL YYYY-MM-DD")
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
            print("Not enough data after cleaning")
            return

        print("\n" + "="*80)
        print(f"DEBUG WEEKLY DATA FOR {symbol} on {target_date}")
        print("="*80)

        # Print last 20 daily rows
        print("\n📊 Last 20 DAILY rows:")
        print(df.tail(20).to_string())
        
        # Check if data is sorted correctly
        print(f"\n✓ Data sorted ASC: {df.index.is_monotonic_increasing}")
        print(f"  First date: {df.index[0]}")
        print(f"  Last date: {df.index[-1]}")

        # Resample to weekly (W-THU: Sunday to Thursday)
        print("\n" + "="*80)
        print("WEEKLY RESAMPLE (W-THU: Sunday-Thursday)")
        print("="*80)
        
        df_w = df.resample('W-THU').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        print(f"\nTotal weekly candles: {len(df_w)}")
        print("\n📊 Last 10 WEEKLY candles:")
        print(df_w.tail(10).to_string())

        # Get weekly candle containing target_date
        df_w_applicable = df_w[df_w.index.to_pydatetime() <= pd.to_datetime(target_date)]
        if not df_w_applicable.empty:
            weekly_row = df_w_applicable.iloc[-1]
            weekly_date = df_w_applicable.index[-1]
            print(f"\n✓ Weekly candle for {target_date}:")
            print(f"  Week ending: {weekly_date.date()}")
            print(f"  O: {weekly_row['open']}  H: {weekly_row['high']}  L: {weekly_row['low']}  C: {weekly_row['close']}")

            # Show which daily bars are included in this weekly candle
            # W-THU groups from Sunday to Thursday
            week_start = weekly_date - pd.Timedelta(days=4)  # Go back 4 days from Thursday
            week_end = weekly_date
            daily_in_week = df[(df.index >= week_start) & (df.index <= week_end)]
            print(f"\n  Daily bars in this week ({week_start.date()} to {week_end.date()}):")
            for idx, row in daily_in_week.iterrows():
                print(f"    {idx.date()}: O={row['open']}  H={row['high']}  L={row['low']}  C={row['close']}")

        # Calculate RSI on weekly closes
        closes_w = df_w['close'].tolist()
        print(f"\n" + "="*80)
        print(f"RSI CALCULATION ON WEEKLY CLOSES")
        print("="*80)
        print(f"Total weekly closes for RSI: {len(closes_w)}")
        print(f"Last 20 weekly closes: {closes_w[-20:]}")

        rsi_w_series = calculate_rsi_pinescript(closes_w, 14)
        print(f"\nRSI(14) on weekly closes:")
        print(f"  Total RSI values: {len(rsi_w_series)}")
        print(f"  Last 10 RSI values: {[round(x, 2) if x else None for x in rsi_w_series[-10:]]}")
        print(f"  Last RSI value: {rsi_w_series[-1]}")

        # Calculate SMA9 of RSI
        sma9_rsi_w = []
        for i in range(len(rsi_w_series)):
            if i < 8:
                sma9_rsi_w.append(None)
            else:
                window = [x for x in rsi_w_series[i-8:i+1] if x is not None]
                if len(window) == 9:
                    sma9_rsi_w.append(sum(window) / 9)
                else:
                    sma9_rsi_w.append(None)

        print(f"\nSMA9(RSI) on weekly:")
        print(f"  Last 10 values: {[round(x, 2) if x else None for x in sma9_rsi_w[-10:]]}")
        print(f"  Last value: {sma9_rsi_w[-1]}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Date checked: {target_date}")
        print(f"RSI(14) Weekly: {rsi_w_series[-1]}")
        print(f"SMA9(RSI) Weekly: {sma9_rsi_w[-1]}")
        print(f"Expected (TradingView): RSI ~61.38, SMA9 ~57.62")

    finally:
        db.close()


if __name__ == '__main__':
    main()
