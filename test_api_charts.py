#!/usr/bin/env python3
"""
اختبار API endpoint للرسوم البيانية
"""

import requests
import json

def test_api_endpoint():
    """اختبار API endpoint لجلب بيانات الرسوم البيانية"""
    try:
        url = "http://localhost:8000/api/prices/history/1321?limit=5"
        print(f"🔗 جاري اختبار: {url}")

        response = requests.get(url, timeout=10)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            records = data.get('data', [])

            print(f"✅ تم جلب {len(records)} نقطة بيانات")

            if records:
                first_record = records[0]
                print("\n📈 أول نقطة بيانات:")
                print(json.dumps(first_record, indent=2, ensure_ascii=False))

                # التحقق من وجود المؤشرات
                indicators_found = []
                for key in ['rsi_14', 'cfg_daily', 'the_number', 'cci', 'sma_10', 'sma_200', 'ema_10']:
                    if key in first_record and first_record[key] is not None:
                        indicators_found.append(f"{key}: {first_record[key]}")

                if indicators_found:
                    print(f"\n🎯 المؤشرات الموجودة ({len(indicators_found)}):")
                    for ind in indicators_found[:10]:  # أظهر أول 10
                        print(f"  • {ind}")
                    if len(indicators_found) > 10:
                        print(f"  ... و {len(indicators_found) - 10} مؤشر آخر")
                else:
                    print("⚠️ لم يتم العثور على مؤشرات في البيانات")

            return True
        else:
            print(f"❌ خطأ في API: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 اختبار API endpoint للرسوم البيانية")
    print("="*60)

    success = test_api_endpoint()

    if success:
        print("\n✅ API يعمل بنجاح!")
        print("📊 يمكنك الآن فتح صفحة stocks/charts لرؤية الرسوم البيانية")
    else:
        print("\n❌ فشل في اختبار API")
        print("🔧 تأكد من أن الخادم يعمل على http://localhost:8000")

    print("="*60)