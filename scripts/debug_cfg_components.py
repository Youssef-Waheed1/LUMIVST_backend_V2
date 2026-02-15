
import sys
import os
import pandas as pd
from sqlalchemy import text

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from scripts.calculate_rsi_indicators import calculate_rsi_pinescript, calculate_sma

def debug_cfg(symbol="1321"):
    db = SessionLocal()
    try:
        print(f"📊 Debugging CFG Components for {symbol}...")
        
        # 1. Fetch Daily Data
        query = text("""
            SELECT date, open, high, low, close
            FROM prices
            WHERE symbol = :symbol
            ORDER BY date ASC
        """)
        
        result = db.execute(query, {"symbol": symbol})
        rows = result.fetchall()
        
        if not rows:
            print("❌ No data found.")
            return

        df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
        closes = df['close'].tolist()
        dates = df['date'].tolist()
        
        # 2. Calculate Components
        rsi_14 = calculate_rsi_pinescript(closes, 14)
        rsi_3 = calculate_rsi_pinescript(closes, 3)
        sma3_rsi3 = calculate_sma(rsi_3, 3)
        
        # 3. Print Last 15 Days
        print("\n🔍 Last 15 Days CFG Components:")
        print(f"{'Date':<12} | {'Close':<8} | {'RSI(14)':<8} | {'RSI(3)':<8} | {'SMA3(RSI3)':<10} | {'CFG':<8}")
        print("-" * 75)
        
        for i in range(len(closes) - 15, len(closes)):
            date_str = str(dates[i])
            c = closes[i]
            r14 = rsi_14[i]
            r3 = rsi_3[i]
            s3r3 = sma3_rsi3[i]
            
            # CFG Calculation
            # CFG = RSI(14) - RSI(14)[9] + SMA(RSI(3), 3)
            r14_9 = rsi_14[i-9] if i >= 9 else None
            cfg = None
            if r14 is not None and r14_9 is not None and s3r3 is not None:
                cfg = r14 - r14_9 + s3r3
            
            print(f"{date_str:<12} | {c:<8} | {r14:.2f}     | {r3:.2f}     | {s3r3:.2f}       | {cfg:.2f} (R14[9]={r14_9:.2f})")

    finally:
        db.close()

if __name__ == "__main__":
    debug_cfg()
