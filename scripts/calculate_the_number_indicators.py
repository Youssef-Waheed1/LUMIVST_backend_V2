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


def convert_to_float(value):
    """Convert value to float, handling Decimal and None values"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def get_val(lst, i):
    """Safely get value from list or return the value itself if it's a scalar"""
    # إذا كانت القيمة None
    if lst is None:
        return None
    
    # إذا كانت القيمة مفردة (float, int, str, bool) وليس قائمة
    if not isinstance(lst, (list, tuple, np.ndarray, pd.Series)):
        return lst  # رجع القيمة كما هي
    
    # إذا كانت قائمة
    if i < 0 or i >= len(lst):
        return None
    val = lst[i]
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        if np.isnan(val):
            return None
    return val


def calculate_sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average"""
    if not values or len(values) < period:
        return [None] * len(values) if values else []
    s = pd.Series(values)
    sma = s.rolling(window=period, min_periods=period).mean()
    return [float(x) if not pd.isna(x) else None for x in sma.tolist()]


def calculate_the_number_full(highs: List[float], lows: List[float], closes: List[float] = None):
    """The Number مع جميع المكونات"""
    high_sma13 = calculate_sma(highs, 13)
    low_sma13 = calculate_sma(lows, 13)
    high_sma65 = calculate_sma(highs, 65)
    low_sma65 = calculate_sma(lows, 65)
    
    sma9_close = calculate_sma(closes, 9) if closes else [None] * len(highs)
    
    the_number = []
    the_number_hl = []
    the_number_ll = []
    
    for i in range(len(highs)):
        if all(x is not None for x in [get_val(high_sma13, i), get_val(low_sma13, i), 
                                        get_val(high_sma65, i), get_val(low_sma65, i)]):
            tn = (high_sma13[i] + low_sma13[i] + high_sma65[i] + low_sma65[i]) / 4.0
            tn_hl = (high_sma13[i] + high_sma65[i]) / 2.0
            tn_ll = (low_sma13[i] + low_sma65[i]) / 2.0
            the_number.append(tn)
            the_number_hl.append(tn_hl)
            the_number_ll.append(tn_ll)
        else:
            the_number.append(None)
            the_number_hl.append(None)
            the_number_ll.append(None)
    
    return {
        'sma9_close': sma9_close,
        'the_number': the_number,
        'the_number_hl': the_number_hl,
        'the_number_ll': the_number_ll,
        'high_sma13': high_sma13,
        'low_sma13': low_sma13,
        'high_sma65': high_sma65,
        'low_sma65': low_sma65
    }


def get_the_number_current_values(components: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Get current The Number values at specified index"""
    return {
        'sma9_close': get_val(components['sma9_close'], idx),
        'the_number': get_val(components['the_number'], idx),
        'the_number_hl': get_val(components['the_number_hl'], idx),
        'the_number_ll': get_val(components['the_number_ll'], idx),
    }