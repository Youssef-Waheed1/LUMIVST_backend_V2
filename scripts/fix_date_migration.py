from datetime import date, timedelta
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.price import Price
from app.models.rs_daily import RSDaily
from sqlalchemy import text

def migrate_data():
    db = SessionLocal()
    try:
        source_date = date(2025, 12, 30)
        target_date = date(2025, 12, 29)
        
        print(f"🔄 Migrating data from {source_date} to {target_date}...")
        
        # 1. Delete existing data for target date to avoid conflicts
        prices_del = db.query(Price).filter(Price.date == target_date).delete()
        rs_del = db.query(RSDaily).filter(RSDaily.date == target_date).delete()
        print(f"🗑️ Deleted existing data for {target_date}: {prices_del} prices, {rs_del} RS records")
        db.flush()
        
        # 2. Update date for Prices
        prices_updated = db.query(Price).filter(Price.date == source_date).update({Price.date: target_date})
        print(f"✅ Migrated {prices_updated} Price records")
        
        # 3. Update date for RS
        rs_updated = db.query(RSDaily).filter(RSDaily.date == source_date).update({RSDaily.date: target_date})
        print(f"✅ Migrated {rs_updated} RS records")
        
        db.commit()
        print("🎉 Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
