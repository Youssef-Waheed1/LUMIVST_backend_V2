
import pandas as pd
from sqlalchemy import create_engine, text
import logging

# Setup
REGION_DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
TARGET_SYMBOL = "8260"  # Gulf General
TARGET_DATE = "2024-12-31" # Let's check close to end of year or latest available

def debug_rajhi_rs():
    print(f"🔍 Debugging RS Logic for {TARGET_SYMBOL}...")
    
    engine = create_engine(REGION_DB_URL)
    
    with engine.connect() as conn:
        # 1. Get Adjusted Close Prices for ALL stocks to calculate ranks
        print("📥 Fetching price data (Date, Symbol, Close)...")
        query = text("""
            SELECT date, symbol, close 
            FROM prices 
            WHERE date >= '2023-01-01'
        """)
        df = pd.read_sql(query, conn)
        
    print(f"📊 Loaded {len(df)} records.")
    
    # 2. Logic Check
    # Sort and calculate proper trading day shifts
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['symbol', 'date'])
    
    # Calculate Returns (Shift Logic)
    # Using 63, 126, 189, 252 trading days
    grouped = df.groupby('symbol')['close']
    
    df['r3m'] = grouped.shift(0) / grouped.shift(63) - 1
    df['r6m'] = grouped.shift(0) / grouped.shift(126) - 1
    df['r9m'] = grouped.shift(0) / grouped.shift(189) - 1
    df['r12m'] = grouped.shift(0) / grouped.shift(252) - 1
    
    # Filter for the Target Date (Latest available if specific date not found)
    latest_date = df['date'].max()
    print(f"📅 Analyzing for Date: {latest_date.date()}")
    
    day_data = df[df['date'] == latest_date].copy()
    
    if day_data.empty:
        print("❌ No data found for the target date.")
        return

    # 3. Calculate Ranks (Percentiles) for this day
    # Rank 1-99
    def get_rank(series):
        # Fill NaN with a value that puts them at the bottom or maintain NaNs
        # Here we just rank ignoring NaNs, and fill result with 0 for display
        ranks = (series.rank(pct=True) * 100).round(0)
        return ranks.fillna(0).astype(int)

    day_data['rank_3m'] = get_rank(day_data['r3m'])
    day_data['rank_6m'] = get_rank(day_data['r6m'])
    day_data['rank_9m'] = get_rank(day_data['r9m'])
    day_data['rank_12m'] = get_rank(day_data['r12m'])
    
    # RS Score Formula (40% for 3M)
    day_data['score'] = (
        0.4 * day_data['r3m'] + 
        0.2 * day_data['r6m'] + 
        0.2 * day_data['r9m'] + 
        0.2 * day_data['r12m']
    )
    day_data['rs_final_rank'] = get_rank(day_data['score'])
    
    # 4. Show Al Rajhi Details
    rajhi = day_data[day_data['symbol'] == TARGET_SYMBOL]
    
    if not rajhi.empty:
        r = rajhi.iloc[0]
        print("\n" + "="*40)
        print(f"🏦 AL RAJHI ({TARGET_SYMBOL}) Analysis for {latest_date.date()}")
        print("="*40)
        print(f"💰 Close Price:       {r['close']}")
        print("-" * 20)
        print("📈 PERFORMANCE (Returns %):")
        print(f"   3 Months: {r['r3m']*100:.2f}%")
        print(f"   6 Months: {r['r6m']*100:.2f}%")
        print(f"   9 Months: {r['r9m']*100:.2f}%")
        print(f"   1 Year:   {r['r12m']*100:.2f}%")
        print("-" * 20)
        print("🏆 MARKET RANKING (Percentile 1-99):")
        print(f"   Rank 3M:  {r['rank_3m']}  (Vs Picture: 67)")
        print(f"   Rank 6M:  {r['rank_6m']}  (Vs Picture: 92)")
        print(f"   Rank 9M:  {r['rank_9m']}  (Vs Picture: 80)")
        print(f"   Rank 1Y:  {r['rank_12m']} (Vs Picture: 91)")
        print("-" * 20)
        print(f"⭐ FINAL RS SCORE: {r['rs_final_rank']} (Vs Picture: 80)")
        print("="*40)
    else:
        print(f"❌ Symbol {TARGET_SYMBOL} not found in data for this date.")

if __name__ == "__main__":
    debug_rajhi_rs()
