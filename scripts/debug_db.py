
import sys
import os
from sqlalchemy import text
from decimal import Decimal

# Add parent directory to path to allow importing app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.stock_indicators import StockIndicator

def check_data():
    session = SessionLocal()
    
    try:
        # Check count of all indicators
        count_query = text("SELECT COUNT(*) FROM stock_indicators")
        count = session.execute(count_query).scalar()
        print(f"Total rows in stock_indicators: {count}")
        
        # Check max date
        max_date_query = text("SELECT MAX(date) FROM stock_indicators")
        max_date = session.execute(max_date_query).scalar()
        print(f"Latest date in stock_indicators: {max_date}")

        if max_date:
            # Check count for max date
            latest_count_query = text("SELECT COUNT(*) FROM stock_indicators WHERE date = :date")
            latest_count = session.execute(latest_count_query, {"date": max_date}).scalar()
            print(f"Rows for {max_date}: {latest_count}")
            
            # Fetch a sample
            sample_query = text("SELECT symbol, close, score FROM stock_indicators WHERE date = :date LIMIT 5")
            sample = session.execute(sample_query, {"date": max_date}).fetchall()
            print("Sample data:", sample)
            
            # Check for specific symbol if known
            symbol = '2080' # GASCO, mentioned in logs
            gasco = session.execute(text("SELECT * FROM stock_indicators WHERE symbol = :symbol AND date = :date"), 
                                  {"symbol": symbol, "date": max_date}).fetchone()
            if gasco:
                print(f"Found GASCO: {gasco}")
            else:
                print("GASCO not found for latest date")

    except Exception as e:
        print(f"Error checking DB: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_data()
