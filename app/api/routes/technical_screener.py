
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import date
import json
from decimal import Decimal
import numpy as np

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.redis import redis_cache
from app.models.price import Price
from app.services.technical_indicators import (
    calculate_all_indicators_for_stock,
    run_full_screener,
    RSIIndicator,
    TheNumberIndicator,
    StampIndicator,
    TrendScreener,
    RSIScreener,
    get_stock_prices,
    resample_to_weekly
)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

router = APIRouter(prefix="/technical-screener", tags=["Technical Screener"])

@router.get("/stock/{symbol}")
@limiter.limit("20/minute")
async def retrieve_stock_indicators(request: Request, symbol: str, db: Session = Depends(get_db)):
    """ Get all technical indicators for a specific stock """
    try:
        # Try Cache First
        cache_key = f"technical_screener:stock:{symbol}"
        cached_data = await redis_cache.get(cache_key)
        
        if cached_data:
            # redis_cache wrapper already deserializes if it's JSON
            data = cached_data
        else:
            # Verify symbol exists
            stock = db.query(Price).filter(Price.symbol == symbol).first()
            if not stock:
                raise HTTPException(status_code=404, detail="Stock not found")
        
            data = calculate_all_indicators_for_stock(db, symbol)
            if not data:
                # Cache empty result for short time to prevent spam
                await redis_cache.set(cache_key, {}, expire=60)
                raise HTTPException(status_code=404, detail="Insufficient data for calculation")
            
            # Cache result
            await redis_cache.set(cache_key, json.dumps(data, cls=DecimalEncoder), expire=3600)

        return {
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
                    "upper_band": None,
                    "lower_band": None
                },
                "stamp": {
                    "s9_rsi": data.get('screener_sma9_rsi'),
                    "e45_cfg": data.get('stamp_e45_cfg'),
                    "e45_rsi": data.get('screener_ema45_rsi'),
                    "e20_sma3_rsi3": data.get('stamp_e20_sma3_rsi3')
                },
                "trend_screener": {
                    "signal": data.get('trend_final_signal'),
                    "cci": data.get('trend_cci'),
                    "cci_ema20": data.get('trend_cci_ema20'),
                    "aroon_up": data.get('trend_aroon_up'),
                    "aroon_down": data.get('trend_aroon_down'),
                    "conditions": {
                        "price_gt_sma18": data.get('trend_price_gt_sma18'),
                        "sma_trend_daily": data.get('trend_sma_trend_daily'),
                        "cci_gt_100": data.get('trend_cci_gt_100'),
                        "cci_ema20_gt_0": data.get('trend_cci_ema20_gt_0_daily'),
                        "aroon_up_gt_70": data.get('trend_aroon_up_gt_70'),
                        "aroon_down_lt_30": data.get('trend_aroon_down_lt_30')
                    }
                },
                "rsi_screener": {
                    "final_signal": data.get('screener_final_signal'),
                    "score": data.get('screener_score'),
                    "total_conditions": data.get('screener_score'),
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
                            "rsi_lt_80": data.get('screener_rsi_lt_80_d'),
                            "sma9_rsi_lte_75": data.get('screener_sma9_rsi_lte_75_d'),
                            "ema45_rsi_lte_70": data.get('screener_ema45_rsi_lte_70_d'),
                            "rsi_55_70": data.get('screener_rsi_55_70_d'),
                            "rsi_gt_wma45": data.get('screener_rsi_gt_wma45_d'),
                            "sma9rsi_gt_wma45rsi": data.get('screener_sma9rsi_gt_wma45rsi_d'),
                            "sma9_gt_tn": data.get('screener_sma9_gt_tn_d')
                        }
                    },
                    "weekly": {
                        "rsi": data.get('screener_rsi_w'),
                        "sma9_rsi": data.get('screener_sma9_rsi_w'),
                        "wma45_rsi": data.get('screener_wma45_rsi_w'),
                        "ema45_rsi": data.get('screener_ema45_rsi_w'),
                        "sma9_close": data.get('screener_sma9_close_w'),
                        "the_number": data.get('screener_the_number_w'),
                        "conditions": {
                            "rsi_lt_80": data.get('screener_rsi_lt_80_w'),
                            "sma9_rsi_lte_75": data.get('screener_sma9_rsi_lte_75_w'),
                            "ema45_rsi_lte_70": data.get('screener_ema45_rsi_lte_70_w'),
                            "rsi_gt_wma45": data.get('screener_rsi_gt_wma45_w'),
                            "sma9rsi_gt_wma45rsi": data.get('screener_sma9rsi_gt_wma45rsi_w'),
                            "sma9_gt_tn": data.get('screener_sma9_gt_tn_w')
                        }
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener")
@limiter.limit("10/minute")
async def get_screener_results(
    request: Request,
    min_score: Optional[int] = Query(None, ge=0, le=15, description="Minimum score (out of 15)"),
    passing_only: bool = Query(False, description="Only show stocks passing all conditions"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Run the full RSI Screener on all stocks.
    
    Returns stocks sorted by screener score.
    """
    try:
        cache_key = "technical_screener:full_results"
        cached_data = await redis_cache.get(cache_key)
        
        if cached_data:
            all_results = cached_data
        else:
            # Get all symbols with company names
            symbols_query = text("""
                SELECT DISTINCT p.symbol, p.company_name
                FROM prices p
                WHERE p.date = (SELECT MAX(date) FROM prices)
            """)
            symbols_result = db.execute(symbols_query)
            symbols_data = {row[0]: row[1] for row in symbols_result.fetchall()}
            
            all_results = []
            
            for symbol in symbols_data.keys():
                try:
                    data = calculate_all_indicators_for_stock(db, symbol)
                    if data:
                        item = {
                            'symbol': symbol,
                            'company_name': symbols_data.get(symbol),
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
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
                    continue
            
            # Cache for 1 hour (3600 seconds)
            await redis_cache.set(cache_key, json.dumps(all_results, cls=DecimalEncoder), expire=3600)
        
        # Filter by min_score
        filtered_results = all_results
        if min_score is not None:
            filtered_results = [r for r in filtered_results if r.get('score', 0) >= min_score]
        
        # Filter by passing_only
        if passing_only:
            filtered_results = [r for r in filtered_results if r.get('final_signal', False)]
        
        # Sort by score descending
        filtered_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Count passing
        passing_count = len([r for r in all_results if r.get('final_signal', False)])
        
        # Get latest date
        latest_date = all_results[0]['date'] if all_results else str(date.today())
        
        # Apply pagination
        paginated = filtered_results[offset:offset + limit]
        
        return {
            "data": paginated,
            "total_count": len(filtered_results),
            "passing_count": passing_count,
            "date": latest_date
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


@router.get("/quick-scan")
@limiter.limit("20/minute")
async def quick_scan(
    request: Request,
    screener_type: str = Query(..., regex="^(rsi|trend)$"),
    db: Session = Depends(get_db)
):
    """
    Run a quick scan for a specific screener type.
    """
    try:
        # Get all symbols
        symbols_query = text("SELECT DISTINCT symbol, company_name FROM prices WHERE date = (SELECT MAX(date) FROM prices)")
        result = db.execute(symbols_query)
        symbols_data = {row[0]: row[1] for row in result.fetchall()}
        
        passing = []
        
        for symbol, company_name in symbols_data.items():
            try:
                # Optimized: We might want separate specialized functions for quick scanning
                # For now, reuse the main calculation but only extract what's needed
                data = calculate_all_indicators_for_stock(db, symbol)
                if not data:
                    continue
                
                close_price = data.get('close')
                
                if screener_type == "rsi":
                    # For RSI screener, return if score >= 10 (example threshold)
                    if data.get('screener_score', 0) >= 10:
                        passing.append({
                            'symbol': symbol,
                            'company_name': company_name,
                            'close': close_price,
                            'rsi': data.get('screener_rsi'),
                            'score': data.get('screener_score', 0),
                        })
                elif screener_type == "trend":
                    if data.get('trend_final_signal', False):
                        passing.append({
                            'symbol': symbol,
                            'company_name': company_name,
                            'close': close_price,
                            'cci': data.get('trend_cci'),
                            'aroon_up': data.get('trend_aroon_up'),
                        })
            except Exception as e:
                continue
        
        # Sort by score/relevant metric
        if screener_type == "rsi":
            passing.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            "screener_type": screener_type,
            "count": len(passing),
            "stocks": passing
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


@router.get("/conditions-summary")
@limiter.limit("30/minute")
async def get_conditions_summary(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get a summary of how many stocks pass each condition.
    """
    try:
        # Get all symbols
        symbols_query = text("SELECT DISTINCT symbol FROM prices WHERE date = (SELECT MAX(date) FROM prices)")
        result = db.execute(symbols_query)
        symbols = [row[0] for row in result.fetchall()]
        
        # Initialize condition counts
        conditions = {
            'stamp_daily': 0,
            'stamp_weekly': 0,
            'stamp': 0,
            'sma9_gt_tn_d': 0,
            'sma9_gt_tn_w': 0,
            'rsi_lt_80_d': 0,
            'rsi_lt_80_w': 0,
            'sma9_rsi_lte_75_d': 0,
            'sma9_rsi_lte_75_w': 0,
            'ema45_rsi_lte_70_d': 0,
            'ema45_rsi_lte_70_w': 0,
            'rsi_55_70_d': 0,
            'rsi_gt_wma45_d': 0,
            'rsi_gt_wma45_w': 0,
            'final_signal': 0,
            'trend_signal': 0,
        }
        
        total_processed = 0
        
        for symbol in symbols:
            try:
                data = calculate_all_indicators_for_stock(db, symbol)
                if not data:
                    continue
                
                total_processed += 1
                
                if data.get('screener_stamp_daily'): conditions['stamp_daily'] += 1
                if data.get('screener_stamp_weekly'): conditions['stamp_weekly'] += 1
                if data.get('screener_stamp'): conditions['stamp'] += 1
                if data.get('screener_sma9_gt_tn_d'): conditions['sma9_gt_tn_d'] += 1
                if data.get('screener_sma9_gt_tn_w'): conditions['sma9_gt_tn_w'] += 1
                if data.get('screener_rsi_lt_80_d'): conditions['rsi_lt_80_d'] += 1
                if data.get('screener_rsi_lt_80_w'): conditions['rsi_lt_80_w'] += 1
                if data.get('screener_sma9_rsi_lte_75_d'): conditions['sma9_rsi_lte_75_d'] += 1
                if data.get('screener_sma9_rsi_lte_75_w'): conditions['sma9_rsi_lte_75_w'] += 1
                if data.get('screener_ema45_rsi_lte_70_d'): conditions['ema45_rsi_lte_70_d'] += 1
                if data.get('screener_ema45_rsi_lte_70_w'): conditions['ema45_rsi_lte_70_w'] += 1
                if data.get('screener_rsi_55_70_d'): conditions['rsi_55_70_d'] += 1
                if data.get('screener_rsi_gt_wma45_d'): conditions['rsi_gt_wma45_d'] += 1
                if data.get('screener_rsi_gt_wma45_w'): conditions['rsi_gt_wma45_w'] += 1
                if data.get('screener_final_signal'): conditions['final_signal'] += 1
                if data.get('trend_final_signal'): conditions['trend_signal'] += 1
                
            except Exception as e:
                continue
        
        # Calculate percentages
        summary = []
        for condition, count in conditions.items():
            summary.append({
                'condition': condition,
                'count': count,
                'percentage': round((count / total_processed * 100), 1) if total_processed > 0 else 0
            })
        
        return {
            'total_stocks': total_processed,
            'conditions': summary
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
