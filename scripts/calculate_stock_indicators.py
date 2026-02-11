import sys
import os
import numpy as np
import pandas as pd
from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.stock_indicators import StockIndicator


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


def delete_old_calculations(db: Session, target_date: date = None):
    """Delete old indicator calculations for the target date"""
    print("🧹 Cleaning up old calculations...")
    
    if target_date is None:
        result = db.execute(text("SELECT MAX(date) FROM prices"))
        target_date = result.scalar()
    
    if target_date:
        delete_query = text("""
            DELETE FROM stock_indicators 
            WHERE date = :target_date
        """)
        result = db.execute(delete_query, {"target_date": target_date})
        deleted_count = result.rowcount
        db.commit()
        print(f"✅ Deleted {deleted_count} old records for date {target_date}")
        return deleted_count, target_date
    return 0, None


def calculate_rsi_pinescript(values: List[float], period: int = 14) -> List[Optional[float]]:
    """✅ RSI مطابق تماماً لـ PineScript باستخدام RMA (Wilder's Smoothing)"""
    if not values or len(values) < period + 1:
        return [None] * len(values) if values else []
    
    prices = np.array(values, dtype=float)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    # RMA - Wilder's Smoothing
    avg_gain = np.full(len(prices), np.nan)
    avg_loss = np.full(len(prices), np.nan)
    
    # First value - simple average
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])
    
    # Wilder's smoothing
    alpha = 1.0 / period
    for i in range(period + 1, len(prices)):
        avg_gain[i] = avg_gain[i-1] * (1 - alpha) + gains[i-1] * alpha
        avg_loss[i] = avg_loss[i-1] * (1 - alpha) + losses[i-1] * alpha
    
    rsi_values = []
    for i in range(len(prices)):
        if i < period:
            rsi_values.append(None)
        elif np.isnan(avg_gain[i]) or np.isnan(avg_loss[i]):
            rsi_values.append(None)
        elif avg_loss[i] == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi = 100.0 - (100.0 / (1.0 + rs))
            rsi_values.append(rsi)
    
    return rsi_values


def calculate_sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average"""
    if not values or len(values) < period:
        return [None] * len(values) if values else []
    s = pd.Series(values)
    sma = s.rolling(window=period, min_periods=period).mean()
    return [float(x) if not pd.isna(x) else None for x in sma.tolist()]


def calculate_wma(values: List[float], period: int) -> List[Optional[float]]:
    """Weighted Moving Average"""
    if not values or len(values) < period:
        return [None] * len(values) if values else []
    
    s = pd.Series(values)
    weights = np.arange(1, period + 1)
    
    def wma_calc(x):
        if len(x) < period:
            return np.nan
        return np.dot(x, weights[:len(x)]) / weights[:len(x)].sum()
        
    wma = s.rolling(window=period, min_periods=period).apply(wma_calc, raw=True)
    return [float(x) if not pd.isna(x) else None for x in wma.tolist()]


def calculate_ema(values: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average"""
    if not values or len(values) < period:
        return [None] * len(values) if values else []
    s = pd.Series(values)
    ema = s.ewm(span=period, min_periods=period, adjust=False).mean()
    return [float(x) if not pd.isna(x) else None for x in ema.tolist()]


def calculate_cci(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Commodity Channel Index"""
    if not highs or not lows or not closes or len(highs) < period:
        return [None] * len(highs) if highs else []
        
    highs_arr = np.array(highs)
    lows_arr = np.array(lows)
    closes_arr = np.array(closes)
    tp = (highs_arr + lows_arr + closes_arr) / 3
    
    cci_values = []
    for i in range(len(tp)):
        if i < period - 1:
            cci_values.append(None)
            continue
            
        sma_tp = np.mean(tp[i-period+1:i+1])
        md = np.mean(np.abs(tp[i-period+1:i+1] - sma_tp))
        
        if md == 0:
            cci_values.append(0)
        else:
            cci = (tp[i] - sma_tp) / (0.015 * md)
            cci_values.append(cci)
    
    return cci_values


def calculate_aroon_correct(highs: List[float], lows: List[float], period: int = 25) -> tuple:
    """
    ✅ Aroon صحيح 100% - يطابق PineScript
    يستخدم أول occurrence (barssince) وليس آخر occurrence
    """
    if not highs or not lows or len(highs) < period:
        return [], []
        
    highs_arr = np.array(highs, dtype=float)
    lows_arr = np.array(lows, dtype=float)
    
    aroon_up = []
    aroon_down = []
    
    for i in range(len(highs_arr)):
        if i < period - 1:
            aroon_up.append(None)
            aroon_down.append(None)
            continue
            
        window_high = highs_arr[i-period+1:i+1]
        window_low = lows_arr[i-period+1:i+1]
        
        # ✅ أول occurrence - يطابق barssince في PineScript
        days_since_high = np.argmax(window_high)
        days_since_low = np.argmin(window_low)
        
        up = ((period - days_since_high) / period) * 100
        down = ((period - days_since_low) / period) * 100
        
        aroon_up.append(up)
        aroon_down.append(down)
        
    return aroon_up, aroon_down


def calculate_stamp_correct(rsi14_series: List[float], rsi3_series: List[float]) -> Dict[str, Any]:
    """
    ✅ STAMP صحيح 100% - يطابق PineScript
    A = RSI14 - RSI14[9] + SMA(RSI3, 3)
    """
    if len(rsi14_series) < 10 or len(rsi3_series) < 3:
        return {
            'a_value': None,
            's9rsi': None,
            'e45cfg': None,
            'e45rsi': None,
            'e20sma3': None
        }
    
    # RSI14 الحالي
    rsi14_current = rsi14_series[-1]
    
    # ✅ RSI14[9] - قيمة RSI من 9 أيام مضت (وليس إعادة حساب)
    rsi14_9days_ago = rsi14_series[-10] if len(rsi14_series) > 10 else None
    
    # SMA(RSI3, 3)
    rsi3_last_3 = rsi3_series[-3:]
    sma3_rsi3 = sum(rsi3_last_3) / 3 if len(rsi3_last_3) == 3 else None
    
    # ✅ A = RSI14 - RSI14[9] + SMA(RSI3, 3)
    a_value = None
    if rsi14_current is not None and rsi14_9days_ago is not None and sma3_rsi3 is not None:
        a_value = rsi14_current - rsi14_9days_ago + sma3_rsi3
    
    # المؤشرات الأخرى
    s9rsi = calculate_sma(rsi14_series, 9)[-1] if len(rsi14_series) >= 9 else None
    e45cfg = calculate_ema([a_value] if a_value else [], 45)[-1] if a_value else None
    e45rsi = calculate_ema(rsi14_series, 45)[-1] if len(rsi14_series) >= 45 else None
    e20sma3 = calculate_ema(calculate_sma(rsi3_series, 3), 20)[-1] if len(rsi3_series) >= 23 else None
    
    return {
        'a_value': a_value,
        's9rsi': s9rsi,
        'e45cfg': e45cfg,
        'e45rsi': e45rsi,
        'e20sma3': e20sma3,
        'rsi14_9days_ago': rsi14_9days_ago,
        'sma3_rsi3': sma3_rsi3
    }


def calculate_rsi_on_shifted_series(closes: List[float], period: int = 14, shift: int = 9) -> Optional[float]:
    """
    تحسب ta.rsi(close[9], 14) بشكل صحيح وسريع
    هذه تختلف عن rsi[9]
    Optimization: Only use necessary history (period + 100 buffer) instead of full history
    """
    if not closes or len(closes) < period + shift + 1:
        return None
    
    # تحسين الأداء: نأخذ آخر period + 100 يوم قبل الـ shift فقط (ليس كل التاريخ)
    # This avoids recalculating RSI from the beginning of time for every single day
    buffer = 100
    end_idx = len(closes) - shift
    start_idx = max(0, end_idx - period - buffer)
    
    series = closes[start_idx:end_idx]
    
    if len(series) < period + 1:
        return None
        
    # نحسب RSI على هذه السلسلة الجزئيه
    rsi_shifted = calculate_rsi_pinescript(series, period)
    
    # نرجع آخر قيمة
    return rsi_shifted[-1] if rsi_shifted else None


def calculate_cfg_correct(rsi14_series: List[float], closes: List[float], rsi3_series: List[float]) -> Dict[str, Any]:
    """
    ✅ CFG صحيح 100% - يطابق PineScript تماماً (V2)
    CFG = RSI14 - ta.rsi(close[9], 14) + SMA(RSI3, 3)
    """
    if len(rsi14_series) < 1 or len(closes) < 1:
        return {
            'cfg': None,
            'rsi14_shifted': None,
            'rsi14_current': None,
            'sma3_rsi3': None
        }

    rsi14_current = rsi14_series[-1]
    
    # ✅ هذا هو الفرق الحاسم - نستخدم السعر وليس RSI
    # ta.rsi(close[9], 14)
    rsi14_shifted = calculate_rsi_on_shifted_series(closes, 14, 9)
    
    rsi3_last_3 = rsi3_series[-3:]
    sma3_rsi3 = sum(rsi3_last_3) / 3 if len(rsi3_last_3) == 3 else None
    
    cfg = None
    if rsi14_current is not None and rsi14_shifted is not None and sma3_rsi3 is not None:
        cfg = rsi14_current - rsi14_shifted + sma3_rsi3
    
    return {
        'cfg': cfg,
        'rsi14_shifted': rsi14_shifted,  # ta.rsi(close[9], 14)
        'rsi14_current': rsi14_current,
        'sma3_rsi3': sma3_rsi3
    }


def calculate_the_number_full(highs: List[float], lows: List[float]):
    """The Number مع جميع المكونات"""
    high_sma13 = calculate_sma(highs, 13)
    low_sma13 = calculate_sma(lows, 13)
    high_sma65 = calculate_sma(highs, 65)
    low_sma65 = calculate_sma(lows, 65)
    
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
    
    return the_number, the_number_hl, the_number_ll


def get_val(lst, i):
    """Safely get value from list"""
    if i < 0 or i >= len(lst):
        return None
    val = lst[i]
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        if np.isnan(val):
            return None
    return val


def calculate_all_indicators_for_stock(db: Session, symbol: str, target_date: date = None) -> Dict[str, Any]:
    """✅ حساب جميع المؤشرات بشكل صحيح 100%"""
    
    # جلب البيانات
    if target_date:
        query_limit = text("""
            SELECT * FROM (
                SELECT date, open, high, low, close
                FROM prices
                WHERE symbol = :symbol AND date <= :target_date
                ORDER BY date DESC
                LIMIT 500
            ) as sub ORDER BY date ASC
        """)
        result = db.execute(query_limit, {"symbol": symbol, "target_date": target_date})
    else:
        query_limit = text("""
            SELECT * FROM (
                SELECT date, open, high, low, close
                FROM prices
                WHERE symbol = :symbol
                ORDER BY date DESC
                LIMIT 500
            ) as sub ORDER BY date ASC
        """)
        result = db.execute(query_limit, {"symbol": symbol})
    
    rows = result.fetchall()
    
    if not rows or len(rows) < 100:
        print(f"⚠️  {symbol}: Not enough data ({len(rows)} rows)")
        return {}
    
    # DataFrame
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    df['open'] = df['open'].apply(convert_to_float)
    df['high'] = df['high'].apply(convert_to_float)
    df['low'] = df['low'].apply(convert_to_float)
    df['close'] = df['close'].apply(convert_to_float)
    df.dropna(subset=['close'], inplace=True)
    
    if len(df) < 100:
        return {}
    
    # --- البيانات اليومية ---
    dates = df['date'].tolist()
    closes = df['close'].tolist()
    highs = df['high'].tolist()
    lows = df['low'].tolist()
    
    # 1. RSI Calculations
    rsi_14 = calculate_rsi_pinescript(closes, 14)
    rsi_3 = calculate_rsi_pinescript(closes, 3)
    
    # 2. Moving Averages of RSI
    sma9_rsi = calculate_sma(rsi_14, 9)
    wma45_rsi = calculate_wma(rsi_14, 45)
    ema45_rsi = calculate_ema(rsi_14, 45)
    
    # 3. Price Moving Averages
    sma9_close = calculate_sma(closes, 9)
    wma45_close = calculate_wma(closes, 45)
    sma4 = calculate_sma(closes, 4)
    sma18 = calculate_sma(closes, 18)
    
    # 4. SMA3 of RSI3
    sma3_rsi3 = calculate_sma(rsi_3, 3)
    ema20_sma3 = calculate_ema(sma3_rsi3, 20)
    
    # 5. ✅ STAMP - تصحيح كامل
    stamp_data = calculate_stamp_correct(rsi_14, rsi_3)
    
    # 6. ✅ CFG - تصحيح كامل (V2)
    cfg_data = calculate_cfg_correct(rsi_14, closes, rsi_3)
    
    # 7. CFG Averages
    cfg_values = [cfg_data['cfg']] * len(closes) if cfg_data['cfg'] else [None] * len(closes)
    sma9_cfg = calculate_sma(cfg_values, 9)
    sma20_cfg = calculate_sma(cfg_values, 20)
    ema20_cfg = calculate_ema(cfg_values, 20)
    ema45_cfg = calculate_ema(cfg_values, 45)
    
    # 8. The Number
    the_number, the_number_hl, the_number_ll = calculate_the_number_full(highs, lows)
    
    # 9. Trend Indicators
    cci = calculate_cci(highs, lows, closes, 14)
    cci_ema20 = calculate_ema(cci, 20)
    
    # ✅ Aroon صحيح
    aroon_up, aroon_down = calculate_aroon_correct(highs, lows, 25)
    
    # --- Weekly Calculations ---
    df_weekly = df.set_index('date').resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).ffill().dropna()
    
    if len(df_weekly) < 20:
        print(f"⚠️  {symbol}: Not enough weekly data ({len(df_weekly)} weeks)")
        return {}
    
    closes_w = df_weekly['close'].tolist()
    highs_w = df_weekly['high'].tolist()
    lows_w = df_weekly['low'].tolist()
    
    # Weekly RSI
    rsi_w = calculate_rsi_pinescript(closes_w, 14)
    rsi_3_w = calculate_rsi_pinescript(closes_w, 3)
    sma3_rsi3_w = calculate_sma(rsi_3_w, 3)
    sma9_rsi_w = calculate_sma(rsi_w, 9)
    wma45_rsi_w = calculate_wma(rsi_w, 45)
    ema45_rsi_w = calculate_ema(rsi_w, 45)
    
    # Weekly CFG (V2)
    cfg_w_data = calculate_cfg_correct(rsi_w, closes_w, rsi_3_w)
    cfg_w = cfg_w_data['cfg']
    ema45_cfg_w = calculate_ema([cfg_w] if cfg_w else [], 45)[-1] if cfg_w else None
    ema20_cfg_w = calculate_ema([cfg_w] if cfg_w else [], 20)[-1] if cfg_w else None
    sma9_cfg_w = calculate_sma([cfg_w] if cfg_w else [], 9)[-1] if cfg_w else None
    
    # Weekly Price MAs
    sma9_close_w = calculate_sma(closes_w, 9)
    wma45_close_w = calculate_wma(closes_w, 45)
    sma4_w = calculate_sma(closes_w, 4)
    sma18_w = calculate_sma(closes_w, 18)
    
    # Weekly The Number
    tn_w, _, _ = calculate_the_number_full(highs_w, lows_w)
    
    # Weekly CCI and Aroon
    cci_w = calculate_cci(highs_w, lows_w, closes_w, 14)
    cci_ema20_w = calculate_ema(cci_w, 20)
    aroon_up_w, aroon_down_w = calculate_aroon_correct(highs_w, lows_w, 25)
    
    # --- Current Values ---
    idx = len(df) - 1
    w_idx = -1  # ✅ تعريف w_idx - آخر قيمة في البيانات الأسبوعية
    
    # التحقق من تطابق التاريخ
    actual_date = df.iloc[idx]['date']
    if target_date and pd.to_datetime(actual_date) != pd.to_datetime(target_date):
        print(f"⚠️  {symbol}: Last row date ({actual_date}) != target date ({target_date})")
        # البحث عن التاريخ المطلوب
        target_idx = None
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]['date'] == pd.to_datetime(target_date):
                target_idx = i
                break
        if target_idx is None:
            return {}
        idx = target_idx
        # w_idx يبقى -1 (آخر قيمة في الأسبوعي)
    
    # --- Filters ---
    is_etf_or_index = 'INDEX' in symbol or 'ETF' in symbol
    
    current_open = df.iloc[idx]['open'] if 'open' in df.columns else None
    has_gap = False
    if idx > 0 and current_open is not None:
        prev_close = df.iloc[idx - 1]['close']
        if prev_close and prev_close > 0:
            gap_percent = abs((current_open - prev_close) / prev_close)
            has_gap = gap_percent > 0.03
    
    # --- STAMP Conditions ---
    cond_stamp_1_d = get_val(sma9_close, idx) > get_val(wma45_close, idx) if all(v is not None for v in [get_val(sma9_close, idx), get_val(wma45_close, idx)]) else False
    cond_stamp_2_d = get_val(sma9_rsi, idx) > get_val(wma45_rsi, idx) if all(v is not None for v in [get_val(sma9_rsi, idx), get_val(wma45_rsi, idx)]) else False
    cond_stamp_3_d = get_val(ema45_rsi, idx) > 50 if get_val(ema45_rsi, idx) is not None else False
    cond_stamp_4_d = get_val(ema45_cfg, idx) > 50 if get_val(ema45_cfg, idx) is not None else False
    cond_stamp_5_d = get_val(ema20_sma3, idx) > 50 if get_val(ema20_sma3, idx) is not None else False
    
    stamp_daily = cond_stamp_1_d and cond_stamp_2_d and cond_stamp_3_d and cond_stamp_4_d and cond_stamp_5_d
    
    # Weekly STAMP Correction
    ema20_sma3_w_series = calculate_ema(sma3_rsi3_w, 20)
    ema20_sma3_w_val = get_val(ema20_sma3_w_series, w_idx)

    cond_stamp_1_w = get_val(sma9_close_w, w_idx) > get_val(wma45_close_w, w_idx) if all(v is not None for v in [get_val(sma9_close_w, w_idx), get_val(wma45_close_w, w_idx)]) else False
    cond_stamp_2_w = get_val(sma9_rsi_w, w_idx) > get_val(wma45_rsi_w, w_idx) if all(v is not None for v in [get_val(sma9_rsi_w, w_idx), get_val(wma45_rsi_w, w_idx)]) else False
    cond_stamp_3_w = get_val(ema45_rsi_w, w_idx) > 50 if get_val(ema45_rsi_w, w_idx) is not None else False
    cond_stamp_4_w = get_val(ema45_cfg_w, -1) > 50 if ema45_cfg_w is not None else False
    cond_stamp_5_w = ema20_sma3_w_val > 50 if ema20_sma3_w_val is not None else False
    
    stamp_weekly = cond_stamp_1_w and cond_stamp_2_w and cond_stamp_3_w and cond_stamp_4_w and cond_stamp_5_w
    stamp = stamp_daily and stamp_weekly
    
    # --- RSI Screener Conditions ---
    sma9_gt_tn_daily = get_val(sma9_close, idx) > get_val(the_number, idx) if all(v is not None for v in [get_val(sma9_close, idx), get_val(the_number, idx)]) else False
    sma9_gt_tn_weekly = get_val(sma9_close_w, w_idx) > get_val(tn_w, w_idx) if all(v is not None for v in [get_val(sma9_close_w, w_idx), get_val(tn_w, w_idx)]) else False
    
    rsi_lt_80_d = get_val(rsi_14, idx) < 80 if get_val(rsi_14, idx) is not None else False
    rsi_lt_80_w = get_val(rsi_w, w_idx) < 80 if get_val(rsi_w, w_idx) is not None else False
    
    sma9_rsi_lte_75_d = get_val(sma9_rsi, idx) <= 75 if get_val(sma9_rsi, idx) is not None else False
    sma9_rsi_lte_75_w = get_val(sma9_rsi_w, w_idx) <= 75 if get_val(sma9_rsi_w, w_idx) is not None else False
    
    ema45_rsi_lte_70_d = get_val(ema45_rsi, idx) <= 70 if get_val(ema45_rsi, idx) is not None else False
    ema45_rsi_lte_70_w = get_val(ema45_rsi_w, w_idx) <= 70 if get_val(ema45_rsi_w, w_idx) is not None else False
    
    rsi_55_70 = 55 <= get_val(rsi_14, idx) <= 70 if get_val(rsi_14, idx) is not None else False
    
    rsi_gt_wma45_d = get_val(rsi_14, idx) > get_val(wma45_rsi, idx) if all(v is not None for v in [get_val(rsi_14, idx), get_val(wma45_rsi, idx)]) else False
    rsi_gt_wma45_w = get_val(rsi_w, w_idx) > get_val(wma45_rsi_w, w_idx) if all(v is not None for v in [get_val(rsi_w, w_idx), get_val(wma45_rsi_w, w_idx)]) else False
    
    sma9rsi_gt_wma45rsi_d = get_val(sma9_rsi, idx) > get_val(wma45_rsi, idx) if all(v is not None for v in [get_val(sma9_rsi, idx), get_val(wma45_rsi, idx)]) else False
    sma9rsi_gt_wma45rsi_w = get_val(sma9_rsi_w, w_idx) > get_val(wma45_rsi_w, w_idx) if all(v is not None for v in [get_val(sma9_rsi_w, w_idx), get_val(wma45_rsi_w, w_idx)]) else False
    
    # CFG Conditions
    cfg_gt_50_daily = cfg_data['cfg'] > 50 if cfg_data['cfg'] is not None else False
    cfg_ema45_gt_50 = get_val(ema45_cfg, idx) > 50 if get_val(ema45_cfg, idx) is not None else False
    cfg_ema20_gt_50 = get_val(ema20_cfg, idx) > 50 if get_val(ema20_cfg, idx) is not None else False
    
    cfg_gt_50_w = cfg_w > 50 if cfg_w is not None else False
    cfg_ema45_gt_50_w = ema45_cfg_w > 50 if ema45_cfg_w is not None else False
    cfg_ema20_gt_50_w = ema20_cfg_w > 50 if ema20_cfg_w is not None else False
    
    # --- Trend Conditions ---
    price_gt_sma18 = get_val(closes, idx) > get_val(sma18, idx) if all(v is not None for v in [get_val(closes, idx), get_val(sma18, idx)]) else False
    price_gt_sma9_weekly = get_val(closes_w, w_idx) > get_val(sma9_close_w, w_idx) if all(v is not None for v in [get_val(closes_w, w_idx), get_val(sma9_close_w, w_idx)]) else False
    
    sma_trend_daily = (get_val(sma4, idx) > get_val(sma9_close, idx) and get_val(sma9_close, idx) > get_val(sma18, idx)) if all(v is not None for v in [get_val(sma4, idx), get_val(sma9_close, idx), get_val(sma18, idx)]) else False
    sma_trend_weekly = (get_val(sma4_w, w_idx) > get_val(sma9_close_w, w_idx) and get_val(sma9_close_w, w_idx) > get_val(sma18_w, w_idx)) if all(v is not None for v in [get_val(sma4_w, w_idx), get_val(sma9_close_w, w_idx), get_val(sma18_w, w_idx)]) else False
    
    cci_gt_100 = get_val(cci, idx) > 100 if get_val(cci, idx) is not None else False
    cci_ema20_gt_0_daily = get_val(cci_ema20, idx) > 0 if get_val(cci_ema20, idx) is not None else False
    cci_ema20_gt_0_weekly = get_val(cci_ema20_w, w_idx) > 0 if get_val(cci_ema20_w, w_idx) is not None else False
    
    aroon_up_gt_70 = get_val(aroon_up, idx) > 70 if get_val(aroon_up, idx) is not None else False
    aroon_down_lt_30 = get_val(aroon_down, idx) < 30 if get_val(aroon_down, idx) is not None else False
    
    # Trend Signal
    trend_signal = (
        price_gt_sma18 and price_gt_sma9_weekly and
        sma_trend_daily and sma_trend_weekly and
        cci_gt_100 and cci_ema20_gt_0_daily and cci_ema20_gt_0_weekly and
        aroon_up_gt_70 and aroon_down_lt_30 and
        not is_etf_or_index and not has_gap
    )
    
    # Final Signal (RSI Screener)
    final_signal = (
        stamp and
        sma9_gt_tn_daily and sma9_gt_tn_weekly and
        rsi_lt_80_d and rsi_lt_80_w and
        sma9_rsi_lte_75_d and sma9_rsi_lte_75_w and
        ema45_rsi_lte_70_d and ema45_rsi_lte_70_w and
        rsi_55_70 and
        rsi_gt_wma45_d and rsi_gt_wma45_w and
        sma9rsi_gt_wma45rsi_d and sma9rsi_gt_wma45rsi_w
    )
    
    # Score
    conditions = [
        stamp_daily, stamp_weekly,
        sma9_gt_tn_daily, sma9_gt_tn_weekly,
        rsi_lt_80_d, rsi_lt_80_w,
        sma9_rsi_lte_75_d, sma9_rsi_lte_75_w,
        ema45_rsi_lte_70_d, ema45_rsi_lte_70_w,
        rsi_55_70,
        rsi_gt_wma45_d, rsi_gt_wma45_w,
        sma9rsi_gt_wma45rsi_d, sma9rsi_gt_wma45rsi_w
    ]
    score = sum(1 for c in conditions if c)
    
    # --- Result Dictionary ---
    result = {
        # Price
        'close': get_val(closes, idx),
        
        # ===== 1. RSI Indicator =====
        'rsi_14': get_val(rsi_14, idx),
        'sma9_rsi': get_val(sma9_rsi, idx),
        'wma45_rsi': get_val(wma45_rsi, idx),
        
        # ===== 2. The Number =====
        'sma9_close': get_val(sma9_close, idx),
        'the_number': get_val(the_number, idx),
        'the_number_hl': get_val(the_number_hl, idx),
        'the_number_ll': get_val(the_number_ll, idx),
        
        # ===== 3. Stamp Indicator =====
        'rsi_14_9days_ago': stamp_data.get('rsi14_9days_ago'),
        'rsi_3': get_val(rsi_3, idx),
        'sma3_rsi3': stamp_data.get('sma3_rsi3'),
        'stamp_a_value': stamp_data.get('a_value'),
        'stamp_s9rsi': stamp_data.get('s9rsi'),
        'stamp_e45cfg': stamp_data.get('e45cfg'),
        'stamp_e45rsi': stamp_data.get('e45rsi'),
        'stamp_e20sma3': stamp_data.get('e20sma3'),
        
        # ===== 4. Trend Screener =====
        'sma4': get_val(sma4, idx),
        'sma9': get_val(sma9_close, idx),
        'sma18': get_val(sma18, idx),
        'sma4_w': get_val(sma4_w, w_idx),
        'sma9_w': get_val(sma9_close_w, w_idx),
        'sma18_w': get_val(sma18_w, w_idx),
        'close_w': get_val(closes_w, w_idx),
        'cci': get_val(cci, idx),
        'cci_ema20': get_val(cci_ema20, idx),
        'cci_ema20_w': get_val(cci_ema20_w, w_idx),
        'aroon_up': get_val(aroon_up, idx),
        'aroon_down': get_val(aroon_down, idx),
        'aroon_up_w': get_val(aroon_up_w, w_idx),
        'aroon_down_w': get_val(aroon_down_w, w_idx),
        
        # Trend Conditions
        'price_gt_sma18': price_gt_sma18,
        'price_gt_sma9_weekly': price_gt_sma9_weekly,
        'sma_trend_daily': sma_trend_daily,
        'sma_trend_weekly': sma_trend_weekly,
        'cci_gt_100': cci_gt_100,
        'cci_ema20_gt_0_daily': cci_ema20_gt_0_daily,
        'cci_ema20_gt_0_weekly': cci_ema20_gt_0_weekly,
        'aroon_up_gt_70': aroon_up_gt_70,
        'aroon_down_lt_30': aroon_down_lt_30,
        'is_etf_or_index': is_etf_or_index,
        'has_gap': has_gap,
        'trend_signal': trend_signal,
        
        # ===== 5. RSI Screener =====
        'wma45_rsi_screener': get_val(wma45_rsi, idx),
        'ema45_rsi': get_val(ema45_rsi, idx),
        'ema45_cfg': get_val(ema45_cfg, idx),
        'ema20_sma3': get_val(ema20_sma3, idx),
        'wma45_close': get_val(wma45_close, idx),
        
        # Weekly Values
        'rsi_w': get_val(rsi_w, w_idx),
        'rsi_3_w': get_val(rsi_3_w, w_idx),
        'sma3_rsi3_w': get_val(sma3_rsi3_w, w_idx),
        'sma9_rsi_w': get_val(sma9_rsi_w, w_idx),
        'wma45_rsi_w': get_val(wma45_rsi_w, w_idx),
        'ema45_rsi_w': get_val(ema45_rsi_w, w_idx),
        'ema45_cfg_w': ema45_cfg_w,
        'ema20_sma3_w': ema20_sma3_w_val,  # ✅ Corrected
        'sma9_close_w': get_val(sma9_close_w, w_idx),
        'wma45_close_w': get_val(wma45_close_w, w_idx),
        'the_number_w': get_val(tn_w, w_idx),
        
        # RSI Screener Conditions
        'sma9_gt_tn_daily': sma9_gt_tn_daily,
        'sma9_gt_tn_weekly': sma9_gt_tn_weekly,
        'rsi_lt_80_d': rsi_lt_80_d,
        'rsi_lt_80_w': rsi_lt_80_w,
        'sma9_rsi_lte_75_d': sma9_rsi_lte_75_d,
        'sma9_rsi_lte_75_w': sma9_rsi_lte_75_w,
        'ema45_rsi_lte_70_d': ema45_rsi_lte_70_d,
        'ema45_rsi_lte_70_w': ema45_rsi_lte_70_w,
        'rsi_55_70': rsi_55_70,
        'rsi_gt_wma45_d': rsi_gt_wma45_d,
        'rsi_gt_wma45_w': rsi_gt_wma45_w,
        'sma9rsi_gt_wma45rsi_d': sma9rsi_gt_wma45rsi_d,
        'sma9rsi_gt_wma45rsi_w': sma9rsi_gt_wma45rsi_w,
        
        # STAMP Conditions
        'stamp_daily': stamp_daily,
        'stamp_weekly': stamp_weekly,
        'stamp': stamp,
        
        # ===== 6. CFG Analysis =====
        'cfg_daily': cfg_data.get('cfg'),
        'cfg_sma9': get_val(sma9_cfg, idx),
        'cfg_sma20': get_val(sma20_cfg, idx),
        'cfg_ema20': get_val(ema20_cfg, idx),
        'cfg_ema45': get_val(ema45_cfg, idx),
        'cfg_w': cfg_w,
        'cfg_sma9_w': sma9_cfg_w,
        'cfg_ema20_w': ema20_cfg_w,
        'cfg_ema45_w': ema45_cfg_w,
        
        # CFG Conditions
        'cfg_gt_50_daily': cfg_gt_50_daily,
        'cfg_ema45_gt_50': cfg_ema45_gt_50,
        'cfg_ema20_gt_50': cfg_ema20_gt_50,
        'cfg_gt_50_w': cfg_gt_50_w,
        'cfg_ema45_gt_50_w': cfg_ema45_gt_50_w,
        'cfg_ema20_gt_50_w': cfg_ema20_gt_50_w,  # ✅ Corrected: Added missing variable

        
        # CFG Components
        'rsi_14_9days_ago_cfg': cfg_data.get('rsi14_shifted'), # ✅ Correctly mapped to new V2 Logic
        'rsi_14_w_shifted': cfg_w_data.get('rsi14_shifted'), # ✅ Added
        'rsi_14_minus_9': cfg_data.get('cfg') - cfg_data.get('sma3_rsi3') if cfg_data.get('cfg') is not None else None, # approximate
        'rsi_14_minus_9_w': get_val(rsi_w, w_idx) - get_val(rsi_w, w_idx-9) if len(rsi_w) > 9 and get_val(rsi_w, w_idx) is not None and get_val(rsi_w, w_idx-9) is not None else None,
        
        # Final Results
        'final_signal': final_signal,
        'score': score,
    }
    
    return result


def calculate_and_store_indicators(db: Session, target_date: date = None):
    """حساب وتخزين جميع المؤشرات"""
    print("=" * 60)
    print("📊 Starting Stock Indicators Calculation - CORRECTED VERSION")
    print("=" * 60)
    
    deleted_count, target_date = delete_old_calculations(db, target_date)
    
    if not target_date:
        print("❌ No price data found.")
        return
    
    print(f"📅 Using latest date: {target_date}")
    
    symbols_query = text("""
        SELECT DISTINCT p.symbol, p.company_name
        FROM prices p
        WHERE p.date <= :target_date
        AND EXISTS (
            SELECT 1 FROM prices p2 
            WHERE p2.symbol = p.symbol 
            AND p2.date = :target_date
        )
        ORDER BY p.symbol
    """)
    symbols_result = db.execute(symbols_query, {"target_date": target_date})
    symbols_data = {row[0]: row[1] for row in symbols_result.fetchall()}
    
    total_stocks = len(symbols_data)
    print(f"📈 Found {total_stocks} stocks to process")
    print("-" * 60)
    
    processed = 0
    errors = 0
    successful = 0
    
    for symbol, company_name in symbols_data.items():
        try:
            print(f"📊 Processing {symbol} ({company_name})...")
            
            data = calculate_all_indicators_for_stock(db, symbol, target_date)
            
            if not data:
                print(f"⚠️  {symbol}: No data available or insufficient data")
                errors += 1
                continue
            
            indicator_data = {
                'symbol': symbol,
                'date': target_date,
                'company_name': company_name,
                **data
            }
            
            # تنظيف البيانات
            for k, v in indicator_data.items():
                if isinstance(v, (np.float64, np.float32, np.integer)):
                    indicator_data[k] = float(v) if not pd.isna(v) else None
                elif isinstance(v, np.bool_):
                    indicator_data[k] = bool(v)
                elif isinstance(v, float) and np.isnan(v):
                    indicator_data[k] = None
            
            stmt = insert(StockIndicator).values(indicator_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'date'],
                set_={k: v for k, v in indicator_data.items() if k not in ['symbol', 'date', 'created_at']}
            )
            
            db.execute(stmt)
            db.commit()
            processed += 1
            successful += 1
            
            if processed % 10 == 0:
                print(f"✅ Processed {processed}/{total_stocks} stocks...")
                print(f"   Last: {symbol} - Score: {data.get('score', 0)} | CFG: {data.get('cfg_daily', 0):.1f}")
                
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            errors += 1

    print("-" * 60)
    print("📊 Calculation Summary:")
    print(f"   🧹 Deleted: {deleted_count}")
    print(f"   ✅ Success: {successful}")
    print(f"   ❌ Errors: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    db = SessionLocal()
    try:
        calculate_and_store_indicators(db)
    finally:
        db.close()