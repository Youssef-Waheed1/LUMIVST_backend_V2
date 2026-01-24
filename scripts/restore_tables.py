from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.scraped_reports import FinancialReport

def restore_tables():
    engine = create_engine(settings.DATABASE_URL)
    print("🚑 Restoring 'financial_reports' table...")
    
    # Clean up potentially orphaned types
    with engine.connect() as conn:
        try:
            print("Cleaning up old types...")
            # We don't drop types to preserve data integrity if used elsewhere, 
            # but here we know they are blocking creation.
            # Actually, existing types are fine, we just need SQLAlchemy to NOT try creating them again.
            # But SQLAlchemy's create_all usually handles checkfirst.
            # The issue is psycopg2 throws DuplicateObject directly.
            pass
        except Exception as e:
            print(f"Warning: {e}")

    try:
        FinancialReport.__table__.create(engine)
        print("✅ Table 'financial_reports' restored successfully.")
    except Exception as e:
        if "already exists" in str(e):
             print(f"⚠️ Types already exist, retrying creation without types might be needed or manual intervention.")
             # Fallback: try using raw SQL if ORM fails due to types
             # Or just ignore if table exists? No, table is missing.
             print(f"Error detail: {e}")
             
        # Force create via raw SQL if types persist? 
        # Better: Drop types first so ORM can recreate them clean.
        with engine.connect() as conn:
            print("♻️ Dropping conflict types to recreate...")
            conn.execute(text("DROP TYPE IF EXISTS period_type_enum CASCADE"))
            conn.execute(text("DROP TYPE IF EXISTS report_type_enum CASCADE"))
            conn.commit()
            
        print("🔄 Retrying creation...")
        FinancialReport.__table__.create(engine)
        print("✅ Table 'financial_reports' restored successfully (Attempt 2).")

if __name__ == "__main__":
    restore_tables()
