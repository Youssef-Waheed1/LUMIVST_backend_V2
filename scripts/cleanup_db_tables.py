from sqlalchemy import create_engine, text
import os
import sys

# Ensure backend path is in pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def drop_old_tables():
    print(f"🔌 Connecting to DB...")
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        tables_to_drop = ["rs_daily", "temp_rs_data", "temp_rs_batch", "financial_reports"]
        
        for table in tables_to_drop:
            try:
                print(f"🗑️ Attempting to drop table: {table}...")
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"✅ Dropped {table} (if it existed)")
            except Exception as e:
                print(f"⚠️ Error dropping {table}: {e}")
        
        conn.commit()
    print("✨ Cleanup complete.")

if __name__ == "__main__":
    drop_old_tables()
