
import sys
import os
import json
from decimal import Decimal
import numpy as np

sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from app.services.technical_indicators import calculate_all_indicators_for_stock
from sqlalchemy import text

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        return super(DecimalEncoder, self).default(obj)

db = SessionLocal()
try:
    # Get a symbol
    symbol = db.execute(text("SELECT DISTINCT symbol FROM prices LIMIT 1")).scalar()
    print(f"Checking keys for symbol: {symbol}")
    
    data = calculate_all_indicators_for_stock(db, symbol)
    if data:
        print("\n--- ROOT KEYS ---")
        print(list(data.keys()))
        
        # Check specific screener keys logic
        print("\n--- SCREENER KEYS SAMPLE ---")
        screener_keys = [k for k in data.keys() if 'screener' in k]
        print(screener_keys[:20]) # Print first 20
        
        print("\n--- JSON OUTPUT SAMPLE ---")
        # Dump to verify serialization
        json_str = json.dumps(data, cls=DecimalEncoder)
        print("Serialization OK")
    else:
        print("No data returned")
finally:
    db.close()
