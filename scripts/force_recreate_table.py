from sqlalchemy import create_engine, text
import os
import sys

# Add backend to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.scraped_reports import FinancialReport

def force_recreate():
    print(f"🔌 Connecting to DB...")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("🔥 Dropping table 'financial_reports' and related Enums...")
        conn.execute(text("DROP TABLE IF EXISTS financial_reports CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS period_type_enum CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS report_type_enum CASCADE"))
        conn.commit()
    
    print("✨ Recreating table from model schema...")
    FinancialReport.__table__.create(engine)
    print("✅ Table 'financial_reports' recreated successfully with ALL columns.")

if __name__ == "__main__":
    force_recreate()
