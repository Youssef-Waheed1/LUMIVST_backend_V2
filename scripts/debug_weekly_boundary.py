"""
debug_weekly_boundary.py
تفاصيل دقيقة عن أي أيام تُدخل في كل أسبوع
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
        print("Usage: python scripts/debug_weekly_boundary.py SYMBOL YYYY-MM-DD")
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
        print(f"WEEKLY BOUNDARY ANALYSIS FOR {symbol}")
        print("="*80)

        # Resample to weekly
        df_w = df.resample('W-THU').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        print(f"\nTotal weekly candles: {len(df_w)}")
        print("\nLast 5 weeks - which DAILY bars are included:\n")

        for idx, (week_date, week_row) in enumerate(df_w.tail(5).iterrows()):
            # Show which daily bars fall into this weekly candle
            # W-THU: groups from Friday to Thursday
            # But since there's no Friday data (weekend), it should be Sun-Thu
            
            # Get all daily bars that end up in this week
            # We need to find which daily dates map to this weekly date
            week_start = week_date - pd.Timedelta(days=6)  # 7 days back (Sun to Thu = 5 days, so go back to cover it)
            week_end = week_date
            
            daily_in_week = df[(df.index > week_start) & (df.index <= week_end)]
            
            print(f"Week {idx+1}: {week_date.date()} (close={week_row['close']:.2f})")
            print(f"  Daily bars included:")
            
            for d_idx, (d_date, d_row) in enumerate(daily_in_week.iterrows(), 1):
                day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d_date.weekday()]
                print(f"    {d_idx}. {d_date.date()} ({day_name}): close={d_row['close']:.4f}")
            
            print()

        # Now check: compare with pandas internal grouping
        print("\n" + "="*80)
        print("PANDAS INTERNAL GROUPING (detailed):")
        print("="*80)
        
        # Get the groupby groups to see exact assignment
        last_5_dates = df_w.index[-5]
        for group_key, group_df in df.groupby(pd.Grouper(freq='W-THU')):
            if len(group_df) > 0 and group_key >= last_5_dates:  # Only show last 5 weeks
                print(f"\nWeek ending {group_key.date()}:")
                for d_date, d_row in group_df.iterrows():
                    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d_date.weekday()]
                    print(f"  {d_date.date()} ({day_name}): {d_row['close']:.4f}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
