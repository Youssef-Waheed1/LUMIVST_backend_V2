#!/usr/bin/env python3
"""
فحص البيانات في قاعدة البيانات
"""

from app.core.database import SessionLocal
from sqlalchemy import text

def check_database_data():
    """فحص البيانات في stock_indicators و prices"""
    db = SessionLocal()
    try:
        # التحقق من وجود بيانات في stock_indicators للسهم 1321
        result = db.execute(text("SELECT COUNT(*) FROM stock_indicators WHERE symbol = '1321'"))
        count = result.fetchone()[0]
        print(f'📊 عدد السجلات في stock_indicators للسهم 1321: {count}')

        if count > 0:
            # جلب أحدث 3 سجلات
            result = db.execute(text("SELECT date, rsi_14, cfg_daily, the_number FROM stock_indicators WHERE symbol = '1321' ORDER BY date DESC LIMIT 3"))
            rows = result.fetchall()
            print('📈 أحدث 3 سجلات:')
            for row in rows:
                print(f'  التاريخ: {row[0]}, RSI: {row[1]}, CFG: {row[2]}, THE_NUMBER: {row[3]}')

        # التحقق من التواريخ في prices
        result = db.execute(text("SELECT COUNT(*) FROM prices WHERE symbol = '1321'"))
        count_prices = result.fetchone()[0]
        print(f'💰 عدد السجلات في prices للسهم 1321: {count_prices}')

        if count_prices > 0:
            result = db.execute(text("SELECT date FROM prices WHERE symbol = '1321' ORDER BY date DESC LIMIT 3"))
            dates = result.fetchall()
            print('📅 أحدث 3 تواريخ في prices:')
            for date_row in dates:
                print(f'  {date_row[0]}')

        # فحص التطابق بين التواريخ
        if count > 0 and count_prices > 0:
            result = db.execute(text("""
                SELECT COUNT(*) FROM prices p
                INNER JOIN stock_indicators si ON p.symbol = si.symbol AND p.date = si.date
                WHERE p.symbol = '1321'
            """))
            matching_count = result.fetchone()[0]
            print(f'🔗 عدد السجلات المتطابقة: {matching_count}')

    except Exception as e:
        print(f"❌ خطأ: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("="*50)
    print("🔍 فحص البيانات في قاعدة البيانات")
    print("="*50)

    check_database_data()