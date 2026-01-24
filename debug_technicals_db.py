from app.core.database import get_db
from sqlalchemy import text
import pandas as pd

def check_db_values():
    db = next(get_db())
    conn = db.connection()
    
    query = text("""
        SELECT symbol, date, 
               price_vs_sma_10_percent, percent_off_52w_high, vol_diff_50_percent
        FROM prices
        WHERE date = '2026-01-21'
        LIMIT 10
    """)
    
    result = conn.execute(query).fetchall()
    
    print("📋 Checking values in DB for 2026-01-21:")
    if not result:
        print("❌ No data found for 2026-01-21")
        # Check if there is data at all
        query_any = text("SELECT count(*) FROM prices WHERE price_vs_sma_10_percent IS NOT NULL")
        count = conn.execute(query_any).scalar()
        print(f"Total rows with technical data: {count}")
    else:
        for row in result:
            print(f"Symbol: {row[0]} | Date: {row[1]} | SMA10%: {row[2]} | OffHigh%: {row[3]} | VolDiff%: {row[4]}")

    db.close()

if __name__ == "__main__":
    check_db_values()
