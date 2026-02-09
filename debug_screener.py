
import asyncio
import sys
import os
from sqlalchemy import text
import pandas as pd

# Add app to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.services.technical_indicators import calculate_all_indicators_for_stock, get_stock_prices

db = SessionLocal()

try:
    print("🔍 Starting Diagnostic Check...")
    
    # 1. Check Date Range
    print("\n📅 Checking Date Range in DB...")
    date_query = text("SELECT MIN(date), MAX(date), COUNT(*) FROM prices")
    min_date, max_date, total_count = db.execute(date_query).fetchone()
    print(f"   Min Date: {min_date}")
    print(f"   Max Date: {max_date}")
    print(f"   Total Records: {total_count}")
    
    if total_count == 0:
        print("❌ ERROR: No data in prices table!")
        sys.exit(1)

    # 2. Get a sample symbol
    print("\n🔍 Getting a sample symbol...")
    symbol_query = text("SELECT DISTINCT symbol FROM prices LIMIT 1")
    symbol = db.execute(symbol_query).scalar()
    
    if not symbol:
        print("❌ ERROR: No symbols found!")
        sys.exit(1)
        
    print(f"   Testing with symbol: {symbol}")
    
    # 3. Check Data for Symbol
    print(f"\n📊 Checking data for {symbol}...")
    df = get_stock_prices(db, symbol, days=500)
    print(f"   Retrieved {len(df)} rows.")
    
    if len(df) > 0:
        print(f"   First Date: {df['date'].iloc[0]}")
        print(f"   Last Date: {df['date'].iloc[-1]}")
    else:
        print("❌ ERROR: No price data found for symbol!")
        
    # 4. Try Calculation
    print(f"\n🧮 Attempting calculation for {symbol}...")
    try:
        result = calculate_all_indicators_for_stock(db, symbol)
        
        if result:
            print("✅ Calculation SUCCESS!")
            print(f"   RSI: {result.get('screener_rsi')}")
            print(f"   Score: {result.get('screener_score')}")
            print(f"   Final Signal: {result.get('screener_final_signal')}")
        else:
            print("❌ Calculation returned None (Empty result)")
            
    except Exception as e:
        print(f"❌ Calculation CRASHED: {e}")
        import traceback
        traceback.print_exc()

finally:
    db.close()
