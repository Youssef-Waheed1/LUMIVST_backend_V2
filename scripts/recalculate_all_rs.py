import sys
from pathlib import Path
import logging
import time
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from scripts.calculate_rs_final_precise import RSCalculatorUltraFast
from sqlalchemy import text

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def recalculate_all_history():
    """
    Recalculates RS history for ALL stocks from scratch using the optimized logic.
    WARNING: This will TRUNCATE (Wipe) the rs_daily_v2 table to ensure a clean slate.
    """
    
    print("🚀 Starting Full Historical RS Recalculation...")
    print("⚠️  WARNING: This operation will REPLACE all data in rs_daily_v2 table.")
    print("⏳ Waiting 5 seconds before starting... (Ctrl+C to cancel)")
    time.sleep(5)
    
    try:
        # 1. Initialize Calculator
        db_url = str(settings.DATABASE_URL)
        calculator = RSCalculatorUltraFast(db_url)
        
        # 2. Calculate EVERYTHING in Memory
        # This uses the new logic (3m minimum, dynamic weights)
        logger.info("🧮 Calculating full history in memory...")
        start_calc = time.time()
        df_all = calculator.calculate_full_history_optimized()
        calc_time = time.time() - start_calc
        
        if df_all is None or df_all.empty:
            logger.error("❌ Calculation returned no data! Aborting save.")
            return

        logger.info(f"✅ Calculation complete in {calc_time/60:.1f} minutes.")
        logger.info(f"📊 Total Records to Save: {len(df_all):,}")
        
        # 3. Truncate Table (For Speed and Cleanliness)
        # Since we have ALL data in memory, it's faster to wipe and COPY than to UPSERT
        logger.info("🧹 Truncating rs_daily_v2 table...")
        with calculator.engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE rs_daily_v2"))
            
        # 4. Save using COPY Protocol
        logger.info("💾 Saving data to DB (using COPY)...")
        start_save = time.time()
        
        # Note: save_with_copy_protocol handles the formatting
        count = calculator.save_with_copy_protocol(df_all)
        
        save_time = time.time() - start_save
        
        print("\n" + "="*60)
        print("🎉 RECALCULATION SUCCESSFUL!")
        print("="*60)
        print(f"✅ Total Records: {count:,}")
        print(f"⏱️  Calculation Time: {calc_time/60:.1f} min")
        print(f"⏱️  Saving Time: {save_time/60:.1f} min")
        print(f"🚀 Total Time: {(calc_time + save_time)/60:.1f} min")
        print("="*60)

    except Exception as e:
        logger.error(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    recalculate_all_history()
