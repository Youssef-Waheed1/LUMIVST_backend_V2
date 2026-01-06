import sys
from pathlib import Path
import csv
import traceback
import json
import logging
import datetime
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal 
from app.models.price import Price
# استيراد الخدمات الجديدة
from app.services.daily_detailed_scraper import scrape_daily_details
# ✅ بنستخدم الـ Calculator الجديد المبني على الـ Calendar عشان السرعة والدقة
from scripts.rs_calculator_v3_calendar import calculate_daily_rs

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مسار المشروع والملفات
project_root = Path(__file__).resolve().parent.parent.parent

def load_industry_mapping():
    """
    تحميل ملف الربط بين الرموز والقطاعات
    """
    mapping = {}
    json_path = project_root / "backend" / "industry_mapping.json"
    
    # Try different paths just in case
    if not json_path.exists():
         json_path = project_root / "industry_mapping.json"
         
    try:
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            logger.info(f"Loaded {len(mapping)} industry mappings.")
        else:
            logger.warning("⚠️ Industry mapping file not found. New stocks might miss industry info.")
    except Exception as e:
        logger.error(f"❌ Error loading industry mapping: {e}")
        
    return mapping

def update_daily():
    """
    1. Scrape Daily Data
    2. Save to DB (with correct Industry Group)
    3. Calculate RS (Incremental)
    """
    # تهيئة الاتصال بقاعدة البيانات
    db = SessionLocal()
    
    try:
        logger.info(f"🚀 Starting Daily Market Update...")
        
        # 0. Load Mappings
        industry_map = load_industry_mapping()
        
        # 1. Scraping
        logger.info("📡 Scraping daily detailed report...")
        # Scraper returns list of dicts: {'Symbol': '...', 'Close': ...}
        scraped_data = scrape_daily_details(headless=True)
        
        if not scraped_data:
            logger.error("❌ Scraping failed or returned no data.")
            return

        logger.info(f"📊 Scraped {len(scraped_data)} records.")
        
        # تحديد التاريخ (نفس اللوجيك بتاعك)
        now = datetime.datetime.now()
        market_date = date.today()
        # لو قبل الساعة 3:30 (وقت إغلاق السوق + قليل)، ممكن نكون بنحدث امبارح؟
        # بس الأصح نخليها دايمًا تاريخ اليوم، ولو البيانات لسة منزلتش السكرابر هيجيب القديم؟
        # لأ، صفحة تداول بتتحدث يوميًا. هنفترض إننا بنشغل السكربت بعد الإغلاق.
        
        logger.info(f"📅 Setting market date to: {market_date}")

        # 2. Saving Prices
        success_count = 0
        for item in scraped_data:
            symbol = item.get("Symbol")
            company = item.get("Company")
            
            if not symbol: continue

            # Get Industry Group
            # 1. Try from Scraper (unlikely for daily page)
            # 2. Try from Mapping File (Static)
            # 3. Fallback to "Unknown"
            industry = item.get("Industry Group") or item.get("Sector")
            if not industry:
                industry = industry_map.get(str(symbol), "Unknown")

            try:
                price_data = {
                    "symbol": symbol,
                    "date": market_date,
                    "open": item.get("Open", 0.0),
                    "high": item.get("Highest", 0.0),
                    "low": item.get("Lowest", 0.0),
                    "close": item.get("Close", 0.0),
                    "change": item.get("Change", 0.0),
                    "change_percent": item.get("Change %", 0.0),
                    "volume_traded": int(item.get("Volume Traded", 0)),
                    "value_traded_sar": float(item.get("Value Traded", 0.0)),
                    "company_name": company,
                    "industry_group": industry  # ✅ Added Industry
                }
                
                # Upsert
                stmt = insert(Price).values(price_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'date'],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "change": stmt.excluded.change,
                        "change_percent": stmt.excluded.change_percent,
                        "volume_traded": stmt.excluded.volume_traded,
                        "value_traded_sar": stmt.excluded.value_traded_sar,
                        "company_name": stmt.excluded.company_name,
                        "industry_group": stmt.excluded.industry_group
                    }
                )
                db.execute(stmt)
                success_count += 1
            except Exception as row_error:
                logger.warning(f"⚠️ Skipped row {symbol}: {row_error}")
                continue
            
        db.commit()
        logger.info(f"✅ Successfully saved/updated {success_count} price records.")

        # 3. RS Calculation (Optimized V3)
        # -------------------------------------------------------------------
        logger.info("🧮 Starting RS Calculation (Incremental)...")
        
        # Calculate RS just for the target date
        # Note: We pass the DB URL string, not the session
        calculate_daily_rs(str(settings.DATABASE_URL), target_date=market_date)
        
        logger.info("🎉 Daily Update Workflow Completed Successfully!")

    except Exception as e:
        logger.error(f"❌ Critical Error in Daily Update: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_daily()
