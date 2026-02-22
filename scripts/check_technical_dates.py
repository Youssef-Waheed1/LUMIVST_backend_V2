
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path to import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def cleanup_dates():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env")
        return

    target_date = "2026-02-17"
    print(f"🧹 Attempting to delete records for date: {target_date}...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Check if records exist first
        check_query = text("SELECT COUNT(*) FROM stock_indicators WHERE date = :target_date")
        delete_query = text("DELETE FROM stock_indicators WHERE date = :target_date")
        
        with engine.begin() as connection:
            # Check count
            result = connection.execute(check_query, {"target_date": target_date})
            count = result.scalar()
            
            if count == 0:
                print(f"ℹ️ No records found for {target_date}. Nothing to delete.")
            else:
                print(f"📦 Found {count} records. Deleting...")
                connection.execute(delete_query, {"target_date": target_date})
                print(f"✅ Successfully deleted {count} records for {target_date}.")

        # Final status check using a new connection context
        with engine.connect() as connection:
            print("\n📊 Current state of stock_indicators table:")
            status_query = text("""
                SELECT date, COUNT(*) as record_count 
                FROM stock_indicators 
                GROUP BY date 
                ORDER BY date DESC
            """)
            result = connection.execute(status_query)
            for row in result:
                print(f"  {str(row.date)}: {row.record_count} records")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    cleanup_dates()
