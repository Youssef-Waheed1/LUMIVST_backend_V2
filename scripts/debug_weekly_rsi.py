
import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import text
from typing import List

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from scripts.calculate_rsi_indicators import calculate_rsi_pinescript

def debug_weekly_data(symbol="1321"):
    db = SessionLocal()
    try:
        print(f"📊 Debugging Weekly Data for {symbol}...")
        
        # 1. Fetch Daily Data (LIMIT 5000)
        query = text("""
            SELECT date, open, high, low, close
            FROM prices
            WHERE symbol = :symbol
            ORDER BY date ASC
        """) # No limit to verify full history, but assuming user db has history
        
        result = db.execute(query, {"symbol": symbol})
        rows = result.fetchall()
        
        if not rows:
            print("❌ No data found.")
            return

        print(f"📉 Total Daily Rows fetched: {len(rows)}")
        
        # 2. DataFrame Logic
        df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col])
        
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        print(f"📅 Daily Date Range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"💰 Latest Daily Close: {df.iloc[-1]['close']}")

        # 3. Resample Weekly (W-THU)
        df_weekly = df.resample('W-THU').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        print(f"📅 Weekly Rows created: {len(df_weekly)}")
        
        # 4. Calculate RSI
        closes_w = df_weekly['close'].tolist()
        rsi_w = calculate_rsi_pinescript(closes_w, 14)
        
        df_weekly['rsi_14'] = rsi_w
        
        # 5. Print Last 10 Weeks
        print("\n🔍 Last 10 Weekly Candles:")
        print(f"{'Date':<12} | {'Close':<10} | {'RSI(14)':<10}")
        print("-" * 40)
        
        last_10 = df_weekly.tail(10)
        for date, row in last_10.iterrows():
            rsi_val = f"{row['rsi_14']:.2f}" if row['rsi_14'] else "None"
            print(f"{date.date()} | {row['close']:<10} | {rsi_val:<10}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_weekly_data()
