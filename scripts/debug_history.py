from sqlalchemy import create_engine, text
import pandas as pd

# Database URL
DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"

def check_history():
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        # Check total records
        total = conn.execute(text("SELECT COUNT(*) FROM rs_daily_v2")).scalar()
        print(f"📊 Total Records in rs_daily_v2: {total:,}")
        
        # Get a sample symbol
        symbol = conn.execute(text("SELECT symbol FROM rs_daily_v2 LIMIT 1")).scalar()
        if not symbol:
            print("❌ No symbols found!")
            return

        print(f"🔍 Checking history for symbol: {symbol}")
        
        query = text("""
            SELECT date, rs_rating 
            FROM rs_daily_v2 
            WHERE symbol = :symbol 
            ORDER BY date DESC 
            LIMIT 5
        """)
        
        result = conn.execute(query, {"symbol": symbol}).fetchall()
        
        if not result:
            print(f"❌ No history found for {symbol}!")
        else:
            print(f"✅ Found {len(result)} records for {symbol}. Last 5:")
            for row in result:
                print(f"   Date: {row[0]}, RS: {row[1]}")

if __name__ == "__main__":
    check_history()
