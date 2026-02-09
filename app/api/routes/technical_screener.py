
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from typing import List, Optional, Dict, Any
from datetime import date
import json
from decimal import Decimal
import numpy as np

from app.core.database import get_db
from app.core.limiter import limiter
from app.models.stock_indicators import StockIndicator

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


def indicator_to_dict(ind: StockIndicator) -> dict:
    """Convert StockIndicator model to dictionary"""
    return {
        'symbol': ind.symbol,
        'company_name': ind.company_name,
        'date': str(ind.date) if ind.date else None,
        'close': float(ind.close) if ind.close else None,
        
        # RSI Values
        'rsi': float(ind.rsi_14) if ind.rsi_14 else None,
        'sma9_rsi': float(ind.sma9_rsi) if ind.sma9_rsi else None,
        'wma45_rsi': float(ind.wma45_rsi) if ind.wma45_rsi else None,
        'ema45_rsi': float(ind.ema45_rsi) if ind.ema45_rsi else None,
        
        # The Number
        'sma9_close': float(ind.sma9_close) if ind.sma9_close else None,
        'the_number': float(ind.the_number) if ind.the_number else None,
        
        # STAMP
        'stamp': bool(ind.stamp),
        'stamp_daily': bool(ind.stamp_daily),
        'stamp_weekly': bool(ind.stamp_weekly),
        
        # Conditions
        'rsi_55_70': bool(ind.rsi_55_70),
        'sma9_gt_tn_daily': bool(ind.sma9_gt_tn_daily),
        'sma9_gt_tn_weekly': bool(ind.sma9_gt_tn_weekly),
        
        # Trend
        'cci': float(ind.cci) if ind.cci else None,
        'aroon_up': float(ind.aroon_up) if ind.aroon_up else None,
        'aroon_down': float(ind.aroon_down) if ind.aroon_down else None,
        'trend_signal': bool(ind.trend_signal),
        
        # Final
        'final_signal': bool(ind.final_signal),
        'score': int(ind.score) if ind.score else 0,
        
        # Weekly Values
        'rsi_w': float(ind.rsi_w) if ind.rsi_w else None,
        'sma9_rsi_w': float(ind.sma9_rsi_w) if ind.sma9_rsi_w else None,
        'wma45_rsi_w': float(ind.wma45_rsi_w) if ind.wma45_rsi_w else None,
        'ema45_rsi_w': float(ind.ema45_rsi_w) if ind.ema45_rsi_w else None,
        'sma9_close_w': float(ind.sma9_close_w) if ind.sma9_close_w else None,
        'the_number_w': float(ind.the_number_w) if ind.the_number_w else None,
        
        # Daily Conditions
        'rsi_lt_80_d': bool(ind.rsi_lt_80_d),
        'sma9_rsi_lte_75_d': bool(ind.sma9_rsi_lte_75_d),
        'ema45_rsi_lte_70_d': bool(ind.ema45_rsi_lte_70_d),
        'rsi_gt_wma45_d': bool(ind.rsi_gt_wma45_d),
        'sma9rsi_gt_wma45rsi_d': bool(ind.sma9rsi_gt_wma45rsi_d),
        
        # Weekly Conditions
        'rsi_lt_80_w': bool(ind.rsi_lt_80_w),
        'sma9_rsi_lte_75_w': bool(ind.sma9_rsi_lte_75_w),
        'ema45_rsi_lte_70_w': bool(ind.ema45_rsi_lte_70_w),
        'rsi_gt_wma45_w': bool(ind.rsi_gt_wma45_w),
        'sma9rsi_gt_wma45rsi_w': bool(ind.sma9rsi_gt_wma45rsi_w),
    }


@router.get("/stock/{symbol}")
@limiter.limit("60/minute")
async def retrieve_stock_indicators(request: Request, symbol: str, db: Session = Depends(get_db)):
    """ Get all technical indicators for a specific stock from pre-computed database """
    try:
        # Get latest indicator for this symbol
        indicator = db.query(StockIndicator).filter(
            StockIndicator.symbol == symbol
        ).order_by(desc(StockIndicator.date)).first()
        
        if not indicator:
            raise HTTPException(status_code=404, detail="Stock not found or no indicators available")
        
        data = indicator_to_dict(indicator)
        
        return {
            "symbol": symbol,
            "date": data.get('date'),
            "close": data.get('close'),
            "indicators": {
                "rsi": {
                    "rsi": data.get('rsi'),
                    "sma9": data.get('sma9_rsi'),
                    "wma45": data.get('wma45_rsi')
                },
                "the_number": {
                    "sma9": data.get('sma9_close'),
                    "value": data.get('the_number'),
                    "upper_band": None,
                    "lower_band": None
                },
                "stamp": {
                    "s9_rsi": data.get('sma9_rsi'),
                    "e45_cfg": None,
                    "e45_rsi": data.get('ema45_rsi'),
                    "e20_sma3_rsi3": None
                },
                "trend_screener": {
                    "signal": data.get('trend_signal'),
                    "cci": data.get('cci'),
                    "cci_ema20": None,
                    "aroon_up": data.get('aroon_up'),
                    "aroon_down": data.get('aroon_down'),
                    "conditions": {
                        "price_gt_sma18": None,
                        "sma_trend_daily": None,
                        "cci_gt_100": None,
                        "cci_ema20_gt_0": None,
                        "aroon_up_gt_70": None,
                        "aroon_down_lt_30": None
                    }
                },
                "rsi_screener": {
                    "final_signal": data.get('final_signal'),
                    "score": data.get('score'),
                    "total_conditions": data.get('score'),
                    "stamp": data.get('stamp'),
                    "stamp_daily": data.get('stamp_daily'),
                    "stamp_weekly": data.get('stamp_weekly'),
                    "daily": {
                        "rsi": data.get('rsi'),
                        "sma9_rsi": data.get('sma9_rsi'),
                        "wma45_rsi": data.get('wma45_rsi'),
                        "ema45_rsi": data.get('ema45_rsi'),
                        "sma9_close": data.get('sma9_close'),
                        "the_number": data.get('the_number'),
                        "conditions": {
                            "rsi_lt_80": data.get('rsi_lt_80_d'),
                            "sma9_rsi_lte_75": data.get('sma9_rsi_lte_75_d'),
                            "ema45_rsi_lte_70": data.get('ema45_rsi_lte_70_d'),
                            "rsi_55_70": data.get('rsi_55_70'),
                            "rsi_gt_wma45": data.get('rsi_gt_wma45_d'),
                            "sma9rsi_gt_wma45rsi": data.get('sma9rsi_gt_wma45rsi_d'),
                            "sma9_gt_tn": data.get('sma9_gt_tn_daily')
                        }
                    },
                    "weekly": {
                        "rsi": data.get('rsi_w'),
                        "sma9_rsi": data.get('sma9_rsi_w'),
                        "wma45_rsi": data.get('wma45_rsi_w'),
                        "ema45_rsi": data.get('ema45_rsi_w'),
                        "sma9_close": data.get('sma9_close_w'),
                        "the_number": data.get('the_number_w'),
                        "conditions": {
                            "rsi_lt_80": data.get('rsi_lt_80_w'),
                            "sma9_rsi_lte_75": data.get('sma9_rsi_lte_75_w'),
                            "ema45_rsi_lte_70": data.get('ema45_rsi_lte_70_w'),
                            "rsi_gt_wma45": data.get('rsi_gt_wma45_w'),
                            "sma9rsi_gt_wma45rsi": data.get('sma9rsi_gt_wma45rsi_w'),
                            "sma9_gt_tn": data.get('sma9_gt_tn_weekly')
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
@limiter.limit("30/minute")
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
    Now reads from pre-computed database table instead of calculating on-the-fly.
    
    Returns stocks sorted by screener score.
    """
    try:
        # Get latest date
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        # Build base query
        query = db.query(StockIndicator).filter(StockIndicator.date == latest_date)
        
        # Apply filters
        if min_score is not None:
            query = query.filter(StockIndicator.score >= min_score)
        
        if passing_only:
            query = query.filter(StockIndicator.final_signal == True)
        
        # Get total counts (before pagination)
        total_count = query.count()
        passing_count = db.query(StockIndicator).filter(
            StockIndicator.date == latest_date,
            StockIndicator.final_signal == True
        ).count()
        
        # Sort by score descending and apply pagination
        indicators = query.order_by(desc(StockIndicator.score)).offset(offset).limit(limit).all()
        
        # Convert to dicts
        all_results = [indicator_to_dict(ind) for ind in indicators]
        
        return {
            "data": all_results,
            "total_count": total_count,
            "passing_count": passing_count,
            "date": str(latest_date)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


@router.get("/quick-scan")
@limiter.limit("30/minute")
async def quick_scan(
    request: Request,
    screener_type: str = Query(..., regex="^(rsi|trend)$"),
    db: Session = Depends(get_db)
):
    """
    Run a quick scan for a specific screener type.
    Now reads from pre-computed database table.
    """
    try:
        # Get latest date
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        # Build query based on screener type
        if screener_type == "rsi":
            # RSI screener: score >= 10
            indicators = db.query(StockIndicator).filter(
                StockIndicator.date == latest_date,
                StockIndicator.score >= 10
            ).order_by(desc(StockIndicator.score)).all()
            
            passing = [{
                'symbol': ind.symbol,
                'company_name': ind.company_name,
                'close': float(ind.close) if ind.close else None,
                'rsi': float(ind.rsi_14) if ind.rsi_14 else None,
                'score': int(ind.score) if ind.score else 0,
            } for ind in indicators]
            
        elif screener_type == "trend":
            # Trend screener: trend_signal = True
            indicators = db.query(StockIndicator).filter(
                StockIndicator.date == latest_date,
                StockIndicator.trend_signal == True
            ).order_by(desc(StockIndicator.cci)).all()
            
            passing = [{
                'symbol': ind.symbol,
                'company_name': ind.company_name,
                'close': float(ind.close) if ind.close else None,
                'cci': float(ind.cci) if ind.cci else None,
                'aroon_up': float(ind.aroon_up) if ind.aroon_up else None,
            } for ind in indicators]
        
        return {
            "screener_type": screener_type,
            "count": len(passing),
            "stocks": passing
        }
        
    except HTTPException:
        raise
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
    Now reads from pre-computed database table.
    """
    try:
        # Get latest date
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        # Get all indicators for latest date
        indicators = db.query(StockIndicator).filter(StockIndicator.date == latest_date).all()
        
        total_processed = len(indicators)
        
        # Count conditions
        conditions = {
            'stamp_daily': sum(1 for ind in indicators if ind.stamp_daily),
            'stamp_weekly': sum(1 for ind in indicators if ind.stamp_weekly),
            'stamp': sum(1 for ind in indicators if ind.stamp),
            'sma9_gt_tn_d': sum(1 for ind in indicators if ind.sma9_gt_tn_daily),
            'sma9_gt_tn_w': sum(1 for ind in indicators if ind.sma9_gt_tn_weekly),
            'rsi_lt_80_d': sum(1 for ind in indicators if ind.rsi_lt_80_d),
            'rsi_lt_80_w': sum(1 for ind in indicators if ind.rsi_lt_80_w),
            'sma9_rsi_lte_75_d': sum(1 for ind in indicators if ind.sma9_rsi_lte_75_d),
            'sma9_rsi_lte_75_w': sum(1 for ind in indicators if ind.sma9_rsi_lte_75_w),
            'ema45_rsi_lte_70_d': sum(1 for ind in indicators if ind.ema45_rsi_lte_70_d),
            'ema45_rsi_lte_70_w': sum(1 for ind in indicators if ind.ema45_rsi_lte_70_w),
            'rsi_55_70_d': sum(1 for ind in indicators if ind.rsi_55_70),
            'rsi_gt_wma45_d': sum(1 for ind in indicators if ind.rsi_gt_wma45_d),
            'rsi_gt_wma45_w': sum(1 for ind in indicators if ind.rsi_gt_wma45_w),
            'final_signal': sum(1 for ind in indicators if ind.final_signal),
            'trend_signal': sum(1 for ind in indicators if ind.trend_signal),
        }
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


@router.get("/history/{symbol}")
@limiter.limit("30/minute")
async def get_stock_indicator_history(
    request: Request,
    symbol: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get historical indicators for a specific stock.
    This is a NEW endpoint that leverages the historical data storage.
    """
    try:
        # Get indicators for this symbol, ordered by date
        indicators = db.query(StockIndicator).filter(
            StockIndicator.symbol == symbol
        ).order_by(desc(StockIndicator.date)).limit(days).all()
        
        if not indicators:
            raise HTTPException(status_code=404, detail="No indicator data found for this symbol")
        
        history = [{
            'date': str(ind.date),
            'close': float(ind.close) if ind.close else None,
            'rsi': float(ind.rsi_14) if ind.rsi_14 else None,
            'score': int(ind.score) if ind.score else 0,
            'stamp': bool(ind.stamp),
            'final_signal': bool(ind.final_signal),
            'trend_signal': bool(ind.trend_signal),
        } for ind in indicators]
        
        return {
            'symbol': symbol,
            'company_name': indicators[0].company_name if indicators else None,
            'data_points': len(history),
            'history': history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
