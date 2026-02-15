from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from datetime import date

from app.core.database import get_db
from app.models.stock_indicators import StockIndicator

router = APIRouter()

@router.get("/technical-screener")
def get_technical_screener_data(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    symbol: Optional[str] = None
):
    query = db.query(StockIndicator)
    
    if symbol:
        query = query.filter(StockIndicator.symbol == symbol)
        
    # Default sort by date desc, then symbol
    query = query.order_by(desc(StockIndicator.date), StockIndicator.symbol)
    
    results = query.offset(offset).limit(limit).all()
    
    return [indicator_to_dict(ind) for ind in results]

def indicator_to_dict(ind: StockIndicator) -> dict:
    """✅ تحويل جميع المؤشرات إلى Dictionary - نسخة كاملة جداً مع كل الحقول"""
    
    # دالة مساعدة للتحويل الآمن
    def safe_float(value):
        return float(value) if value is not None else None
    
    def safe_int(value):
        return int(value) if value is not None else 0
    
    def safe_bool(value):
        return bool(value) if value is not None else False
    
    return {
        # ============ Basic Info ============
        'id': ind.id,
        'symbol': ind.symbol,
        'company_name': ind.company_name,
        'date': str(ind.date) if ind.date else None,
        'close': safe_float(ind.close),
        'created_at': str(ind.created_at) if ind.created_at else None,
        'updated_at': str(ind.updated_at) if ind.updated_at else None,
        
        # ============ 1. RSI Indicator ============
        'rsi': safe_float(ind.rsi_14),                    # Alias
        'rsi_14': safe_float(ind.rsi_14),
        'sma9_rsi': safe_float(ind.sma9_rsi),
        'wma45_rsi': safe_float(ind.wma45_rsi),
        
        # ============ 2. The Number Indicator ============
        'sma9_close': safe_float(ind.sma9_close),
        'the_number': safe_float(ind.the_number),
        'the_number_hl': safe_float(ind.the_number_hl),
        'the_number_ll': safe_float(ind.the_number_ll),
        
        # ============ 3. Stamp Indicator ============
        'rsi_14_9days_ago': safe_float(ind.rsi_14_9days_ago),
        'rsi_3': safe_float(ind.rsi_3),
        'sma3_rsi3': safe_float(ind.sma3_rsi3),
        'stamp_a_value': safe_float(ind.stamp_a_value),
        'stamp_s9rsi': safe_float(ind.stamp_s9rsi),
        'stamp_e45cfg': safe_float(ind.stamp_e45cfg),
        'stamp_e45rsi': safe_float(ind.stamp_e45rsi),
        'stamp_e20sma3': safe_float(ind.stamp_e20sma3),
        
        # ============ 4. Trend Screener - Daily ============
        'sma4': safe_float(ind.sma4),                      # ✅ Daily SMA4
        'sma9': safe_float(ind.sma9),                      # ✅ Daily SMA9
        'sma18': safe_float(ind.sma18),                    # ✅ Daily SMA18
        'wma45_close': safe_float(ind.wma45_close),        # ✅ Daily WMA45
        'cci': safe_float(ind.cci),                        # ✅ Daily CCI
        'cci_ema20': safe_float(ind.cci_ema20),            # ✅ Daily CCI EMA20
        'aroon_up': safe_float(ind.aroon_up),              # ✅ Daily Aroon Up
        'aroon_down': safe_float(ind.aroon_down),          # ✅ Daily Aroon Down
        
        # ============ 5. Trend Screener - Weekly ============
        'close_w': safe_float(ind.close_w),                 # ✅ Weekly Close
        'sma4_w': safe_float(ind.sma4_w),                   # ✅ Weekly SMA4
        'sma9_w': safe_float(ind.sma9_w),                   # ✅ Weekly SMA9
        'sma18_w': safe_float(ind.sma18_w),                 # ✅ Weekly SMA18
        'wma45_close_w': safe_float(ind.wma45_close_w),     # ✅ Weekly WMA45
        'cci_w': safe_float(ind.cci_w),                     # ✅ Weekly CCI
        'cci_ema20_w': safe_float(ind.cci_ema20_w),         # ✅ Weekly CCI EMA20
        'aroon_up_w': safe_float(ind.aroon_up_w),           # ✅ Weekly Aroon Up
        'aroon_down_w': safe_float(ind.aroon_down_w),       # ✅ Weekly Aroon Down
        
        # ============ 6. RSI Screener Conditions ============
        'price_gt_sma18': safe_bool(ind.price_gt_sma18),
        'price_gt_sma9_weekly': safe_bool(ind.price_gt_sma9_weekly),
        'sma_trend_daily': safe_bool(ind.sma_trend_daily),
        'sma_trend_weekly': safe_bool(ind.sma_trend_weekly),
        'cci_gt_100': safe_bool(ind.cci_gt_100),
        'cci_ema20_gt_0_daily': safe_bool(ind.cci_ema20_gt_0_daily),
        'cci_ema20_gt_0_weekly': safe_bool(ind.cci_ema20_gt_0_weekly),
        'aroon_up_gt_70': safe_bool(ind.aroon_up_gt_70),
        'aroon_down_lt_30': safe_bool(ind.aroon_down_lt_30),
        'is_etf_or_index': safe_bool(ind.is_etf_or_index),
        'has_gap': safe_bool(ind.has_gap),
        'trend_signal': safe_bool(ind.trend_signal),
        
        # ============ 7. RSI Weekly Values ============
        'rsi_w': safe_float(ind.rsi_w),
        'rsi_3_w': safe_float(ind.rsi_3_w),
        'sma9_rsi_w': safe_float(ind.sma9_rsi_w),
        'wma45_rsi_w': safe_float(ind.wma45_rsi_w),
        'ema45_rsi_w': safe_float(ind.ema45_rsi_w),
        
        # ============ 8. CFG Analysis ============
        'cfg_daily': safe_float(ind.cfg_daily),
        'cfg_sma9': safe_float(ind.cfg_sma9),
        'cfg_ema20': safe_float(ind.cfg_ema20),
        'cfg_ema45': safe_float(ind.cfg_ema45),
        'cfg_wma45': safe_float(ind.cfg_wma45),
        'cfg_w': safe_float(ind.cfg_w),
        'cfg_ema20_w': safe_float(ind.cfg_ema20_w),
        'cfg_ema45_w': safe_float(ind.cfg_ema45_w),
        'cfg_wma45_w': safe_float(ind.cfg_wma45_w),
        
        # ============ 9. CFG Conditions ============
        'cfg_gt_50_daily': safe_bool(ind.cfg_gt_50_daily),
        'cfg_ema45_gt_50': safe_bool(ind.cfg_ema45_gt_50),
        'cfg_ema20_gt_50': safe_bool(ind.cfg_ema20_gt_50),
        'cfg_gt_50_w': safe_bool(ind.cfg_gt_50_w),
        'cfg_ema45_gt_50_w': safe_bool(ind.cfg_ema45_gt_50_w),
        'cfg_ema20_gt_50_w': safe_bool(ind.cfg_ema20_gt_50_w),
        
        # ============ 10. RSI Screener Final ============
        'sma9_gt_tn_daily': safe_bool(ind.sma9_gt_tn_daily),
        'sma9_gt_tn_weekly': safe_bool(ind.sma9_gt_tn_weekly),
        'rsi_lt_80_d': safe_bool(ind.rsi_lt_80_d),
        'rsi_lt_80_w': safe_bool(ind.rsi_lt_80_w),
        'sma9_rsi_lte_75_d': safe_bool(ind.sma9_rsi_lte_75_d),
        'sma9_rsi_lte_75_w': safe_bool(ind.sma9_rsi_lte_75_w),
        'ema45_rsi_lte_70_d': safe_bool(ind.ema45_rsi_lte_70_d),
        'ema45_rsi_lte_70_w': safe_bool(ind.ema45_rsi_lte_70_w),
        'rsi_55_70': safe_bool(ind.rsi_55_70),
        'rsi_gt_wma45_d': safe_bool(ind.rsi_gt_wma45_d),
        'rsi_gt_wma45_w': safe_bool(ind.rsi_gt_wma45_w),
        'sma9rsi_gt_wma45rsi_d': safe_bool(ind.sma9rsi_gt_wma45rsi_d),
        'sma9rsi_gt_wma45rsi_w': safe_bool(ind.sma9rsi_gt_wma45rsi_w),
        
        # STAMP Conditions
        'stamp_daily': safe_bool(ind.stamp_daily),
        'stamp_weekly': safe_bool(ind.stamp_weekly),
        'stamp': safe_bool(ind.stamp),
        
        # ============ Final Results ============
        'final_signal': safe_bool(ind.final_signal),
        'score': safe_int(ind.score),
        'total_conditions': 15,
    }