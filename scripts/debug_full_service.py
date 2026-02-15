
import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import text
from typing import List

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from scripts.indicators_data_service import IndicatorsDataService
from scripts.calculate_the_number_indicators import calculate_the_number_full

def debug_service(symbol="1321"):
    db = SessionLocal()
    try:
        print(f"📊 Debugging FULL INDICATORS SERVICE Check for {symbol}...")
        
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

        df = IndicatorsDataService.prepare_price_dataframe(rows)
        print(f"📈 Daily DF Rows: {len(df)}")
        print(f"💰 Last Daily Close: {df.iloc[-1]['close']}")
        
        # 2. Convert to Weekly
        df_weekly = IndicatorsDataService.prepare_weekly_dataframe(df)
        print(f"📅 Weekly DF Rows: {len(df_weekly)}")
        print(f"💰 Last Weekly Close in df_weekly: {df_weekly.iloc[-1]['close']}")
        
        # 3. Calculate The Number Weekly Manually
        print("\n🔍 MANUAL CALCULATION OF WEEKLY THE NUMBER:")
        closes_w = df_weekly['close'].tolist()
        highs_w = df_weekly['high'].tolist()
        lows_w = df_weekly['low'].tolist()
        
        tn_components_w = calculate_the_number_full(highs_w, lows_w, closes_w)
        
        last_tn = tn_components_w['the_number'][-1]
        last_h13 = tn_components_w['high_sma13'][-1]
        last_l13 = tn_components_w['low_sma13'][-1]
        last_h65 = tn_components_w['high_sma65'][-1]
        last_l65 = tn_components_w['low_sma65'][-1]
        
        print(f"   Calculated TN: {last_tn}")
        print(f"   Calculated H13: {last_h13}")
        print(f"   Calculated L13: {last_l13}")
        print(f"   Calculated H65: {last_h65}")
        print(f"   Calculated L65: {last_l65}")
        
        calc_tn = (last_h13 + last_l13 + last_h65 + last_l65) / 4
        print(f"   Verification (Sum/4): {calc_tn}")
        
        # 4. Check what's in df_weekly columns
        print("\n🔍 DF_WEEKLY Columns Values (Last Row):")
        cols_to_check = ['the_number_w', 'high_sma13_w', 'low_sma13_w']
        for col in cols_to_check:
            if col in df_weekly.columns:
                print(f"   {col}: {df_weekly.iloc[-1][col]}")
            else:
                print(f"   {col}: MISSING!")

        # 5. Check Merge
        print("\n🔍 CHECK MERGE:")
        merged = IndicatorsDataService.merge_weekly_with_daily(df, df_weekly)
        last_daily_idx = merged.index[-1]
        print(f"   Last Daily Date: {last_daily_idx}")
        
        for col in cols_to_check:
            if col in merged.columns:
                print(f"   Merged {col}: {merged.iloc[-1][col]}")
            else:
                print(f"   Merged {col}: MISSING!")

        # 6. Check Final Result Dict logic
        print("\n🔍 RESULT DICT LOGIC:")
        idx = len(df) - 1
        res_h13_w = merged.iloc[idx]['high_sma13_w'] if 'high_sma13_w' in merged.columns else None
        print(f"   Result high_sma13_w: {res_h13_w}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_service()
