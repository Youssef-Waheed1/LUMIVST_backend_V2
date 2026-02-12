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
    """✅ تحويل جميع المؤشرات إلى Dictionary - نسخة كاملة مع aliases للـ Frontend"""
    return {
        'symbol': ind.symbol,
        'company_name': ind.company_name,
        'date': str(ind.date) if ind.date else None,
        'close': float(ind.close) if ind.close else None,
        
        # ===== 1. RSI Indicator =====
        'rsi': float(ind.rsi_14) if ind.rsi_14 else None,  # ✅ Alias for Frontend
        'rsi_14': float(ind.rsi_14) if ind.rsi_14 else None,
        'sma9_rsi': float(ind.sma9_rsi) if ind.sma9_rsi else None,
        'wma45_rsi': float(ind.wma45_rsi) if ind.wma45_rsi else None,
        
        # ===== 2. The Number =====
        'sma9_close': float(ind.sma9_close) if ind.sma9_close else None,
        'the_number': float(ind.the_number) if ind.the_number else None,
        'the_number_hl': float(ind.the_number_hl) if ind.the_number_hl else None,
        'the_number_ll': float(ind.the_number_ll) if ind.the_number_ll else None,
        
        # ===== 3. Stamp Indicator =====
        'rsi_14_9days_ago': float(ind.rsi_14_9days_ago) if ind.rsi_14_9days_ago else None,
        'rsi_14_9_days_ago': float(ind.rsi_14_9days_ago) if ind.rsi_14_9days_ago else None,  # ✅ Alias
        'rsi_3': float(ind.rsi_3) if ind.rsi_3 else None,
        'sma3_rsi3': float(ind.sma3_rsi3) if ind.sma3_rsi3 else None,
        'stamp_a_value': float(ind.stamp_a_value) if ind.stamp_a_value else None,
        'stamp_s9rsi': float(ind.stamp_s9rsi) if ind.stamp_s9rsi else None,
        'stamp_e45cfg': float(ind.stamp_e45cfg) if ind.stamp_e45cfg else None,
        'stamp_e45rsi': float(ind.stamp_e45rsi) if ind.stamp_e45rsi else None,
        'stamp_e20sma3': float(ind.stamp_e20sma3) if ind.stamp_e20sma3 else None,
        
        # ===== 4. Trend Screener =====
        'sma4': float(ind.sma4) if ind.sma4 else None,
        'sma9': float(ind.sma9) if ind.sma9 else None,
        'sma18': float(ind.sma18) if ind.sma18 else None,
        'sma4_w': float(ind.sma4_w) if ind.sma4_w else None,
        'sma9_w': float(ind.sma9_w) if ind.sma9_w else None,
        'sma18_w': float(ind.sma18_w) if ind.sma18_w else None,
        'close_w': float(ind.close_w) if ind.close_w else None,
        'cci': float(ind.cci) if ind.cci else None,
        'cci_ema20': float(ind.cci_ema20) if ind.cci_ema20 else None,
        'cci_ema20_w': float(ind.cci_ema20_w) if ind.cci_ema20_w else None,
        'aroon_up': float(ind.aroon_up) if ind.aroon_up else None,
        'aroon_down': float(ind.aroon_down) if ind.aroon_down else None,
        'aroon_up_w': float(ind.aroon_up_w) if ind.aroon_up_w else None,
        'aroon_down_w': float(ind.aroon_down_w) if ind.aroon_down_w else None,
        
        # Trend Conditions
        'price_gt_sma18': bool(ind.price_gt_sma18),
        'price_gt_sma9_weekly': bool(ind.price_gt_sma9_weekly),
        'sma_trend_daily': bool(ind.sma_trend_daily),
        'sma_trend_weekly': bool(ind.sma_trend_weekly),
        'cci_gt_100': bool(ind.cci_gt_100),
        'cci_ema20_gt_0_daily': bool(ind.cci_ema20_gt_0_daily),
        'cci_ema20_gt_0_weekly': bool(ind.cci_ema20_gt_0_weekly),
        'aroon_up_gt_70': bool(ind.aroon_up_gt_70),
        'aroon_down_lt_30': bool(ind.aroon_down_lt_30),
        'is_etf_or_index': bool(ind.is_etf_or_index),
        'has_gap': bool(ind.has_gap),
        'trend_signal': bool(ind.trend_signal),
        
        # ===== 5. RSI Screener =====
        'wma45_rsi_screener': float(ind.wma45_rsi) if ind.wma45_rsi else None,
        'ema45_rsi': float(ind.ema45_rsi) if ind.ema45_rsi else None,
        'cfg_ema45': float(ind.cfg_ema45) if ind.cfg_ema45 is not None else None,
        'e45_cfg': float(ind.cfg_ema45) if ind.cfg_ema45 is not None else None,  # ✅ Alias for Frontend
        'cfg_wma45': float(ind.cfg_wma45) if ind.cfg_wma45 is not None else None,
        'w45_cfg': float(ind.cfg_wma45) if ind.cfg_wma45 is not None else None,  # ✅ Alias for Frontend
        'ema20_sma3': float(ind.ema20_sma3) if ind.ema20_sma3 is not None else None,
        'e20_sma3_rsi3': float(ind.ema20_sma3) if ind.ema20_sma3 is not None else None,  # ✅ Alias for Frontend
        'wma45_close': float(ind.wma45_close) if ind.wma45_close else None,
        
        # Weekly Values
        'rsi_w': float(ind.rsi_w) if ind.rsi_w else None,
        'rsi_3_w': float(ind.rsi_3_w) if ind.rsi_3_w else None,
        'sma3_rsi3_w': float(ind.sma3_rsi3_w) if ind.sma3_rsi3_w else None,
        'sma9_rsi_w': float(ind.sma9_rsi_w) if ind.sma9_rsi_w else None,
        'wma45_rsi_w': float(ind.wma45_rsi_w) if ind.wma45_rsi_w else None,
        'ema45_rsi_w': float(ind.ema45_rsi_w) if ind.ema45_rsi_w else None,
        'cfg_ema45_w': float(ind.cfg_ema45_w) if ind.cfg_ema45_w is not None else None,
        'ema45_cfg_w': float(ind.cfg_ema45_w) if ind.cfg_ema45_w is not None else None,
        'cfg_wma45_w': float(ind.cfg_wma45_w) if ind.cfg_wma45_w is not None else None,
        'wma45_cfg_w': float(ind.cfg_wma45_w) if ind.cfg_wma45_w is not None else None,  # ✅ Alias for Frontend
        'ema20_sma3_w': float(ind.ema20_sma3_w) if ind.ema20_sma3_w is not None else None,
        'ema20_sma3_rsi3_w': float(ind.ema20_sma3_w) if ind.ema20_sma3_w is not None else None,  # ✅ Alias for Frontend
        'sma9_close_w': float(ind.sma9_close_w) if ind.sma9_close_w else None,
        'wma45_close_w': float(ind.wma45_close_w) if ind.wma45_close_w else None,
        'the_number_w': float(ind.the_number_w) if ind.the_number_w else None,
        
        # RSI Screener Conditions
        'sma9_gt_tn_daily': bool(ind.sma9_gt_tn_daily),
        'sma9_gt_tn_weekly': bool(ind.sma9_gt_tn_weekly),
        'rsi_lt_80_d': bool(ind.rsi_lt_80_d),
        'rsi_lt_80_w': bool(ind.rsi_lt_80_w),
        'sma9_rsi_lte_75_d': bool(ind.sma9_rsi_lte_75_d),
        'sma9_rsi_lte_75_w': bool(ind.sma9_rsi_lte_75_w),
        'ema45_rsi_lte_70_d': bool(ind.ema45_rsi_lte_70_d),
        'ema45_rsi_lte_70_w': bool(ind.ema45_rsi_lte_70_w),
        'rsi_55_70': bool(ind.rsi_55_70),
        'rsi_gt_wma45_d': bool(ind.rsi_gt_wma45_d),
        'rsi_gt_wma45_w': bool(ind.rsi_gt_wma45_w),
        'sma9rsi_gt_wma45rsi_d': bool(ind.sma9rsi_gt_wma45rsi_d),
        'sma9rsi_gt_wma45rsi_w': bool(ind.sma9rsi_gt_wma45rsi_w),
        
        # STAMP Conditions
        'stamp_daily': bool(ind.stamp_daily),
        'stamp_weekly': bool(ind.stamp_weekly),
        'stamp': bool(ind.stamp),
        
        # ===== 6. CFG Analysis =====
        'cfg_daily': float(ind.cfg_daily) if ind.cfg_daily is not None else None,
        'cfg_sma9': float(ind.cfg_sma9) if ind.cfg_sma9 is not None else None,
        'cfg_sma20': float(ind.cfg_sma20) if ind.cfg_sma20 is not None else None,
        'cfg_ema20': float(ind.cfg_ema20) if ind.cfg_ema20 is not None else None,
        'cfg_ema45': float(ind.cfg_ema45) if ind.cfg_ema45 is not None else None,
        'cfg_w': float(ind.cfg_w) if ind.cfg_w is not None else None,
        'cfg_weekly': float(ind.cfg_w) if ind.cfg_w is not None else None,  # ✅ Alias for Frontend
        'cfg_sma9_w': float(ind.cfg_sma9_w) if ind.cfg_sma9_w is not None else None,
        'cfg_ema20_w': float(ind.cfg_ema20_w) if ind.cfg_ema20_w is not None else None,
        'cfg_ema45_w': float(ind.cfg_ema45_w) if ind.cfg_ema45_w is not None else None,
        
        # CFG Conditions
        'cfg_gt_50_daily': bool(ind.cfg_gt_50_daily),
        'cfg_gt_50_weekly': bool(ind.cfg_gt_50_w),  # ✅ Alias for Frontend
        'cfg_ema45_gt_50': bool(ind.cfg_ema45_gt_50),
        'cfg_ema20_gt_50': bool(ind.cfg_ema20_gt_50),
        'cfg_gt_50_w': bool(ind.cfg_gt_50_w),
        'cfg_ema45_gt_50_w': bool(ind.cfg_ema45_gt_50_w),
        'cfg_ema20_gt_50_w': bool(ind.cfg_ema20_gt_50_w),
        
        # CFG Components
        'rsi_14_shifted': float(ind.rsi_14_9days_ago_cfg) if ind.rsi_14_9days_ago_cfg is not None else None,  # ✅ Alias
        'rsi_14_9days_ago_cfg': float(ind.rsi_14_9days_ago_cfg) if ind.rsi_14_9days_ago_cfg is not None else None,
        'rsi_14_w_shifted': float(ind.rsi_14_w_shifted) if ind.rsi_14_w_shifted is not None else None,
        'rsi_14_minus_9': float(ind.rsi_14_minus_9) if ind.rsi_14_minus_9 is not None else None,
        'rsi_14_minus_9_w': float(ind.rsi_14_minus_9_w) if ind.rsi_14_minus_9_w is not None else None,
        
        # Final Results
        'final_signal': bool(ind.final_signal),
        'score': int(ind.score) if ind.score else 0,
    }


@router.get("/stock/{symbol}")
@limiter.limit("60/minute")
async def retrieve_stock_indicators(request: Request, symbol: str, db: Session = Depends(get_db)):
    """✅ Get all technical indicators for a specific stock"""
    try:
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
                "rsi_indicator": {
                    "rsi_14": data.get('rsi_14'),
                    "sma9_rsi": data.get('sma9_rsi'),
                    "wma45_rsi": data.get('wma45_rsi'),
                },
                "the_number": {
                    "sma9": data.get('sma9_close'),
                    "value": data.get('the_number'),
                    "upper_band": data.get('the_number_hl'),
                    "lower_band": data.get('the_number_ll'),
                },
                "stamp": {
                    "a_value": data.get('stamp_a_value'),
                    "s9rsi": data.get('stamp_s9rsi'),
                    "e45cfg": data.get('stamp_e45cfg'),
                    "e45rsi": data.get('stamp_e45rsi'),
                    "e20sma3": data.get('stamp_e20sma3'),
                    "rsi14_9days_ago": data.get('rsi_14_9days_ago'),
                    "sma3_rsi3": data.get('sma3_rsi3'),
                },
                "trend_screener": {
                    "signal": data.get('trend_signal'),
                    "cci": data.get('cci'),
                    "cci_ema20": data.get('cci_ema20'),
                    "cci_ema20_w": data.get('cci_ema20_w'),
                    "aroon_up": data.get('aroon_up'),
                    "aroon_down": data.get('aroon_down'),
                    "aroon_up_w": data.get('aroon_up_w'),
                    "aroon_down_w": data.get('aroon_down_w'),
                    "conditions": {
                        "price_gt_sma18": data.get('price_gt_sma18'),
                        "price_gt_sma9_weekly": data.get('price_gt_sma9_weekly'),
                        "sma_trend_daily": data.get('sma_trend_daily'),
                        "sma_trend_weekly": data.get('sma_trend_weekly'),
                        "cci_gt_100": data.get('cci_gt_100'),
                        "cci_ema20_gt_0_daily": data.get('cci_ema20_gt_0_daily'),
                        "cci_ema20_gt_0_weekly": data.get('cci_ema20_gt_0_weekly'),
                        "aroon_up_gt_70": data.get('aroon_up_gt_70'),
                        "aroon_down_lt_30": data.get('aroon_down_lt_30'),
                    }
                },
                "rsi_screener": {
                    "final_signal": data.get('final_signal'),
                    "score": data.get('score'),
                    "stamp": data.get('stamp'),
                    "stamp_daily": data.get('stamp_daily'),
                    "stamp_weekly": data.get('stamp_weekly'),
                    "cfg": {
                        "cfg": data.get('cfg_daily'),
                        "cfg_ema45": data.get('cfg_ema45'),
                        "cfg_gt_50": data.get('cfg_gt_50_daily'),
                        "cfg_ema45_gt_50": data.get('cfg_ema45_gt_50'),
                    },
                    "daily": {
                        "rsi": data.get('rsi_14'),
                        "sma9_rsi": data.get('sma9_rsi'),
                        "wma45_rsi": data.get('wma45_rsi_screener'),
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
                },
                "cfg_analysis": {
                    "daily": {
                        "cfg": data.get('cfg_daily'),
                        "cfg_sma9": data.get('cfg_sma9'),
                        "cfg_sma20": data.get('cfg_sma20'),
                        "cfg_ema20": data.get('cfg_ema20'),
                        "cfg_ema45": data.get('cfg_ema45'),
                        "rsi14_current": data.get('rsi_14'),
                        "rsi14_9days_ago": data.get('rsi_14_9days_ago_cfg'),
                        "rsi14_minus_9": data.get('rsi_14_minus_9'),
                        "sma3_rsi3": data.get('sma3_rsi3'),
                        "conditions": {
                            "cfg_gt_50": data.get('cfg_gt_50_daily'),
                            "cfg_ema45_gt_50": data.get('cfg_ema45_gt_50'),
                        }
                    },
                    "weekly": {
                        "cfg": data.get('cfg_w'),
                        "cfg_sma9": data.get('cfg_sma9_w'),
                        "cfg_ema20": data.get('cfg_ema20_w'),
                        "cfg_ema45": data.get('cfg_ema45_w'),
                        "rsi14_current": data.get('rsi_w'),
                        "rsi14_weekly_shifted": data.get('rsi_14_w_shifted'),  # ✅ ta.rsi(close[9], 14)
                        "rsi14_9weeks_ago": data.get('rsi_14_minus_9_w'),      # ⚠️ 
                        "conditions": {
                            "cfg_gt_50": data.get('cfg_gt_50_w'),
                            "cfg_ema45_gt_50": data.get('cfg_ema45_gt_50_w'),
                        }
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener")
@limiter.limit("30/minute")
async def get_screener_results(
    request: Request,
    min_score: Optional[int] = Query(None, ge=0, le=15),
    passing_only: bool = Query(False),
    cfg_filter: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """✅ Run the full RSI Screener on all stocks"""
    try:
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        query = db.query(StockIndicator).filter(StockIndicator.date == latest_date)
        
        if min_score is not None:
            query = query.filter(StockIndicator.score >= min_score)
        
        if passing_only:
            query = query.filter(StockIndicator.final_signal == True)
        
        if cfg_filter == "cfg_gt_50":
            query = query.filter(StockIndicator.cfg_gt_50_daily == True)
        elif cfg_filter == "cfg_ema45_gt_50":
            query = query.filter(StockIndicator.cfg_ema45_gt_50 == True)
        
        total_count = query.count()
        passing_count = db.query(StockIndicator).filter(
            StockIndicator.date == latest_date,
            StockIndicator.final_signal == True
        ).count()
        
        indicators = query.order_by(desc(StockIndicator.score)).offset(offset).limit(limit).all()
        all_results = [indicator_to_dict(ind) for ind in indicators]
        
        return {
            "data": all_results,
            "total_count": total_count,
            "passing_count": passing_count,
            "date": str(latest_date)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")


@router.get("/quick-scan")
@limiter.limit("30/minute")
async def quick_scan(
    request: Request,
    screener_type: str = Query(..., regex="^(rsi|trend|cfg)$"),
    db: Session = Depends(get_db)
):
    """✅ Quick scan for specific screener types"""
    try:
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        if screener_type == "rsi":
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
                'cfg': float(ind.cfg_daily) if ind.cfg_daily else None,
                'cfg_ema45': float(ind.cfg_ema45) if ind.cfg_ema45 else None,
                'stamp': bool(ind.stamp),
            } for ind in indicators]
            
        elif screener_type == "trend":
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
                'trend_signal': bool(ind.trend_signal),
                'cfg': float(ind.cfg_daily) if ind.cfg_daily else None,
            } for ind in indicators]
        
        elif screener_type == "cfg":
            indicators = db.query(StockIndicator).filter(
                StockIndicator.date == latest_date,
                StockIndicator.cfg_ema45_gt_50 == True
            ).order_by(desc(StockIndicator.cfg_ema45)).all()
            
            passing = [{
                'symbol': ind.symbol,
                'company_name': ind.company_name,
                'close': float(ind.close) if ind.close else None,
                'cfg': float(ind.cfg_daily) if ind.cfg_daily else None,
                'cfg_ema45': float(ind.cfg_ema45) if ind.cfg_ema45 else None,
                'cfg_gt_50': bool(ind.cfg_gt_50_daily),
                'cfg_ema45_gt_50': bool(ind.cfg_ema45_gt_50),
                'score': int(ind.score) if ind.score else 0,
            } for ind in indicators]
        
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
    """✅ Summary of how many stocks pass each condition"""
    try:
        latest_date_result = db.execute(text("SELECT MAX(date) FROM stock_indicators"))
        latest_date = latest_date_result.scalar()
        
        if not latest_date:
            raise HTTPException(status_code=404, detail="No indicator data available")
        
        indicators = db.query(StockIndicator).filter(StockIndicator.date == latest_date).all()
        total_processed = len(indicators)
        
        conditions = {
            # RSI Screener
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
            'rsi_55_70': sum(1 for ind in indicators if ind.rsi_55_70),
            'rsi_gt_wma45_d': sum(1 for ind in indicators if ind.rsi_gt_wma45_d),
            'rsi_gt_wma45_w': sum(1 for ind in indicators if ind.rsi_gt_wma45_w),
            'sma9rsi_gt_wma45rsi_d': sum(1 for ind in indicators if ind.sma9rsi_gt_wma45rsi_d),
            'sma9rsi_gt_wma45rsi_w': sum(1 for ind in indicators if ind.sma9rsi_gt_wma45rsi_w),
            'final_signal': sum(1 for ind in indicators if ind.final_signal),
            
            # Trend Screener
            'trend_signal': sum(1 for ind in indicators if ind.trend_signal),
            'price_gt_sma18': sum(1 for ind in indicators if ind.price_gt_sma18),
            'price_gt_sma9_weekly': sum(1 for ind in indicators if ind.price_gt_sma9_weekly),
            'sma_trend_daily': sum(1 for ind in indicators if ind.sma_trend_daily),
            'sma_trend_weekly': sum(1 for ind in indicators if ind.sma_trend_weekly),
            'cci_gt_100': sum(1 for ind in indicators if ind.cci_gt_100),
            'cci_ema20_gt_0_daily': sum(1 for ind in indicators if ind.cci_ema20_gt_0_daily),
            'cci_ema20_gt_0_weekly': sum(1 for ind in indicators if ind.cci_ema20_gt_0_weekly),
            'aroon_up_gt_70': sum(1 for ind in indicators if ind.aroon_up_gt_70),
            'aroon_down_lt_30': sum(1 for ind in indicators if ind.aroon_down_lt_30),
            
            # CFG
            'cfg_gt_50_daily': sum(1 for ind in indicators if ind.cfg_gt_50_daily),
            'cfg_ema45_gt_50': sum(1 for ind in indicators if ind.cfg_ema45_gt_50),
            'cfg_gt_50_w': sum(1 for ind in indicators if ind.cfg_gt_50_w),
            'cfg_ema45_gt_50_w': sum(1 for ind in indicators if ind.cfg_ema45_gt_50_w),
        }
        
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


@router.get("/history/{symbol}")
@limiter.limit("30/minute")
async def get_stock_indicator_history(
    request: Request,
    symbol: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """✅ Get historical indicators for a specific stock"""
    try:
        indicators = db.query(StockIndicator).filter(
            StockIndicator.symbol == symbol
        ).order_by(desc(StockIndicator.date)).limit(days).all()
        
        if not indicators:
            raise HTTPException(status_code=404, detail="No indicator data found for this symbol")
        
        history = [{
            'date': str(ind.date),
            'close': float(ind.close) if ind.close else None,
            'rsi': float(ind.rsi_14) if ind.rsi_14 else None,
            'sma9_rsi': float(ind.sma9_rsi) if ind.sma9_rsi else None,
            'wma45_rsi': float(ind.wma45_rsi) if ind.wma45_rsi else None,
            'cfg': float(ind.cfg_daily) if ind.cfg_daily else None,
            'cfg_ema45': float(ind.cfg_ema45) if ind.cfg_ema45 else None,
            'score': int(ind.score) if ind.score else 0,
            'stamp': bool(ind.stamp),
            'final_signal': bool(ind.final_signal),
            'trend_signal': bool(ind.trend_signal),
            'cfg_gt_50': bool(ind.cfg_gt_50_daily),
            'cfg_ema45_gt_50': bool(ind.cfg_ema45_gt_50),
            'rsi_14_9days_ago': float(ind.rsi_14_9days_ago) if ind.rsi_14_9days_ago else None,
            'stamp_a_value': float(ind.stamp_a_value) if ind.stamp_a_value else None,
        } for ind in indicators]
        
        return {
            'symbol': symbol,
            'company_name': indicators[0].company_name if indicators else None,
            'data_points': len(history),
            'history': history
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
