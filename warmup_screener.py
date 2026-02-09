
import asyncio
import sys
import os
import time
import json
import redis
from sqlalchemy import text
from decimal import Decimal
from datetime import date

# Add app to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.services.technical_indicators import calculate_all_indicators_for_stock
from app.core.config import settings

import numpy as np

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, date):
            return str(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def warmup_cache():
    db = SessionLocal()
    
    # Establish a direct synchronous Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        print("✅ Connected to Redis successfully.")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return

    try:
        print("🚀 Starting Screener Warmup (Pre-calculation)...")
        start_time = time.time()
        
        # Get all symbols
        print("📋 Fetching symbols...")
        symbols_query = text("""
            SELECT DISTINCT p.symbol, p.company_name
            FROM prices p
            WHERE p.date = (SELECT MAX(date) FROM prices)
        """)
        symbols_result = db.execute(symbols_query).fetchall()
        symbols_data = {row[0]: row[1] for row in symbols_result}
        
        total_symbols = len(symbols_data)
        print(f"   Found {total_symbols} symbols.")
        
        all_results = []
        processed = 0
        errors = 0
        
        for symbol, company_name in symbols_data.items():
            try:
                # Calculate
                data = calculate_all_indicators_for_stock(db, symbol)
                
                if data:
                    item = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'date': data.get('date'),
                        'close': data.get('close'),
                        'rsi': data.get('screener_rsi'),
                        'sma9_rsi': data.get('screener_sma9_rsi'),
                        'wma45_rsi': data.get('screener_wma45_rsi'),
                        'ema45_rsi': data.get('screener_ema45_rsi'),
                        'sma9_close': data.get('screener_sma9_close'),
                        'the_number': data.get('screener_the_number'),
                        'stamp': data.get('screener_stamp', False),
                        'stamp_daily': data.get('screener_stamp_daily', False),
                        'stamp_weekly': data.get('screener_stamp_weekly', False),
                        'rsi_55_70': data.get('screener_rsi_55_70_d', False),
                        'sma9_gt_tn_daily': data.get('screener_sma9_gt_tn_d', False),
                        'sma9_gt_tn_weekly': data.get('screener_sma9_gt_tn_w', False),
                        'cci': data.get('trend_cci'),
                        'aroon_up': data.get('trend_aroon_up'),
                        'aroon_down': data.get('trend_aroon_down'),
                        'trend_signal': data.get('trend_final_signal', False),
                        'final_signal': data.get('screener_final_signal', False),
                        'score': data.get('screener_score', 0),
                    }
                    all_results.append(item)

                    # NEW: Cache individual stock data for detail view
                    # We need to structure it exactly as the /stock/{symbol} endpoint expects
                    stock_detail = {
                        "symbol": symbol,
                        "date": data.get('date'),
                        "close": data.get('close'),
                        "indicators": {
                            "rsi": {
                                "rsi": data.get('screener_rsi'),
                                "sma9": data.get('screener_sma9_rsi'),
                                "wma45": data.get('screener_wma45_rsi')
                            },
                            "the_number": {
                                "sma9": data.get('screener_sma9_close'),
                                "value": data.get('screener_the_number'),
                                "upper_band": None, # Not calculated in screener due to performance, can be added if needed
                                "lower_band": None
                            },
                            "stamp": {
                                "s9_rsi": data.get('screener_sma9_rsi'), # Approximate mapping if exact fields missing
                                "e45_cfg": None, # These detailed internal fields might not be in the simple screener dict
                                "e45_rsi": data.get('screener_ema45_rsi'),
                                "e20_sma3_rsi3": None
                            },
                            "trend_screener": {
                                "signal": data.get('trend_final_signal'),
                                "cci": data.get('trend_cci'),
                                "cci_ema20": None, # Missing in simple dict
                                "aroon_up": data.get('trend_aroon_up'),
                                "aroon_down": data.get('trend_aroon_down'),
                                "conditions": {} # Detailed conditions might be missing
                            },
                            "rsi_screener": {
                                "final_signal": data.get('screener_final_signal'),
                                "score": data.get('screener_score'),
                                "total_conditions": 0,
                                "stamp": data.get('screener_stamp'),
                                "stamp_daily": data.get('screener_stamp_daily'),
                                "stamp_weekly": data.get('screener_stamp_weekly'),
                                "daily": {
                                    "rsi": data.get('screener_rsi'),
                                    "sma9_rsi": data.get('screener_sma9_rsi'),
                                    "wma45_rsi": data.get('screener_wma45_rsi'),
                                    "ema45_rsi": data.get('screener_ema45_rsi'),
                                    "sma9_close": data.get('screener_sma9_close'),
                                    "the_number": data.get('screener_the_number'),
                                    "conditions": {
                                        "rsi_55_70": data.get('screener_rsi_55_70_d'),
                                        "sma9_gt_tn": data.get('screener_sma9_gt_tn_d'),
                                    }
                                },
                                "weekly": {
                                    "conditions": {
                                        "sma9_gt_tn": data.get('screener_sma9_gt_tn_w'),
                                    }
                                }
                            }
                        }
                    }
                    
                    # For full details (including all sub-conds), we actually need the FULL returned dict from calculate_all_indicators_for_stock
                    # The 'data' variable ALREADY contains everything!
                    # So we can just cache 'data' and let the API format it, OR format it here.
                    # Better approach: Cache the RAW data from calculate_all_indicators_for_stock
                    # because the API endpoint /stock/{symbol} calls calculate_all_indicators_for_stock directly and returns it.
                    
                    r.setex(
                        f"technical_screener:stock:{symbol}",
                        3600,
                        json.dumps(data, cls=DecimalEncoder)
                    )
                
                processed += 1
                if processed % 10 == 0:
                    print(f"   Processed {processed}/{total_symbols} stocks... (Elapsed: {time.time()-start_time:.1f}s)", end='\r')
                    
            except Exception as e:
                errors += 1
                # print(f"❌ Error processing {symbol}: {e}") # Reduce noise
        
        print(f"\n✅ Finished processing {processed} stocks with {errors} errors.")
        
        # Save to Redis
        print("💾 Saving to Redis Cache...")
        cache_key = "technical_screener:full_results"
        
        # Save directly using the synchronous connection
        r.setex(
            cache_key,
            3600, # 1 hour
            json.dumps(all_results, cls=DecimalEncoder)
        )
        
        duration = time.time() - start_time
        print(f"🎉 Done! Total time: {duration:.2f} seconds.")
        print("👉 You can now refresh the page to see the data immediately.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        r.close()

if __name__ == "__main__":
    warmup_cache()
