"""
Fix: Change period column from Enum to String for flexibility,
and filter empty metric names.
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Check current column type
    r = conn.execute(text("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'company_financial_metrics' AND column_name = 'period'
    """))
    row = r.fetchone()
    print(f"Current period column: {row}")
    
    # Change period from enum to varchar
    print("🔄 Changing period column from enum to varchar...")
    conn.execute(text("""
        ALTER TABLE company_financial_metrics 
        ALTER COLUMN period TYPE VARCHAR(20) USING period::text
    """))
    conn.commit()
    print("✅ Done! Period column is now VARCHAR.")
    
    # Verify
    r = conn.execute(text("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'company_financial_metrics' AND column_name = 'period'
    """))
    row = r.fetchone()
    print(f"New period column: {row}")
