import sys
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# إضافة المسار للمجلد الرئيسي للوصول للإعدادات
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
import app.api.routes.screeners as screeners

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_all_screeners():
    db: Session = SessionLocal()
    try:
        latest_date = screeners.get_latest_date(db)
        logger.info("=" * 60)
        logger.info(f"🚀 RUNNING SCREENERS FOR LATEST DATE: {latest_date}")
        logger.info("=" * 60)

        # 1. Trend 1 Month
        logger.info("\n🔵 Testing Trend - 1 Month...")
        res_1m = screeners.get_trend_1_month(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_1m['count']} stocks")
        if res_1m['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_1m['data'][:10]]) + ("..." if res_1m['count'] > 10 else ""))

        # 2. Trend 2 Months
        logger.info("\n🔵 Testing Trend - 2 Months...")
        res_2m = screeners.get_trend_2_months(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_2m['count']} stocks")
        if res_2m['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_2m['data'][:10]]) + ("..." if res_2m['count'] > 10 else ""))

        # 3. Trend 4 Months
        logger.info("\n🔵 Testing Trend - 4 Months...")
        res_4m = screeners.get_trend_4_months(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_4m['count']} stocks")
        if res_4m['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_4m['data'][:10]]) + ("..." if res_4m['count'] > 10 else ""))

        # 4. Trend 5 Months
        logger.info("\n🔵 Testing Trend - 5 Months...")
        res_5m = screeners.get_trend_5_months(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_5m['count']} stocks")
        if res_5m['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_5m['data'][:10]]) + ("..." if res_5m['count'] > 10 else ""))

        # 5. Trend 5 Months Wide
        logger.info("\n🔵 Testing Trend - 5 Months Wide...")
        res_wide = screeners.get_trend_5_months_wide(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_wide['count']} stocks")
        if res_wide['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_wide['data'][:10]]) + ("..." if res_wide['count'] > 10 else ""))

        # 6. Power Play
        logger.info("\n🔴 Testing Power Play...")
        res_pp = screeners.get_power_play(db=db, limit=5000, offset=0, target_date=latest_date)
        logger.info(f"✅ Found {res_pp['count']} stocks")
        if res_pp['count'] > 0:
            logger.info("   Symbols: " + ", ".join([d['symbol'] for d in res_pp['data'][:10]]) + ("..." if res_pp['count'] > 10 else ""))
            
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Testing Complete! Check these numbers against what you see on the Web UI.")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    test_all_screeners()
