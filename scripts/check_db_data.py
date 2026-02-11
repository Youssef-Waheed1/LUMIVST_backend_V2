import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def check_data(symbol):
    with engine.connect() as conn:
        print(f"Checking data for {symbol}...")
        
        # Check count
        count = conn.execute(text("SELECT count(*) FROM company_financial_metrics WHERE company_symbol = :s"), {"s": symbol}).scalar()
        print(f"Total Records: {count}")
        
        # Check distribution by Year/Period
        print("\nBreakdown by Period:")
        rows = conn.execute(text("""
            SELECT year, period, COUNT(*) 
            FROM company_financial_metrics 
            WHERE company_symbol = :s 
            GROUP BY year, period 
            ORDER BY year DESC, period
        """), {"s": symbol}).fetchall()
        
        for r in rows:
            print(f"  📅 {r[0]} - {r[1]}: {r[2]} metrics")

if __name__ == "__main__":
    check_data('1010')
