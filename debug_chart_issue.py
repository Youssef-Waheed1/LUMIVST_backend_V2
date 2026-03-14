#!/usr/bin/env python3
"""
فحص سبب عدم ظهور بيانات 1321 في الرسم البياني
"""

import requests
import json

def debug_chart_data():
    """فحص بيانات الرسم البياني"""
    try:
        # 1. فحص API مباشرة
        print("=" * 60)
        print("🔍 فحص API endpoint")
        print("=" * 60)

        url = "http://localhost:8000/api/prices/history/1321?limit=5"
        response = requests.get(url, timeout=10)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ تم جلب البيانات من API")
            print(f"📈 عدد السجلات: {len(data.get('data', []))}")

            if data.get('data'):
                print("\n📋 أول 3 سجلات:")
                for i, record in enumerate(data['data'][:3], 1):
                    print(f"\n  {i}. التاريخ: {record.get('time')}")
                    print(f"     Close: {record.get('close')}")
                    print(f"     RSI: {record.get('rsi_14')}")
                    print(f"     CFG: {record.get('cfg')}")
            else:
                print("⚠️ لا توجد بيانات في الرد!")
        else:
            print(f"❌ فشل الاتصال برمز: {response.status_code}")
            print(f"📝 الرسالة: {response.text}")

        # 2. فحص قاعدة البيانات مباشرة
        print("\n" + "=" * 60)
        print("🔍 فحص قاعدة البيانات مباشرة")
        print("=" * 60)

        from app.core.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            # فحص stock_indicators
            result = db.execute(text("SELECT COUNT(*) FROM stock_indicators WHERE symbol = '1321'"))
            count = result.fetchone()[0]
            print(f"📊 عدد السجلات في stock_indicators: {count}")

            if count > 0:
                result = db.execute(text("""
                    SELECT date, rsi_14, cfg_daily FROM stock_indicators 
                    WHERE symbol = '1321' 
                    ORDER BY date DESC 
                    LIMIT 3
                """))
                rows = result.fetchall()
                print("✅ أحدث 3 سجلات في قاعدة البيانات:")
                for row in rows:
                    print(f"  التاريخ: {row[0]}, RSI: {row[1]}, CFG: {row[2]}")

            # فحص prices
            result = db.execute(text("SELECT COUNT(*) FROM prices WHERE symbol = '1321'"))
            count_prices = result.fetchone()[0]
            print(f"\n💰 عدد السجلات في prices: {count_prices}")

            # فحص التطابق
            if count > 0 and count_prices > 0:
                result = db.execute(text("""
                    SELECT COUNT(*) FROM prices p
                    INNER JOIN stock_indicators si 
                    ON p.symbol = si.symbol AND p.date = si.date
                    WHERE p.symbol = '1321'
                """))
                matching = result.fetchone()[0]
                print(f"🔗 السجلات المتطابقة: {matching}")

        finally:
            db.close()

    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chart_data()