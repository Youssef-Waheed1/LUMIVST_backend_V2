import sys
from pathlib import Path
import csv
import traceback
import logging
import datetime
from datetime import date, timedelta
from sqlalchemy.dialects.postgresql import insert

# إضافة المجلد الرئيسي للمشروع إلى مسار بايثون
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.core.database import SessionLocal
from app.models.price import Price
# استيراد الخدمات الجديدة
from app.services.daily_detailed_scraper import scrape_daily_details
from app.services.rs_calculator_v2 import calculate_and_save_rs_v2

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_company_symbols():
    """
    تحميل ملف CSV لربط أسماء الشركات بالرموز.
    يستخدم كخطة بديلة إذا فشل السكرابر في جلب الرمز مباشرة.
    """
    mapping = {}
    csv_path = project_root / "company_symbols.csv"
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # تخطي الهيدر المكرر إن وجد
                if row.get('Symbol') == 'Symbol':
                    continue
                    
                sym = row.get('Symbol', '').strip()
                company = row.get('Company', '').strip()
                
                # التأكد من أن الرمز رقمي
                if sym.isdigit() and company:
                    mapping[company] = sym
    except Exception as e:
        logger.error(f"Error loading company symbols: {e}")
    
    logger.info(f"Loaded {len(mapping)} symbols from CSV.")
    return mapping

def update_daily():
    db = SessionLocal()
    try:
        logger.info(f"🚀 Starting Daily Market Update...")
        
        # 1. Scraping (Scraper V2 - Detailed Daily Report)
        # -------------------------------------------------------------------
        logger.info("📡 Scraping daily detailed report...")
        scraped_data = scrape_daily_details(headless=True)
        
        if not scraped_data:
            logger.error("❌ No data scraped. Aborting update.")
            return

        logger.info(f"📊 Scraped {len(scraped_data)} records.")
        
        # تحميل خريطة الرموز (اختياري)
        symbol_map = load_company_symbols()
        
        # تحديد تاريخ البيانات
        # المنطق: لو الوقت قبل 10 صباحاً، يبقى بنحدث بيانات أمس
        now = datetime.datetime.now()
        market_date = date.today()
        if now.hour < 10:
             market_date = date.today() - timedelta(days=1)
        
        logger.info(f"📅 Setting market date to: {market_date}")

        # 2. Saving Prices to Database
        # -------------------------------------------------------------------
        success_count = 0
        for item in scraped_data:
            symbol = item.get("Symbol")
            company = item.get("Company")
            
            # محاولة تصحيح الرمز من الخريطة لو مش موجود
            if (not symbol or not symbol.isdigit()) and company:
                symbol = symbol_map.get(company)
            
            if not symbol:
                continue

            # تجهيز البيانات للإدخال
            price_data = {
                "symbol": symbol,
                "date": market_date,
                "open": item.get("Open", 0.0),
                "high": item.get("Highest", 0.0),
                "low": item.get("Lowest", 0.0),
                "close": item.get("Close", 0.0),
                "volume_traded": int(item.get("Volume Traded", 0)),
                "value_traded_sar": float(item.get("Value Traded", 0.0)),
                "company_name": company # تحديث اسم الشركة
            }
            
            # Upsert (Insert or Update)
            stmt = insert(Price).values(price_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'date'],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume_traded": stmt.excluded.volume_traded,
                    "value_traded_sar": stmt.excluded.value_traded_sar,
                    "company_name": stmt.excluded.company_name
                }
            )
            db.execute(stmt)
            success_count += 1
            
        db.commit()
        logger.info(f"✅ Successfully saved/updated {success_count} price records.")

        # 3. RS Calculation (Calculator V2 - Trading Days Logic)
        # -------------------------------------------------------------------
        logger.info("🧮 Starting RS Calculation V2 (Trading Days Sequence)...")
        
        # بنشغل الحسابات للكل عشان نضمن إن الـ sequences مظبوطة للبيانات الجديدة
        calculate_and_save_rs_v2(db) 
        
        logger.info("🎉 Daily Update Workflow Completed Successfully!")

    except Exception as e:
        logger.error(f"❌ Critical Error in Daily Update: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    update_daily()
