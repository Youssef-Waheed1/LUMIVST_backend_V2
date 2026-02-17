"""
verify_ohlc.py
Simple utility to fetch price rows for a symbol up to a target date,
compute weekly (W-THU) and monthly (month-end) OHLC aggregates,
round closes to 1 decimal (TradingView-like) and print the period values
and basic RSI(14) for daily and weekly closes for verification.

Usage:
  python scripts/verify_ohlc.py SYMBOL YYYY-MM-DD

Example:
  python scripts/verify_ohlc.py 1321 2026-02-12

This script uses the project's DB settings and SQLAlchemy `SessionLocal`.
"""

import sys
from datetime import date
import pandas as pd
import numpy as np

sys.path.insert(0, __file__.replace('/scripts/verify_ohlc.py','').replace('\\','/'))

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
from pathlib import Path


def make_df(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    df['open'] = df['open'].apply(convert_to_float)
    df['high'] = df['high'].apply(convert_to_float)
    df['low'] = df['low'].apply(convert_to_float)
    df['close'] = df['close'].apply(convert_to_float)
    df.dropna(subset=['close'], inplace=True)
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    # Round close to 1 decimal to match TradingView display
    df['close'] = df['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    return df


def resample_weekly(df):
    # W-THU to match project's weekly aggregation
    df_w = df.resample('W-THU').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    # Round weekly close as well
    df_w['close'] = df_w['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    return df_w


def resample_monthly(df):
    df_m = df.resample('M').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    df_m['close'] = df_m['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    return df_m


def print_period(label, row):
    if row is None:
        print(f"{label}: not available")
        return
    o = row['open']
    h = row['high']
    l = row['low']
    c = row['close']
    print(f"{label} -> O: {o}  H: {h}  L: {l}  C: {c}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/verify_ohlc.py SYMBOL YYYY-MM-DD")
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

        # Print last daily rows around target date
        print("\nLast daily rows (near target date):")
        print(df.tail(10).to_string())

        # Daily RSI(14)
        closes = df['close'].tolist()
        rsi_daily = calculate_rsi_pinescript(closes, 14)
        print(f"\nDaily RSI(14) last: {rsi_daily[-1] if rsi_daily else None}")

        # Weekly and monthly aggregates
        df_w = resample_weekly(df)
        df_m = resample_monthly(df)

        # Find the weekly/monthly period that contains target_date (last <= target_date)
        weekly_row = None
        if not df_w.empty:
            df_w_applicable = df_w[df_w.index.to_pydatetime() <= pd.to_datetime(target_date)]
            if not df_w_applicable.empty:
                weekly_row = df_w_applicable.iloc[-1]

        monthly_row = None
        if not df_m.empty:
            df_m_applicable = df_m[df_m.index.to_pydatetime() <= pd.to_datetime(target_date)]
            if not df_m_applicable.empty:
                monthly_row = df_m_applicable.iloc[-1]

        print('\nAggregated periods containing target date:')
        print_period('WEEKLY (W-THU)', weekly_row)
        print_period('MONTHLY (M)', monthly_row)

        # Weekly RSI
        closes_w = df_w['close'].tolist() if not df_w.empty else []
        rsi_weekly = calculate_rsi_pinescript(closes_w, 14) if closes_w else []
        print(f"\nWeekly RSI(14) last applicable: {rsi_weekly[-1] if rsi_weekly else None}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
