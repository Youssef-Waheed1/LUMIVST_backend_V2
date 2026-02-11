#!/usr/bin/env python
"""Comprehensive verification of all indicators mapping"""

import re
import json

# Frontend file content
with open(r'd:/Work/LUMIVST/frontend/app/technical-screener/page.tsx', 'r', encoding='utf-8') as f:
    frontend_content = f.read()

# Extract all field usages from Frontend
frontend_fields = set()
pattern = r'(?:selectedStock|stock)\.([\w_]+)'
matches = re.findall(pattern, frontend_content)
frontend_fields.update(matches)

# Load API response function
with open(r'd:/Work/LUMIVST/backend/app/api/routes/technical_screener.py', 'r', encoding='utf-8') as f:
    api_content = f.read()

# Extract all fields from indicator_to_dict
api_fields = set()
pattern = r"'([\w_]+)':\s*(?:float|int|bool|str)"
matches = re.findall(pattern, api_content)
api_fields.update(matches)

# Also look for dict returns
pattern = r"'([\w_]+)':\s*"
matches = re.findall(pattern, api_content)
api_fields.update(matches)

# Fields from Frontend interface
interface_fields = {
    'symbol', 'company_name', 'date', 'close',
    'rsi', 'rsi_14', 'sma9_rsi', 'wma45_rsi', 'ema45_rsi',
    'e45_cfg', 'e20_sma3_rsi3',
    'sma9_close', 'the_number', 'the_number_hl', 'the_number_ll',
    'rsi_14_9_days_ago', 'rsi_3', 'sma3_rsi3', 'stamp_a_value',
    'stamp_s9rsi', 'stamp_e45cfg', 'stamp_e45rsi', 'stamp_e20sma3',
    'sma4', 'sma9', 'sma18', 'sma4_w', 'sma9_w', 'sma18_w', 'close_w',
    'cci', 'cci_ema20', 'cci_ema20_w',
    'aroon_up', 'aroon_down', 'aroon_up_w', 'aroon_down_w',
    'rsi_w', 'rsi_3_w', 'sma3_rsi3_w', 'sma9_rsi_w', 'wma45_rsi_w', 'ema45_rsi_w',
    'ema20_sma3_rsi3_w', 'the_number_w',
    'cfg_daily', 'cfg_w', 'cfg_sma9', 'cfg_ema45',
    'cfg_gt_50_daily', 'cfg_gt_50_weekly', 'cfg_ema45_gt_50',
    'rsi_14_shifted', 'rsi_14_minus_9', 'rsi_14_w_shifted',
    'final_signal', 'score', 'trend_signal', 'stamp',
    'sma9_gt_tn_daily', 'sma9_gt_tn_weekly',
    'rsi_lt_80_d', 'rsi_lt_80_w',
    'sma9_rsi_lte_75_d', 'sma9_rsi_lte_75_w',
    'ema45_rsi_lte_70_d', 'ema45_rsi_lte_70_w',
    'rsi_55_70', 'rsi_gt_wma45_d', 'rsi_gt_wma45_w',
    'sma9rsi_gt_wma45rsi_d', 'sma9rsi_gt_wma45rsi_w',
    'stamp_daily', 'stamp_weekly',
    'price_gt_sma18', 'price_gt_sma9_weekly',
    'sma_trend_daily', 'sma_trend_weekly',
    'cci_gt_100', 'cci_ema20_gt_0_daily', 'cci_ema20_gt_0_weekly',
    'aroon_up_gt_70', 'aroon_down_lt_30',
    'is_etf_or_index', 'has_gap',
    'cfg_weekly'
}

print("=" * 70)
print("📊 COMPREHENSIVE INDICATORS VERIFICATION")
print("=" * 70)

print(f"\n✅ Frontend Interface Fields: {len(interface_fields)}")
print(f"✅ API Response Fields: {len(api_fields)}")
print(f"✅ Frontend Using Fields: {len(frontend_fields)}")

# Check missing fields
missing_in_api = interface_fields - api_fields
missing_in_frontend = (interface_fields | api_fields) - frontend_fields

if missing_in_api:
    print(f"\n❌ MISSING IN API ({len(missing_in_api)}):")
    for field in sorted(missing_in_api):
        print(f"   - {field}")
else:
    print("\n✅ All interface fields are in API response!")

if missing_in_frontend:
    print(f"\n⚠️  Not used in Frontend UI ({len(missing_in_frontend)}):")
    for field in sorted(missing_in_frontend):
        if field not in ['wma45_rsi_screener', 'ema45_cfg_w', 'ema20_sma3_w', 
                         'rsi_w_9_weeks_ago', 'cfg_weekly', 'rsi_14_9days_ago_cfg', 'wma45_close']:
            print(f"   - {field}")

# Verify specific critical fields
critical_fields = [
    'rsi', 'cfg_daily', 'the_number', 'the_number_hl', 'the_number_ll',
    'aroon_up_w', 'aroon_down_w', 'ema20_sma3_rsi3_w', 'e45_cfg', 'e20_sma3_rsi3',
    'rsi_14_shifted', 'rsi_14_minus_9', 'rsi_14_9_days_ago'
]

print(f"\n🔍 CRITICAL FIELDS CHECK ({len(critical_fields)}):")
for field in critical_fields:
    in_api = field in api_fields
    in_frontend = field in frontend_fields
    status = "✅" if (in_api and in_frontend) else "❌"
    print(f"   {status} {field}: API={in_api}, Frontend={in_frontend}")

print("\n" + "=" * 70)
