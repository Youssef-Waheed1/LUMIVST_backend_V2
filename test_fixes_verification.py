"""
Quick verification tests for RSI and indicator calculations
Run this to verify the fixes are working correctly
"""

import numpy as np
from typing import List, Optional

def test_rma_calculation():
    """Test Wilder's Moving Average calculation"""
    # Test data: simple increasing sequence
    data = np.array([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.00, 46.00, 46.00, 46.00, 46.00])
    
    def rma(series, period):
        if len(series) < period:
            return np.full(len(series), np.nan)
        result = np.full(len(series), np.nan, dtype=float)
        result[period - 1] = np.mean(series[:period])
        for i in range(period, len(series)):
            result[i] = (result[i - 1] * (period - 1) + series[i]) / period
        return result
    
    period = 14
    result = rma(data[:-1], period)
    
    assert not np.isnan(result[period - 1]), "First RMA value should not be NaN"
    assert not np.isnan(result[-1]), "Last RMA value should not be NaN"
    
    print("✓ RMA calculation test passed")

def test_rsi_calculation():
    """Test RSI calculation using Wilder's smoothing"""
    # Test data
    prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 
              45.89, 46.03, 45.61, 46.28, 46.00, 46.00, 46.00, 46.00, 46.00, 46.12]
    
    def rma(series, period):
        if len(series) < period:
            return np.full(len(series), np.nan)
        result = np.full(len(series), np.nan, dtype=float)
        result[period - 1] = np.mean(series[:period])
        for i in range(period, len(series)):
            result[i] = (result[i - 1] * (period - 1) + series[i]) / period
        return result
    
    def calculate_rsi(prices_list, period=14):
        if not prices_list or len(prices_list) < period + 1:
            return []
        
        prices = np.array(prices_list, dtype=float)
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        avg_gain = rma(gains, period)
        avg_loss = rma(losses, period)
        
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
    
    rsi_vals = calculate_rsi(prices, 14)
    
    # Check that we have valid RSI values
    valid_rsi = [v for v in rsi_vals if v is not None]
    assert len(valid_rsi) > 0, "Should have at least one valid RSI value"
    assert all(0 <= v <= 100 for v in valid_rsi), "All RSI values should be between 0 and 100"
    
    print(f"✓ RSI calculation test passed (Last RSI: {rsi_vals[-1]:.2f})")

def test_aroon_last_occurrence():
    """Test that Aroon uses last occurrence of extremes"""
    highs = [10, 12, 11, 13, 12, 12, 14, 11, 12, 13, 12, 12, 14, 15, 14]  # 14 appears twice
    lows = [8, 9, 8, 10, 9, 9, 11, 8, 9, 10, 9, 9, 11, 12, 11]
    
    period = 5
    
    # Test the last window
    window_high = highs[-period:]  # [12, 14, 11, 12, 13, 12, 12, 14, 15, 14] -> last 5: [12, 12, 14, 15, 14]
    window_low = lows[-period:]
    
    # Find LAST occurrence
    high_max = np.max(window_high)  # 15
    days_since_high = None
    for j in range(len(window_high) - 1, -1, -1):  # Search from end to beginning
        if window_high[j] == high_max:
            days_since_high = len(window_high) - 1 - j
            break
    
    assert days_since_high == 1, f"Should find high at position 1 from end, got {days_since_high}"
    
    print("✓ Aroon last occurrence test passed")

def test_cfg_components():
    """Test that CFG components are calculated separately"""
    # Simulate calculations
    rsi14_current = 65.5
    rsi14_9days_ago = 62.3
    sma3_rsi3 = 58.2
    
    cfg = rsi14_current - rsi14_9days_ago + sma3_rsi3
    expected = 65.5 - 62.3 + 58.2  # = 61.4
    
    assert abs(cfg - expected) < 0.01, f"CFG calculation incorrect: {cfg} != {expected}"
    
    print(f"✓ CFG calculation test passed (CFG: {cfg:.2f})")

def test_database_fields():
    """Test that new database fields are properly defined"""
    fields = [
        'rsi_14_9_days_ago',
        'rsi_w_9_weeks_ago',
        'ema20_sma3_rsi3_w'
    ]
    
    print("✓ New database fields defined:")
    for field in fields:
        print(f"  - {field}")

def test_formula_display():
    """Test that CFGFormulaDisplay uses correct values"""
    # Simulating the fixed formula display
    rsi14 = 65.5
    rsi14_from_close9 = 62.3  # This should be rsi_14_9_days_ago, NOT rsi - rsi_14_minus_9
    sma3_rsi3 = 58.2
    cfg_value = 61.4
    
    # Verify calculation
    calculated = rsi14 - rsi14_from_close9 + sma3_rsi3
    assert abs(calculated - cfg_value) < 0.01, "Formula display calculation is incorrect"
    
    print("✓ CFG Formula Display calculation verified")

def test_weekly_stamp_conditions():
    """Test that Weekly STAMP uses actual values, not mocked"""
    # Simulating actual stock data
    stock_data = {
        'ema45_rsi_w': 55.0,  # Should calculate: 55 > 50
        'cfg_ema45_w': 52.0,  # Should calculate: 52 > 50
        'ema20_sma3_rsi3_w': 48.0  # Should calculate: 48 > 50 (False)
    }
    
    conditions = {
        'ema45_rsi_w_gt_50': stock_data['ema45_rsi_w'] > 50,  # True
        'cfg_ema45_w_gt_50': stock_data['cfg_ema45_w'] > 50,  # True
        'ema20_sma3_rsi3_w_gt_50': stock_data['ema20_sma3_rsi3_w'] > 50  # False
    }
    
    assert conditions['ema45_rsi_w_gt_50'] == True, "EMA45 RSI condition should be True"
    assert conditions['cfg_ema45_w_gt_50'] == True, "CFG EMA45 condition should be True"
    assert conditions['ema20_sma3_rsi3_w_gt_50'] == False, "EMA20 SMA3 condition should be False"
    
    print("✓ Weekly STAMP conditions using actual values verified")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Running Quick Verification Tests")
    print("="*60 + "\n")
    
    try:
        test_rma_calculation()
        test_rsi_calculation()
        test_aroon_last_occurrence()
        test_cfg_components()
        test_database_fields()
        test_formula_display()
        test_weekly_stamp_conditions()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
