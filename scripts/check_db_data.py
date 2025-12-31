import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
import logging

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, engine
from app.models.rs_daily import RSDaily

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_data_sample():
    db = SessionLocal()
    try:
        # جلب عدد السجلات
        count = db.query(RSDaily).count()
        print(f"\n📊 Total Records in 'rs_daily': {count}")
        
        if count > 0:
            # جلب آخر 5 سجلات
            print("\n📋 Latest 5 Records:")
            stmt = text("SELECT symbol, date, rs_percentile, return_3m, rank_position FROM rs_daily ORDER BY date DESC, rs_percentile DESC LIMIT 5")
            with db.bind.connect() as conn:
                df = pd.read_sql(stmt, conn)
            print(df.to_string(index=False))
            
            # جلب أول 5 سجلات (أقدم تاريخ)
            print("\n📋 Oldest 5 Records:")
            stmt = text("SELECT symbol, date, rs_percentile, return_3m, rank_position FROM rs_daily ORDER BY date ASC, rs_percentile DESC LIMIT 5")
            with db.bind.connect() as conn:
                df_old = pd.read_sql(stmt, conn)
            print(df_old.to_string(index=False))
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    show_data_sample()
