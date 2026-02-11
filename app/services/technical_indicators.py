"""
Technical Indicators Service
Based on TradingView PineScript indicators provided by استاذ ايمن

Implements:
1. RSI Indicator (Aymcfa-Abo Saad-RSI)
2. The Number Indicator
3. Stamp Indicator
4. Trend Screener (Aymcfa Trend Screener)
5. RSI Screener (Aymcfa RSI Screener)
6. CFG Analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period, min_periods=1).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    return series.rolling(window=period, min_periods=1).apply(
        lambda x: np.dot(x[-len(weights):], weights[-len(x):]) / weights[-len(x):].sum() if len(x) > 0 else np.nan,
        raw=True
    )


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using proper RMA (Relative Moving Average)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use EWM (exponential moving average) for RMA with alpha = 1/period
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values.fillna(50)


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Commodity Channel Index"""
    typical_price = (high + low + close) / 3
    moving_avg = typical_price.rolling(window=period, min_periods=1).mean()
    mean_deviation = typical_price.rolling(window=period, min_periods=1).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (typical_price - moving_avg) / (0.015 * mean_deviation)


def aroon(high: pd.Series, low: pd.Series, period: int = 25) -> Tuple[pd.Series, pd.Series]:
    """Aroon Up and Down Indicators"""
    aroon_up = pd.Series(index=high.index, dtype=float)
    aroon_down = pd.Series(index=low.index, dtype=float)
    
    for i in range(period, len(high)):
        high_window = high.iloc[i - period:i + 1]
        low_window = low.iloc[i - period:i + 1]
        
        days_since_high = period - high_window.argmax()
        days_since_low = period - low_window.argmin()
        
        aroon_up.iloc[i] = 100 * (period - days_since_high) / period
        aroon_down.iloc[i] = 100 * (period - days_since_low) / period
    
    return aroon_up, aroon_down


class RSIIndicator:
    """
    Aymcfa-Abo Saad-RSI Indicator
    
    Components:
    - RSI(14)
    - SMA9 of RSI
    - WMA45 of RSI
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate RSI indicator values"""
        close = df['close']
        
        rsi_14 = rsi(close, 14)
        sma9_rsi = sma(rsi_14, 9)
        wma45_rsi = wma(rsi_14, 45)
        
        latest = len(df) - 1
        
        return {
            'rsi': round(rsi_14.iloc[latest], 2) if not pd.isna(rsi_14.iloc[latest]) else None,
            'sma9_rsi': round(sma9_rsi.iloc[latest], 2) if not pd.isna(sma9_rsi.iloc[latest]) else None,
            'wma45_rsi': round(wma45_rsi.iloc[latest], 2) if not pd.isna(wma45_rsi.iloc[latest]) else None,
        }


class TheNumberIndicator:
    """
    The Number Indicator
    
    THE.NUMBER = (SMA(high,13) + SMA(low,13) + SMA(high,65) + SMA(low,65)) / 4
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate The Number indicator values"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        sma9_close = sma(close, 9)
        high13 = sma(high, 13)
        low13 = sma(low, 13)
        high65 = sma(high, 65)
        low65 = sma(low, 65)
        
        the_number = (high13 + low13 + high65 + low65) / 4
        the_number_hl = (high13 + high65) / 2  # Upper band
        the_number_ll = (low13 + low65) / 2    # Lower band
        
        latest = len(df) - 1
        
        return {
            'sma9': round(sma9_close.iloc[latest], 2) if not pd.isna(sma9_close.iloc[latest]) else None,
            'the_number': round(the_number.iloc[latest], 2) if not pd.isna(the_number.iloc[latest]) else None,
            'the_number_hl': round(the_number_hl.iloc[latest], 2) if not pd.isna(the_number_hl.iloc[latest]) else None,
            'the_number_ll': round(the_number_ll.iloc[latest], 2) if not pd.isna(the_number_ll.iloc[latest]) else None,
        }


class StampIndicator:
    """
    Aymcfa-Abo Saad-Stamp Indicator
    
    Custom formula: A = RSI(14) - Ref(RSI(14), -9) + SMA(RSI(3), 3)
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate Stamp indicator values"""
        close = df['close']
        
        rsi_14 = rsi(close, 14)
        rsi_3 = rsi(close, 3)
        
        # TradingView: a = rsi14 - ta.rsi(close[9], 14) + ta.sma(rsi3, 3)
        # ta.rsi(close[9], 14) means calculating RSI on the close series shifted by 9
        sma3_rsi3 = sma(rsi_3, 3)
        
        # Correct: Calculate RSI on shifted closes (Pine Script logic)
        # This is different from rsi(close).shift(9) because of Wilder's smoothing state depending on the path
        rsi_14_on_shifted_close = rsi(close.shift(9), 14)
        
        a = rsi_14 - rsi_14_on_shifted_close + sma3_rsi3
        
        s9_rsi = sma(rsi_14, 9)
        e45_cfg = ema(a, 45)
        e45_rsi = ema(rsi_14, 45)
        e20_sma3 = ema(sma3_rsi3, 20)
        
        latest = len(df) - 1
        
        return {
            's9_rsi': round(s9_rsi.iloc[latest], 2) if not pd.isna(s9_rsi.iloc[latest]) else None,
            'e45_cfg': round(e45_cfg.iloc[latest], 2) if not pd.isna(e45_cfg.iloc[latest]) else None,
            'e45_rsi': round(e45_rsi.iloc[latest], 2) if not pd.isna(e45_rsi.iloc[latest]) else None,
            'e20_sma3_rsi3': round(e20_sma3.iloc[latest], 2) if not pd.isna(e20_sma3.iloc[latest]) else None,
            'cfg': round(a.iloc[latest], 2) if not pd.isna(a.iloc[latest]) else None,
            'rsi_14_minus_9': round(rsi_14.iloc[latest] - rsi_14_on_shifted_close.iloc[latest], 2) if not pd.isna(rsi_14.iloc[latest]) and not pd.isna(rsi_14_on_shifted_close.iloc[latest]) else None,
            'sma3_rsi3': round(sma3_rsi3.iloc[latest], 2) if not pd.isna(sma3_rsi3.iloc[latest]) else None,
        }


class CFGIndicator:
    """
    CFG (Custom Formula Generator) Analysis
    A = RSI(14) - RSI(14)[9] + SMA(RSI(3), 3)
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict[str, Any]:
        """Correct CFG calculation matching PineScript"""
        close = df['close'].values
        
        # Calculate using new functions
        def calculate_rsi_window_numpy(prices, end_idx, period=14):
            if end_idx < period:
                return None
            
            # We need period+1 prices to get period deltas
            start_idx = end_idx - period
            if start_idx < 0:
                return None
            
            window = prices[start_idx:end_idx+1]
            if len(window) < period + 1:
                return None
                
            delta = np.diff(window)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            # Simple average for first value (Wilder's original method uses simple average for first period)
            # PineScript's rsi() function uses Wilder's smoothing.
            # But here we are calculating a single point.
            # If we want exact match with PineScript 'rsi(src, len)', it's recursive.
            # But 'rsi_window' usually implies we treat this window as the history.
            # If we treat it as initialization:
            avg_gain = np.mean(gain[:period])
            avg_loss = np.mean(loss[:period])
            
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100.0 - (100.0 / (1.0 + rs))
        
        # CFG Calculation
        cfg_values = []
        rsi3_series = [] # To store RSI(3) for SMA calculation
        
        # Pre-calculate RSI(3) for all points first or inside loop?
        # User code calculates rsi3 inside loop:
        # for j in range(max(0, i-2), i+1): rsi3 = calculate_rsi_window_numpy(close, j, 3)
        # This is O(N*3*3) which is fine. O(N).
        
        for i in range(len(close)):
            if i < 9:
                cfg_values.append(None)
                continue
                
            # 1. RSI(14) Current
            rsi14_current = calculate_rsi_window_numpy(close, i, 14)
            
            # 2. ta.rsi(close[9], 14) -> RSI of window ending at i-9
            rsi14_shifted = calculate_rsi_window_numpy(close, i-9, 14)
            
            if rsi14_current is None or rsi14_shifted is None:
                cfg_values.append(None)
                continue
            
            # 3. SMA(RSI(3), 3)
            # Need RSI(3) for j=i, i-1, i-2
            rsi3_vals = []
            for j in range(i-2, i+1):
                if j < 0: continue
                r3 = calculate_rsi_window_numpy(close, j, 3)
                if r3 is not None:
                    rsi3_vals.append(r3)
            
            sma3_rsi3 = np.mean(rsi3_vals) if len(rsi3_vals) == 3 else None
            
            if sma3_rsi3 is not None:
                cfg = rsi14_current - rsi14_shifted + sma3_rsi3
                cfg_values.append(cfg)
            else:
                cfg_values.append(None)
        
        cfg_series = pd.Series(cfg_values, index=df.index)
        
        # Averages
        cfg_sma9 = sma(cfg_series, 9)
        cfg_sma20 = sma(cfg_series, 20)
        cfg_ema20 = ema(cfg_series, 20)
        cfg_ema45 = ema(cfg_series, 45)
        
        latest = len(df) - 1
        
        # Ensure we have values
        cfg_val = cfg_series.iloc[latest]
        
        # Recalculate components for display
        rsi_3_val = calculate_rsi_window_numpy(close, latest, 3)
        
        # SMA3(RSI3)
        rsi3_vals_latest = []
        for j in range(latest-2, latest+1):
            if j >= 0:
                r3 = calculate_rsi_window_numpy(close, j, 3)
                if r3 is not None: rsi3_vals_latest.append(r3)
        sma3_rsi3_val = np.mean(rsi3_vals_latest) if len(rsi3_vals_latest) == 3 else None
        
        rsi14_latest = calculate_rsi_window_numpy(close, latest, 14)
        rsi14_shifted_latest = calculate_rsi_window_numpy(close, latest-9, 14)
        rsi_14_minus_9_val = (rsi14_latest - rsi14_shifted_latest) if (rsi14_latest is not None and rsi14_shifted_latest is not None) else None
        
        return {
            'cfg': round(cfg_val, 2) if not pd.isna(cfg_val) else None,
            'cfg_sma9': round(cfg_sma9.iloc[latest], 2) if not pd.isna(cfg_sma9.iloc[latest]) else None,
            'cfg_sma20': round(cfg_sma20.iloc[latest], 2) if not pd.isna(cfg_sma20.iloc[latest]) else None,
            'cfg_ema20': round(cfg_ema20.iloc[latest], 2) if not pd.isna(cfg_ema20.iloc[latest]) else None,
            'cfg_ema45': round(cfg_ema45.iloc[latest], 2) if not pd.isna(cfg_ema45.iloc[latest]) else None,
            'cfg_gt_50': cfg_val > 50 if not pd.isna(cfg_val) else False,
            'cfg_ema45_gt_50': cfg_ema45.iloc[latest] > 50 if not pd.isna(cfg_ema45.iloc[latest]) else False,
            'cfg_ema20_gt_50': cfg_ema20.iloc[latest] > 50 if not pd.isna(cfg_ema20.iloc[latest]) else False,
            'rsi_3': round(rsi_3_val, 2) if rsi_3_val is not None else None,
            'sma3_rsi3': round(sma3_rsi3_val, 2) if sma3_rsi3_val is not None else None,
            'rsi_14_minus_9': round(rsi_14_minus_9_val, 2) if rsi_14_minus_9_val is not None else None,
        }


class TrendScreener:
    """
    Aymcfa Trend Screener
    
    Conditions:
    1. Price > 18 SMA (Daily)
    2. Price > 9 SMA (Weekly)
    3. SMA 4 > SMA 9 > SMA 18 (Daily)
    4. SMA 4 > SMA 9 > SMA 18 (Weekly)
    5. CCI(14) > 100
    6. CCI EMA(20) > 0 (Daily)
    7. CCI EMA(20) > 0 (Weekly)
    8. Aroon Up > 70%
    9. Aroon Down < 30%
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame, weekly_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Calculate Trend Screener values"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Daily calculations
        sma4 = sma(close, 4)
        sma9 = sma(close, 9)
        sma18 = sma(close, 18)
        
        cci_14 = cci(high, low, close, 14)
        cci_ema20 = ema(cci_14, 20)
        
        aroon_up, aroon_down = aroon(high, low, 25)
        
        latest = len(df) - 1
        
        # Conditions
        price_gt_sma18 = close.iloc[latest] > sma18.iloc[latest]
        sma_trend_daily = (sma4.iloc[latest] > sma9.iloc[latest]) and (sma9.iloc[latest] > sma18.iloc[latest])
        cci_gt_100 = cci_14.iloc[latest] > 100
        cci_ema20_gt_0_daily = cci_ema20.iloc[latest] > 0
        aroon_up_gt_70 = aroon_up.iloc[latest] > 70 if not pd.isna(aroon_up.iloc[latest]) else False
        aroon_down_lt_30 = aroon_down.iloc[latest] < 30 if not pd.isna(aroon_down.iloc[latest]) else False
        
        # Weekly conditions (if weekly data provided)
        price_gt_sma9_weekly = True
        sma_trend_weekly = True
        cci_ema20_gt_0_weekly = True
        cci_ema20_w = None
        
        if weekly_df is not None and len(weekly_df) > 0:
            w_close = weekly_df['close']
            w_high = weekly_df['high']
            w_low = weekly_df['low']
            
            sma4_w = sma(w_close, 4)
            sma9_w = sma(w_close, 9)
            sma18_w = sma(w_close, 18)
            cci_w = cci(w_high, w_low, w_close, 14)
            cci_ema20_w = ema(cci_w, 20)
            
            w_latest = len(weekly_df) - 1
            
            price_gt_sma9_weekly = w_close.iloc[w_latest] > sma9_w.iloc[w_latest]
            sma_trend_weekly = (sma4_w.iloc[w_latest] > sma9_w.iloc[w_latest]) and (sma9_w.iloc[w_latest] > sma18_w.iloc[w_latest])
            cci_ema20_gt_0_weekly = cci_ema20_w.iloc[w_latest] > 0 if not pd.isna(cci_ema20_w.iloc[w_latest]) else False
            cci_ema20_w = round(cci_ema20_w.iloc[w_latest], 2) if not pd.isna(cci_ema20_w.iloc[w_latest]) else None
        
        # Final signal
        final_signal = all([
            price_gt_sma18, price_gt_sma9_weekly, sma_trend_daily, sma_trend_weekly,
            cci_gt_100, cci_ema20_gt_0_daily, cci_ema20_gt_0_weekly,
            aroon_up_gt_70, aroon_down_lt_30
        ])
        
        return {
            'price_gt_sma18': price_gt_sma18,
            'price_gt_sma9_weekly': price_gt_sma9_weekly,
            'sma_trend_daily': sma_trend_daily,
            'sma_trend_weekly': sma_trend_weekly,
            'cci_gt_100': cci_gt_100,
            'cci_ema20_gt_0_daily': cci_ema20_gt_0_daily,
            'cci_ema20_gt_0_weekly': cci_ema20_gt_0_weekly,
            'aroon_up_gt_70': aroon_up_gt_70,
            'aroon_down_lt_30': aroon_down_lt_30,
            'final_signal': final_signal,
            # Raw values
            'cci': round(cci_14.iloc[latest], 2) if not pd.isna(cci_14.iloc[latest]) else None,
            'cci_ema20': round(cci_ema20.iloc[latest], 2) if not pd.isna(cci_ema20.iloc[latest]) else None,
            'cci_ema20_w': cci_ema20_w,
            'aroon_up': round(aroon_up.iloc[latest], 2) if not pd.isna(aroon_up.iloc[latest]) else None,
            'aroon_down': round(aroon_down.iloc[latest], 2) if not pd.isna(aroon_down.iloc[latest]) else None,
        }


class RSIScreener:
    """
    Aymcfa RSI Screener (2026) Updated
    
    Main conditions:
    1. SMA9 > The Number (Daily & Weekly)
    2. RSI < 80 (Daily & Weekly)
    3. SMA9(RSI) <= 75 (Daily & Weekly)
    4. EMA45(RSI) <= 70 (Daily & Weekly)
    5. RSI(14) 55-70 (Daily)
    6. RSI > WMA45 (Daily & Weekly)
    7. SMA9 RSI > WMA45 RSI (Daily & Weekly)
    8. STAMP conditions (Daily & Weekly)
    """
    
    @staticmethod
    def calculate_full(df: pd.DataFrame, weekly_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Calculate all RSI Screener values"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Daily RSI calculations
        rsi_14 = rsi(close, 14)
        rsi_3 = rsi(close, 3)
        sma3_rsi3 = sma(rsi_3, 3)
        
        # TradingView: a = rsi14 - ta.rsi(close[9], 14) + ta.sma(rsi3, 3)
        # Correct: RSI on shifted close series
        rsi_14_on_shifted_close = rsi(close.shift(9), 14)
        cfg = rsi_14 - rsi_14_on_shifted_close + sma3_rsi3
        
        sma9_rsi = sma(rsi_14, 9)
        wma45_rsi = wma(rsi_14, 45)
        ema45_rsi = ema(rsi_14, 45)
        ema45_cfg = ema(cfg, 45)
        ema20_sma3 = ema(sma3_rsi3, 20)
        
        # Price averages
        sma9_close = sma(close, 9)
        wma45_close = wma(close, 45)
        
        # The Number
        high13 = sma(high, 13)
        low13 = sma(low, 13)
        high65 = sma(high, 65)
        low65 = sma(low, 65)
        the_number = (high13 + low13 + high65 + low65) / 4
        the_number_hl = (high13 + high65) / 2
        the_number_ll = (low13 + low65) / 2
        
        latest = len(df) - 1
        
        # STAMP conditions Daily
        stamp_1_d = sma9_close.iloc[latest] > wma45_close.iloc[latest]
        stamp_2_d = sma9_rsi.iloc[latest] > wma45_rsi.iloc[latest]
        stamp_3_d = ema45_rsi.iloc[latest] > 50
        stamp_4_d = ema45_cfg.iloc[latest] > 50 if not pd.isna(ema45_cfg.iloc[latest]) else False
        stamp_5_d = ema20_sma3.iloc[latest] > 50
        stamp_daily = all([stamp_1_d, stamp_2_d, stamp_3_d, stamp_4_d, stamp_5_d])
        
        # Main conditions Daily
        sma9_gt_tn_d = sma9_close.iloc[latest] > the_number.iloc[latest]
        rsi_lt_80_d = rsi_14.iloc[latest] < 80
        sma9_rsi_lte_75_d = sma9_rsi.iloc[latest] <= 75
        ema45_rsi_lte_70_d = ema45_rsi.iloc[latest] <= 70
        rsi_55_70_d = 55 <= rsi_14.iloc[latest] <= 70
        rsi_gt_wma45_d = rsi_14.iloc[latest] > wma45_rsi.iloc[latest]
        sma9rsi_gt_wma45rsi_d = sma9_rsi.iloc[latest] > wma45_rsi.iloc[latest]
        
        # Weekly calculations
        stamp_weekly = True
        sma9_gt_tn_w = True
        rsi_lt_80_w = True
        sma9_rsi_lte_75_w = True
        ema45_rsi_lte_70_w = True
        rsi_gt_wma45_w = True
        sma9rsi_gt_wma45rsi_w = True
        
        # CFG calculations
        cfg_sma9 = sma(cfg, 9)
        cfg_sma20 = sma(cfg, 20)
        cfg_ema20 = ema(cfg, 20)
        cfg_ema45 = ema(cfg, 45)
        
        cfg_gt_50 = cfg.iloc[latest] > 50 if not pd.isna(cfg.iloc[latest]) else False
        cfg_ema45_gt_50 = cfg_ema45.iloc[latest] > 50 if not pd.isna(cfg_ema45.iloc[latest]) else False
        cfg_ema20_gt_50 = cfg_ema20.iloc[latest] > 50 if not pd.isna(cfg_ema20.iloc[latest]) else False
        
        weekly_data = {}
        cfg_weekly_data = {}
        
        if weekly_df is not None and len(weekly_df) > 0:
            w_close = weekly_df['close']
            w_high = weekly_df['high']
            w_low = weekly_df['low']
            
            # Weekly RSI
            w_rsi_14 = rsi(w_close, 14)
            w_rsi_3 = rsi(w_close, 3)
            w_sma3_rsi3 = sma(w_rsi_3, 3)
            
            # TradingView: rsi14[9] -> rsi(close[9], 14)
            w_rsi_14_on_shifted_close = rsi(w_close.shift(9), 14)
            w_cfg = w_rsi_14 - w_rsi_14_on_shifted_close + w_sma3_rsi3
            
            w_sma9_rsi = sma(w_rsi_14, 9)
            w_wma45_rsi = wma(w_rsi_14, 45)
            w_ema45_rsi = ema(w_rsi_14, 45)
            w_ema45_cfg = ema(w_cfg, 45)
            w_ema20_sma3 = ema(w_sma3_rsi3, 20)
            
            w_sma9_close = sma(w_close, 9)
            w_wma45_close = wma(w_close, 45)
            
            w_high13 = sma(w_high, 13)
            w_low13 = sma(w_low, 13)
            w_high65 = sma(w_high, 65)
            w_low65 = sma(w_low, 65)
            w_the_number = (w_high13 + w_low13 + w_high65 + w_low65) / 4
            
            # Weekly CFG
            w_cfg_sma9 = sma(w_cfg, 9)
            w_cfg_ema20 = ema(w_cfg, 20)
            w_cfg_ema45 = ema(w_cfg, 45)
            
            w_latest = len(weekly_df) - 1
            
            # Weekly STAMP
            stamp_1_w = w_sma9_close.iloc[w_latest] > w_wma45_close.iloc[w_latest]
            stamp_2_w = w_sma9_rsi.iloc[w_latest] > w_wma45_rsi.iloc[w_latest]
            stamp_3_w = w_ema45_rsi.iloc[w_latest] > 50
            stamp_4_w = w_ema45_cfg.iloc[w_latest] > 50 if not pd.isna(w_ema45_cfg.iloc[w_latest]) else False
            stamp_5_w = w_ema20_sma3.iloc[w_latest] > 50
            stamp_weekly = all([stamp_1_w, stamp_2_w, stamp_3_w, stamp_4_w, stamp_5_w])
            
            # Weekly main conditions
            sma9_gt_tn_w = w_sma9_close.iloc[w_latest] > w_the_number.iloc[w_latest]
            rsi_lt_80_w = w_rsi_14.iloc[w_latest] < 80
            sma9_rsi_lte_75_w = w_sma9_rsi.iloc[w_latest] <= 75
            ema45_rsi_lte_70_w = w_ema45_rsi.iloc[w_latest] <= 70
            rsi_gt_wma45_w = w_rsi_14.iloc[w_latest] > w_wma45_rsi.iloc[w_latest]
            sma9rsi_gt_wma45rsi_w = w_sma9_rsi.iloc[w_latest] > w_wma45_rsi.iloc[w_latest]
            
            weekly_data = {
                'rsi_w': round(w_rsi_14.iloc[w_latest], 2) if not pd.isna(w_rsi_14.iloc[w_latest]) else None,
                'sma9_rsi_w': round(w_sma9_rsi.iloc[w_latest], 2) if not pd.isna(w_sma9_rsi.iloc[w_latest]) else None,
                'wma45_rsi_w': round(w_wma45_rsi.iloc[w_latest], 2) if not pd.isna(w_wma45_rsi.iloc[w_latest]) else None,
                'ema45_rsi_w': round(w_ema45_rsi.iloc[w_latest], 2) if not pd.isna(w_ema45_rsi.iloc[w_latest]) else None,
                'the_number_w': round(w_the_number.iloc[w_latest], 2) if not pd.isna(w_the_number.iloc[w_latest]) else None,
                'sma9_close_w': round(w_sma9_close.iloc[w_latest], 2) if not pd.isna(w_sma9_close.iloc[w_latest]) else None,
            }
            
            cfg_weekly_data = {
                'cfg_w': round(w_cfg.iloc[w_latest], 2) if not pd.isna(w_cfg.iloc[w_latest]) else None,
                'cfg_sma9_w': round(w_cfg_sma9.iloc[w_latest], 2) if not pd.isna(w_cfg_sma9.iloc[w_latest]) else None,
                'cfg_ema20_w': round(w_cfg_ema20.iloc[w_latest], 2) if not pd.isna(w_cfg_ema20.iloc[w_latest]) else None,
                'cfg_ema45_w': round(w_cfg_ema45.iloc[w_latest], 2) if not pd.isna(w_cfg_ema45.iloc[w_latest]) else None,
                'cfg_gt_50_w': w_cfg.iloc[w_latest] > 50 if not pd.isna(w_cfg.iloc[w_latest]) else False,
                'cfg_ema45_gt_50_w': w_cfg_ema45.iloc[w_latest] > 50 if not pd.isna(w_cfg_ema45.iloc[w_latest]) else False,
                'cfg_ema20_gt_50_w': w_cfg_ema20.iloc[w_latest] > 50 if not pd.isna(w_cfg_ema20.iloc[w_latest]) else False,
                'rsi_3_w': round(w_rsi_3.iloc[w_latest], 2) if not pd.isna(w_rsi_3.iloc[w_latest]) else None,
                'sma3_rsi3_w': round(w_sma3_rsi3.iloc[w_latest], 2) if not pd.isna(w_sma3_rsi3.iloc[w_latest]) else None,
                'rsi_14_minus_9_w': round(w_rsi_14.iloc[w_latest] - w_rsi_14_on_shifted_close.iloc[w_latest], 2) if not pd.isna(w_rsi_14.iloc[w_latest]) and not pd.isna(w_rsi_14_on_shifted_close.iloc[w_latest]) else None,
            }
        
        # Full STAMP
        stamp = stamp_daily and stamp_weekly
        
        # Final Signal
        final_signal = all([
            stamp,
            sma9_gt_tn_d, sma9_gt_tn_w,
            rsi_lt_80_d, rsi_lt_80_w,
            sma9_rsi_lte_75_d, sma9_rsi_lte_75_w,
            ema45_rsi_lte_70_d, ema45_rsi_lte_70_w,
            rsi_55_70_d,
            rsi_gt_wma45_d, rsi_gt_wma45_w,
            sma9rsi_gt_wma45rsi_d, sma9rsi_gt_wma45rsi_w
        ])
        
        # Calculate scores (count of true conditions out of 15)
        conditions = [
            stamp_daily, stamp_weekly,
            sma9_gt_tn_d, sma9_gt_tn_w,
            rsi_lt_80_d, rsi_lt_80_w,
            sma9_rsi_lte_75_d, sma9_rsi_lte_75_w,
            ema45_rsi_lte_70_d, ema45_rsi_lte_70_w,
            rsi_55_70_d,
            rsi_gt_wma45_d, rsi_gt_wma45_w,
            sma9rsi_gt_wma45rsi_d, sma9rsi_gt_wma45rsi_w
        ]
        score = sum(1 for c in conditions if c)
        
        result = {
            # Raw values Daily
            'rsi': round(rsi_14.iloc[latest], 2) if not pd.isna(rsi_14.iloc[latest]) else None,
            'sma9_rsi': round(sma9_rsi.iloc[latest], 2) if not pd.isna(sma9_rsi.iloc[latest]) else None,
            'wma45_rsi': round(wma45_rsi.iloc[latest], 2) if not pd.isna(wma45_rsi.iloc[latest]) else None,
            'ema45_rsi': round(ema45_rsi.iloc[latest], 2) if not pd.isna(ema45_rsi.iloc[latest]) else None,
            'the_number': round(the_number.iloc[latest], 2) if not pd.isna(the_number.iloc[latest]) else None,
            'the_number_hl': round(the_number_hl.iloc[latest], 2) if not pd.isna(the_number_hl.iloc[latest]) else None,
            'the_number_ll': round(the_number_ll.iloc[latest], 2) if not pd.isna(the_number_ll.iloc[latest]) else None,
            'sma9_close': round(sma9_close.iloc[latest], 2) if not pd.isna(sma9_close.iloc[latest]) else None,
            
            # Stamp
            'e45_cfg': round(ema45_cfg.iloc[latest], 2) if not pd.isna(ema45_cfg.iloc[latest]) else None,
            'e20_sma3_rsi3': round(ema20_sma3.iloc[latest], 2) if not pd.isna(ema20_sma3.iloc[latest]) else None,
            'stamp_daily': stamp_daily,
            'stamp_weekly': stamp_weekly,
            'stamp': stamp,
            
            # Conditions Daily
            'sma9_gt_tn_daily': sma9_gt_tn_d,
            'rsi_lt_80_d': rsi_lt_80_d,
            'sma9_rsi_lte_75_d': sma9_rsi_lte_75_d,
            'ema45_rsi_lte_70_d': ema45_rsi_lte_70_d,
            'rsi_55_70': rsi_55_70_d,
            'rsi_gt_wma45_d': rsi_gt_wma45_d,
            'sma9rsi_gt_wma45rsi_d': sma9rsi_gt_wma45rsi_d,
            
            # Conditions Weekly
            'sma9_gt_tn_weekly': sma9_gt_tn_w,
            'rsi_lt_80_w': rsi_lt_80_w,
            'sma9_rsi_lte_75_w': sma9_rsi_lte_75_w,
            'ema45_rsi_lte_70_w': ema45_rsi_lte_70_w,
            'rsi_gt_wma45_w': rsi_gt_wma45_w,
            'sma9rsi_gt_wma45rsi_w': sma9rsi_gt_wma45rsi_w,
            
            # CFG values
            'cfg': round(cfg.iloc[latest], 2) if not pd.isna(cfg.iloc[latest]) else None,
            'cfg_sma9': round(cfg_sma9.iloc[latest], 2) if not pd.isna(cfg_sma9.iloc[latest]) else None,
            'cfg_sma20': round(cfg_sma20.iloc[latest], 2) if not pd.isna(cfg_sma20.iloc[latest]) else None,
            'cfg_ema20': round(cfg_ema20.iloc[latest], 2) if not pd.isna(cfg_ema20.iloc[latest]) else None,
            'cfg_ema45': round(cfg_ema45.iloc[latest], 2) if not pd.isna(cfg_ema45.iloc[latest]) else None,
            'cfg_gt_50': cfg_gt_50,
            'cfg_ema45_gt_50': cfg_ema45_gt_50,
            'cfg_ema20_gt_50': cfg_ema20_gt_50,
            
            # CFG components
            'rsi_3': round(rsi_3.iloc[latest], 2) if not pd.isna(rsi_3.iloc[latest]) else None,
            'sma3_rsi3': round(sma3_rsi3.iloc[latest], 2) if not pd.isna(sma3_rsi3.iloc[latest]) else None,
            'rsi_14_minus_9': round(rsi_14.iloc[latest] - rsi_14_on_shifted_close.iloc[latest], 2) if not pd.isna(rsi_14.iloc[latest]) and not pd.isna(rsi_14_on_shifted_close.iloc[latest]) else None,
            
            # Final
            'final_signal': final_signal,
            'score': score,
            'total_conditions': 15,
            
            # Weekly raw values
            **weekly_data,
            **cfg_weekly_data
        }
        
        return result


def get_stock_prices(db: Session, symbol: str, days: int = 365) -> pd.DataFrame:
    """Fetch stock price data from database"""
    query = text("""
        SELECT date, open, high, low, close, volume_traded as volume
        FROM prices
        WHERE symbol = :symbol
        ORDER BY date DESC
        LIMIT :days
    """)
    
    result = db.execute(query, {"symbol": symbol, "days": days})
    rows = result.fetchall()
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Convert to float
    for col in ['open', 'high', 'low', 'close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily data to weekly"""
    if daily_df.empty:
        return pd.DataFrame()
    
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    weekly = df.resample('W').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    weekly = weekly.reset_index()
    return weekly


def calculate_all_indicators_for_stock(db: Session, symbol: str) -> Dict[str, Any]:
    """Calculate all technical indicators for a single stock"""
    # Get daily data (min 365 days for weekly calculations)
    daily_df = get_stock_prices(db, symbol, days=500)
    
    if daily_df.empty or len(daily_df) < 50:
        return None
    
    # Resample to weekly
    weekly_df = resample_to_weekly(daily_df)
    
    # Calculate all indicators
    result = {
        'symbol': symbol,
        'date': str(daily_df['date'].iloc[-1]),
        'close': float(daily_df['close'].iloc[-1]),
    }
    
    # RSI Indicator
    rsi_data = RSIIndicator.calculate(daily_df)
    result.update({f'rsi_{k}': v for k, v in rsi_data.items()})
    
    # The Number Indicator
    number_data = TheNumberIndicator.calculate(daily_df)
    result.update({f'number_{k}': v for k, v in number_data.items()})
    
    # Stamp Indicator
    stamp_data = StampIndicator.calculate(daily_df)
    result.update({f'stamp_{k}': v for k, v in stamp_data.items()})
    
    # CFG Indicator
    cfg_data = CFGIndicator.calculate(daily_df)
    result.update({f'cfg_{k}': v for k, v in cfg_data.items()})
    
    # Trend Screener
    trend_data = TrendScreener.calculate(daily_df, weekly_df)
    result.update({f'trend_{k}': v for k, v in trend_data.items()})
    
    # RSI Screener
    rsi_screener_data = RSIScreener.calculate_full(daily_df, weekly_df)
    result.update({f'screener_{k}': v for k, v in rsi_screener_data.items()})
    
    return result


def run_full_screener(db: Session) -> List[Dict[str, Any]]:
    """Run the full screener on all stocks"""
    # Get all symbols
    query = text("SELECT DISTINCT symbol FROM prices WHERE date = (SELECT MAX(date) FROM prices)")
    result = db.execute(query)
    symbols = [row[0] for row in result.fetchall()]
    
    results = []
    for symbol in symbols:
        try:
            data = calculate_all_indicators_for_stock(db, symbol)
            if data:
                results.append(data)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    # Sort by screener score
    results.sort(key=lambda x: x.get('screener_score', 0), reverse=True)
    
    return results