"""
Migration Script: Drop Market Statistics columns from the prices table.
These columns have been migrated to stock_indicators.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal

COLUMNS_TO_DROP = [
    # SMAs
    'sma_10', 'sma_21', 'sma_50', 'sma_150', 'sma_200',
    # Historical 200MA
    'sma_200_1m_ago', 'sma_200_2m_ago', 'sma_200_3m_ago', 'sma_200_4m_ago', 'sma_200_5m_ago',
    # Weekly SMAs
    'sma_30w', 'sma_40w',
    # 52-Week & Volume
    'fifty_two_week_high', 'fifty_two_week_low', 'average_volume_50',
    # Price minus SMA
    'price_minus_sma_10', 'price_minus_sma_21', 'price_minus_sma_50', 'price_minus_sma_150', 'price_minus_sma_200',
    # Percentage comparisons
    'price_vs_sma_10_percent', 'price_vs_sma_21_percent', 'price_vs_sma_50_percent', 'price_vs_sma_150_percent', 'price_vs_sma_200_percent',
    # Off High/Low & Volume diff
    'percent_off_52w_high', 'percent_off_52w_low', 'vol_diff_50_percent'
]

def run_migration(dry_run: bool = True):
    db = SessionLocal()
    try:
        print(f"{'[DRY RUN] ' if dry_run else ''}حذف أعمدة Market Statistics من جدول prices...\n")
        
        for col in COLUMNS_TO_DROP:
            sql = f"ALTER TABLE prices DROP COLUMN IF EXISTS {col};"
            print(f"  {'[SKIP] ' if dry_run else ''}➡️  {sql}")
            if not dry_run:
                db.execute(text(sql))
        
        if not dry_run:
            db.commit()
            print("\n✅ تم حذف جميع الأعمدة بنجاح! جدول prices الآن OHLCV نقي.")
        else:
            print("\n⚠️  DRY RUN فقط - لم يتم تنفيذ أي تغييرات.")
            print("    لتنفيذ التغييرات فعلياً، شغّل: python scripts/migrate_drop_market_stats_from_prices.py --execute")
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run_migration(dry_run=not execute)
