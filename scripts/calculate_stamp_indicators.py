"""
STAMP Indicator Calculator - مطابق تماماً لـ Pine Script
Formula: A = RSI14 - RSI14[9] + SMA(RSI3, 3)
"""

import sys
import os
import numpy as np
import pandas as pd
from decimal import Decimal
from datetime import date
from typing import List, Optional, Any, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all functions from calculate_rsi_indicators
from scripts.calculate_rsi_indicators import (
    convert_to_float, get_val,
    calculate_rsi_pinescript, calculate_sma, calculate_wma, calculate_ema
)


def calculate_stamp_components(closes: List[float]) -> Dict[str, Any]:
    """
    حساب جميع مكونات مؤشر STAMP
    
    Formula: A = RSI14 - RSI14[9] + SMA(RSI3, 3)
    
    Args:
        closes: قائمة أسعار الإغلاق
    
    Returns:
        قاموس يحتوي على جميع مكونات STAMP
    """
    if not closes or len(closes) < 60:  # نحتاج بيانات كافية للحسابات
        return {
            's9rsi': [None] * len(closes) if closes else [],
            'e45cfg': [None] * len(closes) if closes else [],
            'e45rsi': [None] * len(closes) if closes else [],
            'e20sma3': [None] * len(closes) if closes else [],
            'a_series': [None] * len(closes) if closes else [],
            'rsi14': [None] * len(closes) if closes else [],
            'rsi3': [None] * len(closes) if closes else [],
            'sma3_rsi3': [None] * len(closes) if closes else [],
        }
    
    # 1. حساب RSI للمؤشرين
    rsi14 = calculate_rsi_pinescript(closes, 14)
    rsi3 = calculate_rsi_pinescript(closes, 3)
    
    # 2. حساب SMA3 لـ RSI3
    sma3_rsi3 = calculate_sma(rsi3, 3)
    
    # 3. حساب A values (المكون الرئيسي لـ STAMP)
    # A = rsi14 - rsi14[9] + sma(rsi3, 3)
    a_values = []
    for i in range(len(rsi14)):
        if i < 9 or rsi14[i] is None or rsi14[i-9] is None or sma3_rsi3[i] is None:
            a_values.append(None)
        else:
            val = rsi14[i] - rsi14[i-9] + sma3_rsi3[i]
            a_values.append(val)
    
    # 4. حساب المتوسطات المطلوبة لـ Stamp
    s9rsi = calculate_sma(rsi14, 9)                 # SMA9 of RSI14
    e45cfg = calculate_ema(a_values, 45)            # EMA45 of A values
    e45rsi = calculate_ema(rsi14, 45)               # EMA45 of RSI14
    e20sma3 = calculate_ema(sma3_rsi3, 20)          # EMA20 of SMA3(RSI3)
    
    return {
        # المكونات الرئيسية للعرض
        's9rsi': s9rsi,
        'e45cfg': e45cfg,
        'e45rsi': e45rsi,
        'e20sma3': e20sma3,
        'a_series': a_values,
        
        # المكونات المساعدة للحسابات الأخرى
        'rsi14': rsi14,
        'rsi3': rsi3,
        'sma3_rsi3': sma3_rsi3,
        
        # CFG المتعلقة
        'cfg_series': a_values,                     # CFG = A series
        'cfg_sma9': calculate_sma(a_values, 9),
        'cfg_sma20': calculate_sma(a_values, 20),
        'cfg_ema20': calculate_ema(a_values, 20),
        'cfg_ema45': e45cfg,                         # نفس EMA45 of A
        'cfg_wma45': calculate_wma(a_values, 45),
    }


def calculate_stamp_components_weekly(closes_weekly: List[float]) -> Dict[str, Any]:
    """
    حساب مكونات STAMP على الإطار الأسبوعي
    
    Args:
        closes_weekly: قائمة أسعار الإغلاق الأسبوعية
    
    Returns:
        قاموس يحتوي على مكونات STAMP الأسبوعية
    """
    if not closes_weekly or len(closes_weekly) < 60:
        return {}
    
    # 1. حساب RSI الأسبوعي
    rsi14_w = calculate_rsi_pinescript(closes_weekly, 14)
    rsi3_w = calculate_rsi_pinescript(closes_weekly, 3)
    
    # 2. حساب SMA3 لـ RSI3 الأسبوعي
    sma3_rsi3_w = calculate_sma(rsi3_w, 3)
    
    # 3. حساب A values الأسبوعية
    a_values_w = []
    for i in range(len(rsi14_w)):
        if i < 9 or rsi14_w[i] is None or rsi14_w[i-9] is None or sma3_rsi3_w[i] is None:
            a_values_w.append(None)
        else:
            val = rsi14_w[i] - rsi14_w[i-9] + sma3_rsi3_w[i]
            a_values_w.append(val)
    
    # 4. حساب المتوسطات الأسبوعية
    return {
        'rsi14_w': rsi14_w,
        'rsi3_w': rsi3_w,
        'sma3_rsi3_w': sma3_rsi3_w,
        'a_series_w': a_values_w,
        's9rsi_w': calculate_sma(rsi14_w, 9),
        'e45cfg_w': calculate_ema(a_values_w, 45),
        'e45rsi_w': calculate_ema(rsi14_w, 45),
        'e20sma3_w': calculate_ema(sma3_rsi3_w, 20),
        'cfg_series_w': a_values_w,
        'cfg_sma9_w': calculate_sma(a_values_w, 9),
        'cfg_ema20_w': calculate_ema(a_values_w, 20),
        'cfg_ema45_w': calculate_ema(a_values_w, 45),
        'cfg_wma45_w': calculate_wma(a_values_w, 45),
    }


def get_stamp_current_values(
    stamp_components: Dict[str, Any],
    rsi14_series: List[float],
    idx: int
) -> Dict[str, Any]:
    """
    الحصول على القيم الحالية لمؤشر STAMP
    
    Args:
        stamp_components: مكونات STAMP من calculate_stamp_components
        rsi14_series: سلسلة RSI14 كاملة
        idx: المؤشر الحالي
    
    Returns:
        قاموس بالقيم الحالية
    """
    
    # الحصول على rsi14[9] (قبل 9 أيام)
    rsi14_9days_ago = get_val(rsi14_series, idx - 9) if idx >= 9 else None
    
    # الحصول على sma3_rsi3 الحالية
    sma3_rsi3_series = stamp_components.get('sma3_rsi3', [])
    sma3_rsi3_val = get_val(sma3_rsi3_series, idx)
    
    # حساب قيمة A الحالية
    a_series = stamp_components.get('a_series', [])
    a_val = get_val(a_series, idx)
    
    return {
        # المكونات الرئيسية لـ STAMP
        'rsi_14_9days_ago': rsi14_9days_ago,
        'sma3_rsi3': sma3_rsi3_val,
        'stamp_a_value': a_val,
        
        # Stamp Plots
        'stamp_s9rsi': get_val(stamp_components.get('s9rsi', []), idx),
        'stamp_e45cfg': get_val(stamp_components.get('e45cfg', []), idx),
        'stamp_e45rsi': get_val(stamp_components.get('e45rsi', []), idx),
        'stamp_e20sma3': get_val(stamp_components.get('e20sma3', []), idx),
        
        # CFG Values
        'cfg_daily': a_val,
        'cfg_sma9': get_val(stamp_components.get('cfg_sma9', []), idx),
        'cfg_sma20': get_val(stamp_components.get('cfg_sma20', []), idx),
        'cfg_ema20': get_val(stamp_components.get('cfg_ema20', []), idx),
        'cfg_ema45': get_val(stamp_components.get('cfg_ema45', []), idx),
        'cfg_wma45': get_val(stamp_components.get('cfg_wma45', []), idx),
    }


def get_stamp_weekly_values(
    stamp_weekly_components: Dict[str, Any],
    w_idx: int
) -> Dict[str, Any]:
    """
    الحصول على القيم الحالية لمؤشر STAMP الأسبوعي
    
    Args:
        stamp_weekly_components: مكونات STAMP الأسبوعية
        w_idx: المؤشر الحالي في البيانات الأسبوعية
    
    Returns:
        قاموس بالقيم الأسبوعية
    """
    
    return {
        # RSI Weekly
        'rsi_w': get_val(stamp_weekly_components.get('rsi14_w', []), w_idx),
        'rsi_3_w': get_val(stamp_weekly_components.get('rsi3_w', []), w_idx),
        'sma3_rsi3_w': get_val(stamp_weekly_components.get('sma3_rsi3_w', []), w_idx),
        
        # Stamp Weekly
        'sma9_rsi_w': get_val(stamp_weekly_components.get('s9rsi_w', []), w_idx),
        'ema45_cfg_w': get_val(stamp_weekly_components.get('e45cfg_w', []), w_idx),
        'ema45_rsi_w': get_val(stamp_weekly_components.get('e45rsi_w', []), w_idx),
        'ema20_sma3_w': get_val(stamp_weekly_components.get('e20sma3_w', []), w_idx),
        
        # CFG Weekly
        'cfg_w': get_val(stamp_weekly_components.get('cfg_series_w', []), w_idx),
        'cfg_sma9_w': get_val(stamp_weekly_components.get('cfg_sma9_w', []), w_idx),
        'cfg_ema20_w': get_val(stamp_weekly_components.get('cfg_ema20_w', []), w_idx),
        'cfg_ema45_w': get_val(stamp_weekly_components.get('cfg_ema45_w', []), w_idx),
        'cfg_wma45_w': get_val(stamp_weekly_components.get('cfg_wma45_w', []), w_idx),
    }


def calculate_rsi_on_shifted_series(closes: List[float], period: int = 14, shift: int = 9) -> Optional[float]:
    """
    حساب RSI على سلسلة منزاحة (للاستخدام في CFG WEEKLY فقط)
    ta.rsi(close[9], 14) - يستخدم فقط للأسبوعي
    
    Args:
        closes: قائمة أسعار الإغلاق
        period: فترة RSI (14)
        shift: عدد الأيام للإزاحة (9)
    
    Returns:
        قيمة RSI أو None
    """
    # In Pine, `ta.rsi(close[9], 14)` or using `rsi14[9]` refers to the RSI value
    # shifted by `shift` bars. The correct equivalent is to compute the RSI
    # series for the full `closes` and return the value `shift` bars ago.
    if not closes:
        return None

    rsi_series = calculate_rsi_pinescript(closes, period)
    if not rsi_series:
        return None

    target_idx = len(rsi_series) - 1 - shift
    if target_idx < 0 or target_idx >= len(rsi_series):
        return None

    return rsi_series[target_idx]


def calculate_cfg_series(rsi14_series: List[float], rsi3_series: List[float]) -> List[Optional[float]]:
    """
    حساب سلسلة CFG كاملة (نفس A series)
    CFG = RSI14 - RSI14[9] + SMA(RSI3, 3)
    
    Args:
        rsi14_series: سلسلة RSI14
        rsi3_series: سلسلة RSI3
    
    Returns:
        سلسلة CFG
    """
    if not rsi14_series or not rsi3_series:
        return []
    
    # حساب SMA3 لـ RSI3
    sma3_rsi3 = calculate_sma(rsi3_series, 3)
    
    cfg_values = []
    for i in range(len(rsi14_series)):
        if i < 9 or rsi14_series[i] is None or rsi14_series[i-9] is None or sma3_rsi3[i] is None:
            cfg_values.append(None)
        else:
            cfg = rsi14_series[i] - rsi14_series[i-9] + sma3_rsi3[i]
            cfg_values.append(cfg)
    
    return cfg_values