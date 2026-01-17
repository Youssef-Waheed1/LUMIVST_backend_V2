import sys
import os

# Adds backend directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.scraped_reports import FinancialReport

def clean_company(symbol):
    db = SessionLocal()
    try:
        deleted = db.query(FinancialReport).filter(FinancialReport.company_symbol == symbol).delete()
        db.commit()
        print(f"✅ Deleted {deleted} corrupt/old reports for {symbol}")
    except Exception as e:
        print(f"❌ Error deleting reports: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_company('4322')
