from app.core.database import get_db
from sqlalchemy import text

def check_specific_stocks():
    db = next(get_db())
    conn = db.connection()
    
    symbols_to_check = ['1323', '2288', '4019']
    
    print("🔍 Deep Dive into specific symbols:")
    
    for symbol in symbols_to_check:
        print(f"\n--- Checking Symbol: {symbol} ---")
        query = text("""
            SELECT min(date), max(date), count(*)
            FROM prices
            WHERE symbol = :sym
        """)
        result = conn.execute(query, {"sym": symbol}).fetchone()
        
        if result[0]:
            print(f"Earliest Date: {result[0]}")
            print(f"Latest Date:   {result[1]}")
            print(f"Total Rows:    {result[2]}")
        else:
            print("❌ No records found in 'prices' table.")

    db.close()

if __name__ == "__main__":
    check_specific_stocks()
