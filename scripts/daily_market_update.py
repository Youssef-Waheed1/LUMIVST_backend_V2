import sys
from pathlib import Path
import csv
import traceback
import json
import logging
import datetime
import pandas as pd
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
# ✅ استخدام الـ Calculator النهائي
from scripts.calculate_rs_final_precise import RSCalculatorUltraFast

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

def update_daily(target_date_str=None):
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
        
        # 1. Determine Date
        if target_date_str:
            market_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
            logger.info(f"📅 User provided custom date: {market_date}")
        else:
            market_date = date.today()
            logger.info(f"📅 Using today's date: {market_date}")

        # 2. Scraping
        logger.info("📡 Scraping daily detailed report...")
        scraped_data = scrape_daily_details(headless=True)
        
        if not scraped_data:
            logger.error("❌ Scraping failed or returned no data.")
            return

        logger.info(f"📊 Scraped {len(scraped_data)} records.")
        

        # 3. Saving Prices
        success_count = 0
        for item in scraped_data:
            symbol = item.get("Symbol")
            company = item.get("Company")
            
            if not symbol: continue

            # Get Industry Group
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
        logger.info(f"✅ Successfully saved/updated {success_count} price records for {market_date}.")
        
        # 4. RS Calculation (Optimized Final)
        # -------------------------------------------------------------------
        logger.info("🧮 Starting RS Calculation (Incremental Mode)...")
        
        # Use the UltraFast Vectorized Calculator
        # calculate_full_history_optimized returns a DataFrame of ALL calcs
        calculator = RSCalculatorUltraFast(str(settings.DATABASE_URL))
        df_all_results = calculator.calculate_full_history_optimized()
        
        if df_all_results is not None and not df_all_results.empty:
            # FILTER: Keep only records for the target market_date
            # Ensure date column is properly typed for filtering
            df_all_results['date'] = pd.to_datetime(df_all_results['date']).dt.date
            
            df_today = df_all_results[df_all_results['date'] == market_date]
            
            if not df_today.empty:
                logger.info(f"💾 Saving {len(df_today)} RS records for {market_date}...")
                
                # SAVE (Append)
                calculator.save_bulk_results(df_today)
                logger.info(f"✅ Calculated and saved RS Data for {market_date}.")
            else:
                logger.warning(f"⚠️ No RS results found for {market_date}. Check if prices were saved correctly.")
        else:
             logger.error("❌ Calculation returned no results.")
        
        logger.info("🎉 Daily Update Workflow Completed Successfully!")

    except Exception as e:
        logger.error(f"❌ Critical Error in Daily Update: {e}")
        # No rollback here for the scrape part as it was committed above
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run Daily Market Update')
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format (overrides today)')
    
    args = parser.parse_args()
    
    update_daily(args.date)
