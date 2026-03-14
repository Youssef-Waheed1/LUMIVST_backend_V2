"""
Migration Script: Drop redundant columns from the prices table.
These columns are now managed exclusively in stock_indicators with PineScript-exact precision.

Columns to DROP:
  - ema_10, ema_21                  (moved to stock_indicators.ema10 / ema21)
  - sma_3, ema_20_sma3              (moved to stock_indicators.sma3_rsi3 / ema20_sma3)
  - sma_4, sma_9, sma_18            (moved to stock_indicators.sma4 / sma9 / sma18)
  - sma_4w, sma_9w, sma_18w         (moved to stock_indicators.sma4_w / sma9_w / sma18_w)
  - cci_14, cci_ema_20              (moved to stock_indicators.cci / cci_ema20)
  - aroon_up, aroon_down            (moved to stock_indicators.aroon_up / aroon_down)
  - price_vs_ema_10_percent         (computed on-the-fly in frontend)
  - price_vs_ema_21_percent         (computed on-the-fly in frontend)

Columns KEPT in prices table:
  - sma_10, sma_21, sma_50, sma_150, sma_200  (used for price_vs_sma_* filters)
  - sma_200_Xm_ago                  (historical 200MA for trend conditions)
  - sma_30w, sma_40w                (no equivalent in stock_indicators)
  - price_vs_sma_*_percent          (screener filters)
  - percent_off_52w_*, vol_diff_50_percent, etc.  (screener filters)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal

COLUMNS_TO_DROP = [
    'ema_10',
    'ema_21',
    'sma_3',
    'ema_20_sma3',
    'sma_4',
    'sma_9',
    'sma_18',
    'sma_4w',
    'sma_9w',
    'sma_18w',
    'cci_14',
    'cci_ema_20',
    'aroon_up',
    'aroon_down',
    'price_vs_ema_10_percent',
    'price_vs_ema_21_percent',
]

def run_migration(dry_run: bool = True):
    db = SessionLocal()
    try:
        print(f"{'[DRY RUN] ' if dry_run else ''}حذف الأعمدة المكررة من جدول prices...\n")
        
        for col in COLUMNS_TO_DROP:
            sql = f"ALTER TABLE prices DROP COLUMN IF EXISTS {col};"
            print(f"  {'[SKIP] ' if dry_run else ''}➡️  {sql}")
            if not dry_run:
                db.execute(text(sql))
        
        if not dry_run:
            db.commit()
            print("\n✅ تم حذف جميع الأعمدة المكررة بنجاح!")
        else:
            print("\n⚠️  DRY RUN فقط - لم يتم تنفيذ أي تغييرات.")
            print("    لتنفيذ التغييرات فعلياً، شغّل: python scripts/migrate_drop_redundant_columns.py --execute")
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run_migration(dry_run=not execute)
