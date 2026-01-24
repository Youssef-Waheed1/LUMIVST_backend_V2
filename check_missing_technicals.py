from app.core.database import get_db
from sqlalchemy import text
import pandas as pd

def check_missing():
    db = next(get_db())
    conn = db.connection()
    
    print("🔍 Analyzing stocks with missing SMA 200...")
    
    # Get symbols with NULL SMA 200 but valid Close price today
    query = text("""
        SELECT symbol, count(*) as history_days
        FROM prices
        GROUP BY symbol
        HAVING count(*) < 200
        LIMIT 20
    """)
    
    result = conn.execute(query).fetchall()
    
    print(f"\nFound {len(result)} stocks with less than 200 days of history:")
    for row in result:
        print(f"Symbol: {row[0]} | History: {row[1]} days")
        
    # Check if there are stocks with > 200 days but still NULL (which would indicate a bug)
    query_bug = text("""
        SELECT p.symbol, count(p.id) as history
        FROM prices p
        WHERE p.symbol IN (
            SELECT symbol FROM prices WHERE date = '2026-01-21' AND price_minus_sma_200 IS NULL
        )
        GROUP BY p.symbol
        HAVING count(p.id) >= 200
    """)
    
    result_bug = conn.execute(query_bug).fetchall()
    if result_bug:
        print(f"\n⚠️ Stocks with enough history (>200) but still NULL SMA 200 (Potential Bug):")
        for row in result_bug:
            print(f"Symbol: {row[0]} | History: {row[1]} days")
    else:
        print("\n✅ No bugs found: All missing values are due to insufficient history (< 200 days).")

    db.close()

if __name__ == "__main__":
    check_missing()
