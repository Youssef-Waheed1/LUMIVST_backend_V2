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
project_root = Path(__file__).resolve().parent.parent

def load_full_hierarchy_mapping():
    """
    تحميل الربط الكامل من ملف new.csv
    """
    mapping = {}
    csv_path = project_root / "new.csv"
    
    try:
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                symbol = str(row['Symbol'])
                mapping[symbol] = {
                    "industry_group": row.get('Industry Group'),
                    "sector": row.get('Sector'),
                    "industry": row.get('Industry'),
                    "sub_industry": row.get('Sub-Industry')
                }
            logger.info(f"Loaded {len(mapping)} symbols with full hierarchy from new.csv.")
        else:
            logger.warning("⚠️ new.csv not found at project root.")
    except Exception as e:
        logger.error(f"❌ Error loading hierarchy mapping: {e}")
        
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
        hierarchy_map = load_full_hierarchy_mapping()
        
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
            symbol = str(item.get("Symbol"))
            company = item.get("Company")
            
            if not symbol: continue

            # Get Detailed Hierarchy
            h = hierarchy_map.get(symbol, {})
            
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
                    "no_of_trades": int(item.get("No. of Trades", 0)),
                    "company_name": company,
                    "industry_group": h.get("industry_group"),
                    "sector": h.get("sector"),
                    "industry": h.get("industry"),
                    "sub_industry": h.get("sub_industry"),
                    "market_cap": float(item.get("Market Cap", 0.0))
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
                        "no_of_trades": stmt.excluded.no_of_trades,
                        "company_name": stmt.excluded.company_name,
                        "industry_group": stmt.excluded.industry_group,
                        "sector": stmt.excluded.sector,
                        "industry": stmt.excluded.industry,
                        "sub_industry": stmt.excluded.sub_industry,
                        "market_cap": stmt.excluded.market_cap
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
             
        # 5. Calculate Technical Indicators
        # -------------------------------------------------------------------
        logger.info("🧮 Calculating Technical Indicators (SMAs, 52W High/Low)...")
        from scripts.calculate_technicals import TechnicalCalculator
        tech_calc = TechnicalCalculator(str(settings.DATABASE_URL))
        df_tech = tech_calc.load_data()
        df_tech_res = tech_calc.calculate(df_tech)
        tech_calc.save_latest(df_tech_res)
        logger.info("✅ Technical Indicators Updated.")

        # 6. Calculate IBD Metrics (RS Ratings & Acc/Dis)
        # -------------------------------------------------------------------
        logger.info("📊 Calculating IBD Metrics (Group RS, Acc/Dis)...")
        from scripts.calculate_ibd_metrics import IBDMetricsCalculator
        
        ibd_calc = IBDMetricsCalculator(db)
        # Load enough history (approx 7 months)
        df_ibd_prices = ibd_calc.load_data(lookback_days=230)
        
        if not df_ibd_prices.empty:
            # Determine target date (ensure we don't calculate for future if data is missing)
            # Use market_date as the target
            
            # calculate_group_rs and calculate_acc_dis expect a datetime object or date string
            # Let's verify what they expect. The script converts to pd.to_datetime inside.
            
            group_rs_map = ibd_calc.calculate_group_rs(df_ibd_prices, market_date)
            acc_dis_map = ibd_calc.calculate_acc_dis(df_ibd_prices, market_date)
            
            if group_rs_map or acc_dis_map:
                ibd_calc.save_results(group_rs_map, acc_dis_map, market_date)
                logger.info("✅ IBD Metrics Updated.")
            else:
                 logger.warning("⚠️ No IBD results generated.")
        else:
            logger.warning("⚠️ No price data found for IBD Metrics.")

        # 7. Calculate Industry Group Metrics
        # -------------------------------------------------------------------
        logger.info("🏭 Calculating Industry Group Metrics (IBD Score, Rank, YTD)...")
        from scripts.calculate_industry_groups import IndustryGroupCalculator
        
        ig_calc = IndustryGroupCalculator(db)
        
        # Step 1: Calculate group index prices
        group_indices = ig_calc.calculate_group_index_prices(market_date)
        
        if group_indices:
            # Step 2: Calculate IBD scores
            group_df = ig_calc.calculate_ibd_group_score(group_indices)
            
            if not group_df.empty:
                # Step 3: Prepare summary with YTD and details
                summary_ig = ig_calc.prepare_summary_data(group_df, market_date)
                
                if not summary_ig.empty:
                    # Step 4: Save to database
                    ig_calc.save(summary_ig, market_date)
                    logger.info(f"✅ Industry Group Metrics Updated ({len(summary_ig)} groups).")
                else:
                    logger.warning("⚠️ No summary data generated for Industry Groups.")
            else:
                logger.warning("⚠️ No IBD scores calculated for Industry Groups.")
        else:
            logger.warning("⚠️ No group indices found for Industry Group Metrics calculation.")
        
        # 8. Calculate and Store Stock Technical Indicators
        # -------------------------------------------------------------------
        logger.info("📈 Calculating and Storing Stock Technical Indicators...")
        from scripts.calculate_stock_indicators import calculate_and_store_indicators
        
        processed, errors, successful = calculate_and_store_indicators(db, market_date)
        logger.info(f"✅ Stock Indicators Updated (Processed: {processed}, Successful: {successful}, Errors: {errors})")
        
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
