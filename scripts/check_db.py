import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.official_filings import CompanyOfficialFiling

def check_filings(symbol):
    db = SessionLocal()
    filings = db.query(CompanyOfficialFiling).filter(
        CompanyOfficialFiling.company_symbol == symbol
    ).all()
    
    print(f"\n🔍 Checking filings for Symbol: {symbol}")
    print(f"Total count: {len(filings)}")
    
    if not filings:
        print("No filings found.")
        db.close()
        return

    print(f"{'ID':<5} | {'Lang':<5} | {'Year':<5} | {'Period':<10} | {'Category':<25} | {'URL (first 60 chars)'}")
    print("-" * 120)
    
    for f in filings:
        lang = str(getattr(f, 'language', 'N/A'))
        url = (f.source_url or '')[:60]
        print(f"{f.id:<5} | {lang:<5} | {f.year:<5} | {str(f.period):<10} | {str(f.category):<25} | {url}")
    
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_db.py <SYMBOL>")
    else:
        check_filings(sys.argv[1])
