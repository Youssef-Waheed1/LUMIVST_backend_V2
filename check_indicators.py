#!/usr/bin/env python3
"""
فحص المؤشرات المتاحة في API
"""

import requests

def check_available_indicators():
    """فحص جميع المؤشرات المتاحة"""
    try:
        url = "http://localhost:8000/api/prices/history/1321?limit=1"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()['data'][0]
            indicators = [k for k, v in data.items()
                         if v is not None and isinstance(v, (int, float))
                         and k not in ['time', 'open', 'high', 'low', 'close', 'volume']]

            print('📊 المؤشرات المتاحة في API:')
            print('=' * 50)

            # تصنيف المؤشرات
            categories = {
                '📈 المتوسطات': [],
                '📊 RSI': [],
                '📉 THE NUMBER': [],
                '🎯 STAMP': [],
                '⚡ CFG': [],
                '📊 CCI': [],
                '🎪 AROON': [],
                '📊 إحصائيات السوق': []
            }

            for ind in indicators:
                if ind.startswith(('sma_', 'ema_', 'wma_')) or ind in ['sma4', 'sma9', 'sma18', 'wma45_close']:
                    categories['📈 المتوسطات'].append(ind)
                elif 'rsi' in ind.lower():
                    categories['📊 RSI'].append(ind)
                elif 'the_number' in ind:
                    categories['📉 THE NUMBER'].append(ind)
                elif 'stamp' in ind:
                    categories['🎯 STAMP'].append(ind)
                elif 'cfg' in ind:
                    categories['⚡ CFG'].append(ind)
                elif 'cci' in ind:
                    categories['📊 CCI'].append(ind)
                elif 'aroon' in ind:
                    categories['🎪 AROON'].append(ind)
                else:
                    categories['📊 إحصائيات السوق'].append(ind)

            for category, inds in categories.items():
                if inds:
                    print(f"\n{category} ({len(inds)}):")
                    for i, ind in enumerate(inds, 1):
                        print(f"  {i:2d}. {ind}")

            print(f"\n{'='*50}")
            print(f"🎯 إجمالي المؤشرات المتاحة: {len(indicators)}")
            return indicators
        else:
            print(f"❌ فشل في جلب البيانات: {response.status_code}")
            return []

    except Exception as e:
        print(f"❌ خطأ: {e}")
        return []

if __name__ == "__main__":
    check_available_indicators()