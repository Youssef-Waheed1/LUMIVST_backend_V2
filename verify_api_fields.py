#!/usr/bin/env python
"""Verify that all Frontend-expected fields are present in API response"""

import sys
import json
from app.core.database import SessionLocal
from app.models.stock_indicators import StockIndicator
from app.api.routes.technical_screener import indicator_to_dict

db = SessionLocal()
latest = db.query(StockIndicator).order_by(StockIndicator.date.desc()).first()

if latest:
    data = indicator_to_dict(latest)
    
    # Expected fields from Frontend
    expected_fields = [
        'symbol', 'company_name', 'date', 'close',
        'rsi', 'rsi_14', 'sma9_rsi', 'wma45_rsi',
        'the_number', 'the_number_hl', 'the_number_ll',
        'rsi_14_9_days_ago', 'sma3_rsi3', 'stamp_a_value',
        'sma4', 'sma9', 'sma18', 'sma4_w', 'sma9_w', 'sma18_w', 'close_w',
        'cci', 'cci_ema20', 'cci_ema20_w',
        'aroon_up', 'aroon_down', 'aroon_up_w', 'aroon_down_w',
        'e45_cfg', 'e20_sma3_rsi3',
        'rsi_w', 'sma9_rsi_w', 'wma45_rsi_w', 'ema45_rsi_w',
        'ema20_sma3_rsi3_w', 'the_number_w',
        'cfg_daily', 'cfg_w', 'cfg_gt_50_daily', 'cfg_gt_50_weekly',
        'rsi_14_shifted', 'rsi_14_minus_9', 'rsi_14_w_shifted',
        'cfg_ema45_gt_50', 'final_signal', 'score'
    ]
    
    missing = []
    present = []
    none_values = {}
    
    for field in expected_fields:
        if field in data:
            present.append(field)
            if data[field] is None or data[field] == '':
                none_values[field] = data[field]
        else:
            missing.append(field)
    
    print(f"✅ Present fields: {len(present)}/{len(expected_fields)}")
    print(f"❌ Missing fields: {len(missing)}")
    
    if missing:
        print("\nMissing fields:")
        for f in missing:
            print(f"   - {f}")
    
    if none_values:
        print(f"\n⚠️  Fields with None/Empty values ({len(none_values)}):")
        for field, val in none_values.items():
            print(f"   - {field}: {repr(val)}")
    
    # Print sample of data
    print(f"\n📊 Sample Data (Symbol: {data['symbol']}, Date: {data['date']}):")
    sample_fields = ['rsi', 'e45_cfg', 'ema20_sma3_rsi3_w', 'cfg_daily', 'score']
    for field in sample_fields:
        if field in data:
            print(f"   {field}: {data[field]}")

else:
    print("❌ No data found in database")

db.close()
