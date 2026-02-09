"""
Calculate Stock Indicators Script
Calculates and stores technical indicators for all stocks in the database

Run: python -m scripts.calculate_stock_indicators
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.core.database import SessionLocal
from app.models.stock_indicators import StockIndicator
from app.services.technical_indicators import calculate_all_indicators_for_stock


def calculate_and_store_indicators(db: Session, target_date: date = None):
    """
    Calculate indicators for all stocks and store them in the database.
    Uses UPSERT: If record exists for symbol+date, it updates. Otherwise, it inserts.
    
    Args:
        db: Database session
        target_date: Date for the indicators (defaults to latest date in prices table)
    """
    print("=" * 60)
    print("📊 Starting Stock Indicators Calculation")
    print("=" * 60)
    
    # Get target date (latest date in prices if not specified)
    if target_date is None:
        result = db.execute(text("SELECT MAX(date) FROM prices"))
        target_date = result.scalar()
        print(f"📅 Using latest date: {target_date}")
    
    # Get all symbols with company names
    symbols_query = text("""
        SELECT DISTINCT p.symbol, p.company_name
        FROM prices p
        WHERE p.date = :target_date
    """)
    symbols_result = db.execute(symbols_query, {"target_date": target_date})
    symbols_data = {row[0]: row[1] for row in symbols_result.fetchall()}
    
    total_stocks = len(symbols_data)
    print(f"📈 Found {total_stocks} stocks to process")
    print("-" * 60)
    
    processed = 0
    updated = 0
    errors = 0
    
    for symbol, company_name in symbols_data.items():
        try:
            # Calculate indicators
            data = calculate_all_indicators_for_stock(db, symbol)
            
            if not data:
                print(f"⚠️  {symbol}: No data available")
                errors += 1
                continue
            
            # Prepare indicator data
            indicator_data = {
                'symbol': symbol,
                'date': target_date,
                'company_name': company_name,
                
                # Price
                'close': data.get('close'),
                
                # RSI Values (Daily)
                'rsi_14': data.get('screener_rsi'),
                'sma9_rsi': data.get('screener_sma9_rsi'),
                'wma45_rsi': data.get('screener_wma45_rsi'),
                'ema45_rsi': data.get('screener_ema45_rsi'),
                
                # The Number (Daily)
                'sma9_close': data.get('screener_sma9_close'),
                'the_number': data.get('screener_the_number'),
                
                # STAMP
                'stamp': data.get('screener_stamp', False),
                'stamp_daily': data.get('screener_stamp_daily', False),
                'stamp_weekly': data.get('screener_stamp_weekly', False),
                
                # Daily Conditions
                'rsi_55_70': data.get('screener_rsi_55_70_d', False),
                'sma9_gt_tn_daily': data.get('screener_sma9_gt_tn_d', False),
                'rsi_lt_80_d': data.get('screener_rsi_lt_80_d', False),
                'sma9_rsi_lte_75_d': data.get('screener_sma9_rsi_lte_75_d', False),
                'ema45_rsi_lte_70_d': data.get('screener_ema45_rsi_lte_70_d', False),
                'rsi_gt_wma45_d': data.get('screener_rsi_gt_wma45_d', False),
                'sma9rsi_gt_wma45rsi_d': data.get('screener_sma9rsi_gt_wma45rsi_d', False),
                
                # Weekly Conditions
                'sma9_gt_tn_weekly': data.get('screener_sma9_gt_tn_w', False),
                'rsi_lt_80_w': data.get('screener_rsi_lt_80_w', False),
                'sma9_rsi_lte_75_w': data.get('screener_sma9_rsi_lte_75_w', False),
                'ema45_rsi_lte_70_w': data.get('screener_ema45_rsi_lte_70_w', False),
                'rsi_gt_wma45_w': data.get('screener_rsi_gt_wma45_w', False),
                'sma9rsi_gt_wma45rsi_w': data.get('screener_sma9rsi_gt_wma45rsi_w', False),
                
                # Weekly Values
                'rsi_w': data.get('screener_rsi_w'),
                'sma9_rsi_w': data.get('screener_sma9_rsi_w'),
                'wma45_rsi_w': data.get('screener_wma45_rsi_w'),
                'ema45_rsi_w': data.get('screener_ema45_rsi_w'),
                'sma9_close_w': data.get('screener_sma9_close_w'),
                'the_number_w': data.get('screener_the_number_w'),
                
                # Trend Screener
                'cci': data.get('trend_cci'),
                'cci_ema20': data.get('trend_cci_ema20'),
                'aroon_up': data.get('trend_aroon_up'),
                'aroon_down': data.get('trend_aroon_down'),
                'trend_signal': data.get('trend_final_signal', False),
                
                # Final Results
                'final_signal': data.get('screener_final_signal', False),
                'score': data.get('screener_score', 0),
            }
            
            # UPSERT: Insert or Update on conflict
            stmt = insert(StockIndicator).values(indicator_data)
            stmt = stmt.on_conflict_do_update(
                constraint='uix_stock_indicators_symbol_date',
                set_={
                    'company_name': stmt.excluded.company_name,
                    'close': stmt.excluded.close,
                    'rsi_14': stmt.excluded.rsi_14,
                    'sma9_rsi': stmt.excluded.sma9_rsi,
                    'wma45_rsi': stmt.excluded.wma45_rsi,
                    'ema45_rsi': stmt.excluded.ema45_rsi,
                    'sma9_close': stmt.excluded.sma9_close,
                    'the_number': stmt.excluded.the_number,
                    'stamp': stmt.excluded.stamp,
                    'stamp_daily': stmt.excluded.stamp_daily,
                    'stamp_weekly': stmt.excluded.stamp_weekly,
                    'rsi_55_70': stmt.excluded.rsi_55_70,
                    'sma9_gt_tn_daily': stmt.excluded.sma9_gt_tn_daily,
                    'rsi_lt_80_d': stmt.excluded.rsi_lt_80_d,
                    'sma9_rsi_lte_75_d': stmt.excluded.sma9_rsi_lte_75_d,
                    'ema45_rsi_lte_70_d': stmt.excluded.ema45_rsi_lte_70_d,
                    'rsi_gt_wma45_d': stmt.excluded.rsi_gt_wma45_d,
                    'sma9rsi_gt_wma45rsi_d': stmt.excluded.sma9rsi_gt_wma45rsi_d,
                    'sma9_gt_tn_weekly': stmt.excluded.sma9_gt_tn_weekly,
                    'rsi_lt_80_w': stmt.excluded.rsi_lt_80_w,
                    'sma9_rsi_lte_75_w': stmt.excluded.sma9_rsi_lte_75_w,
                    'ema45_rsi_lte_70_w': stmt.excluded.ema45_rsi_lte_70_w,
                    'rsi_gt_wma45_w': stmt.excluded.rsi_gt_wma45_w,
                    'sma9rsi_gt_wma45rsi_w': stmt.excluded.sma9rsi_gt_wma45rsi_w,
                    'rsi_w': stmt.excluded.rsi_w,
                    'sma9_rsi_w': stmt.excluded.sma9_rsi_w,
                    'wma45_rsi_w': stmt.excluded.wma45_rsi_w,
                    'ema45_rsi_w': stmt.excluded.ema45_rsi_w,
                    'sma9_close_w': stmt.excluded.sma9_close_w,
                    'the_number_w': stmt.excluded.the_number_w,
                    'cci': stmt.excluded.cci,
                    'cci_ema20': stmt.excluded.cci_ema20,
                    'aroon_up': stmt.excluded.aroon_up,
                    'aroon_down': stmt.excluded.aroon_down,
                    'trend_signal': stmt.excluded.trend_signal,
                    'final_signal': stmt.excluded.final_signal,
                    'score': stmt.excluded.score,
                    'updated_at': datetime.now(),
                }
            )
            db.execute(stmt)
            processed += 1
            
            if processed % 20 == 0:
                db.commit()
                print(f"✅ Processed {processed}/{total_stocks} stocks...")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {str(e)}")
            errors += 1
            continue
    
    # Final commit
    db.commit()
    
    print("-" * 60)
    print("📊 Summary:")
    print(f"   ✅ Processed (Insert/Update): {processed}")
    print(f"   ❌ Errors: {errors}")
    print("=" * 60)
    
    return processed, 0, errors


def main():
    """Main entry point"""
    print(f"\n🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    try:
        calculate_and_store_indicators(db)
    finally:
        db.close()
    
    print(f"🕐 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


if __name__ == "__main__":
    main()
