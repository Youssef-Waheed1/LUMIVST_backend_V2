"""
test_weekly_boundaries.py
Test different weekly boundaries to find which one matches TradingView RSI value
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
    # Round close to 1 decimal
    df['close'] = df['close'].apply(lambda x: round(x, 1) if not pd.isna(x) else x)
    return df


def test_resample(df, period_str, target_date):
    """Test a specific resample period and return the RSI value"""
    try:
        df_w = df.resample(period_str).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        closes_w = df_w['close'].tolist()
        rsi_w = calculate_rsi_pinescript(closes_w, 14)
        
        # Get the RSI for the last available week before/on target_date
        df_w_app = df_w[df_w.index.to_pydatetime() <= pd.to_datetime(target_date)]
        if not df_w_app.empty:
            idx = len(df_w) - len(df_w_app) + len(df_w_app) - 1
            last_rsi = rsi_w[idx] if idx < len(rsi_w) else rsi_w[-1]
            return {
                'period': period_str,
                'candles': len(df_w),
                'rsi': last_rsi,
                'last_close': closes_w[-1] if closes_w else None,
            }
    except Exception as e:
        return {'period': period_str, 'error': str(e)}


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_weekly_boundaries.py SYMBOL YYYY-MM-DD")
        sys.exit(1)

    symbol = sys.argv[1]
    try:
        target_date = date.fromisoformat(sys.argv[2])
    except Exception:
        print("Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    expected_rsi = 61.38  # From TradingView

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
        print(f"TESTING WEEKLY BOUNDARIES FOR {symbol} on {target_date}")
        print("="*80)
        print(f"Expected RSI from TradingView: {expected_rsi}\n")

        # Test different weekly boundaries
        boundaries = [
            'W-MON',  # Monday-Sunday
            'W-TUE',  # Tuesday-Monday
            'W-WED',  # Wednesday-Tuesday
            'W-THU',  # Thursday-Wednesday (current)
            'W-FRI',  # Friday-Thursday
            'W-SAT',  # Saturday-Friday
            'W-SUN',  # Sunday-Saturday (default)
            'W',      # Same as W-SUN
        ]

        results = []
        for boundary in boundaries:
            result = test_resample(df, boundary, target_date)
            results.append(result)
            if 'error' not in result:
                diff = result['rsi'] - expected_rsi if result['rsi'] else float('inf')
                print(f"{boundary:8s}: RSI={result['rsi']:.2f if result['rsi'] else 'N/A':>8s}  "
                      f"Diff={diff:+.2f}  Candles={result['candles']}")
            else:
                print(f"{boundary:8s}: ERROR - {result['error']}")

        # Find closest match
        print("\n" + "="*80)
        valid_results = [r for r in results if 'error' not in r and r['rsi']]
        if valid_results:
            closest = min(valid_results, key=lambda x: abs(x['rsi'] - expected_rsi))
            diff = abs(closest['rsi'] - expected_rsi)
            print(f"Closest match: {closest['period']:8s} with RSI={closest['rsi']:.2f} (diff={diff:.2f})")

    finally:
        db.close()


if __name__ == '__main__':
    main()
