
import sys
import os
sys.path.append(os.getcwd())

try:
    from app.services.technical_indicators import wma, sma, rsi, ema
    import pandas as pd
    import numpy as np

    print("Import successful. Testing wma function...")
    
    # Test wma
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    w = wma(s, 5)
    print(f"WMA result (last value): {w.iloc[-1]}")
    
    print("Test passed!")
    
except Exception as e:
    print(f"Test Failed: {e}")
    import traceback
    traceback.print_exc()
