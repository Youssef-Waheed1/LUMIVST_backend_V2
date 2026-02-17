"""
test_rsi_with_unrounded_closes.py
Test RSI calculation with and without rounding
"""

import sys
from pathlib import Path
from datetime import date
import pandas as pd

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Direct calculation without database to avoid import issues
# Using hard-coded test data from the debug output

def calculate_rsi_wilder(prices, period=14):
    """Calculate RSI using Wilder's smoothing"""
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    rsi_values = [None] * len(prices)
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    seed = sum(deltas[:period]) / period
    up_sum = seed if seed > 0 else 0
    down_sum = -seed if seed < 0 else 0
    
    rsi_values[period] = 100 - (100 / (1 + (up_sum / down_sum))) if down_sum != 0 else 50
    
    for i in range(period + 1, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            up_move = delta
            down_move = 0
        else:
            up_move = 0
            down_move = -delta
        
        up_sum = (up_sum * (period - 1) + up_move) / period
        down_sum = (down_sum * (period - 1) + down_move) / period
        
        rs = up_sum / down_sum if down_sum != 0 else 1
        rsi_values[i] = 100 - (100 / (1 + rs))
    
    return rsi_values


# Weekly closes from debug output (last 10)
weekly_closes_ROUNDED = [144.8, 140.0, 140.4, 137.9, 134.4, 128.0, 130.0, 152.2, 159.8, 152.5]

# Same closes without rounding - slightly different (but debug output shows rounded)
# Let's assume the closes might be slightly different if not rounded

print("\n" + "="*80)
print("TESTING RSI WITH ROUNDED vs UNROUNDED CLOSES")
print("="*80)

try:
    from scripts.calculate_rsi_indicators import calculate_rsi_pinescript
    
    # Test with rounded (current)
    rsi_rounded = calculate_rsi_pinescript(weekly_closes_ROUNDED, 14)
    
    print(f"\nWith ROUNDED closes (current):")
    print(f"Last 10 RSI: {[round(x, 2) if x else None for x in rsi_rounded[-10:]]}")
    print(f"Last RSI: {rsi_rounded[-1]:.2f}")
    
    # Also test with slightly modified closes to see sensitivity
    weekly_closes_SLIGHTLY_HIGHER = [x + 0.05 for x in weekly_closes_ROUNDED]
    rsi_slightly_higher = calculate_rsi_pinescript(weekly_closes_SLIGHTLY_HIGHER, 14)
    
    print(f"\nWith closes +0.05 each (sensitivity test):")
    print(f"Last RSI: {rsi_slightly_higher[-1]:.2f}")
    print(f"Difference: {rsi_slightly_higher[-1] - rsi_rounded[-1]:+.2f}")
    
    # Try with more dramatic difference
    weekly_closes_HIGHER = [x + 0.5 for x in weekly_closes_ROUNDED]
    rsi_higher = calculate_rsi_pinescript(weekly_closes_HIGHER, 14)
    
    print(f"\nWith closes +0.5 each:")
    print(f"Last RSI: {rsi_higher[-1]:.2f}")
    print(f"Difference: {rsi_higher[-1] - rsi_rounded[-1]:+.2f}")
    
    expected_rsi = 61.38
    print(f"\nTarget (TradingView): {expected_rsi:.2f}")
    print(f"Current (Python): {rsi_rounded[-1]:.2f}")
    print(f"Needed increase: {expected_rsi - rsi_rounded[-1]:+.2f}")
    
    # Binary search for what close adjustment would match
    needed_diff = expected_rsi - rsi_rounded[-1]
    test_close_adjustment = needed_diff * 0.15  # rough estimate based on the +0.5 test above
    weekly_closes_ADJUSTED = [x + test_close_adjustment for x in weekly_closes_ROUNDED]
    rsi_adjusted = calculate_rsi_pinescript(weekly_closes_ADJUSTED, 14)
    
    print(f"\nIf closes were +{test_close_adjustment:.3f} each:")
    print(f"Last RSI: {rsi_adjusted[-1]:.2f}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
