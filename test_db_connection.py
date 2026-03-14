#!/usr/bin/env python3
"""
اختبار اتصال قاعدة البيانات
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def test_db_connection():
    """اختبار اتصال قاعدة البيانات"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ متغير DATABASE_URL غير موجود في .env")
            return False

        print(f"🔗 محاولة الاتصال بقاعدة البيانات...")
        print(f"📍 URL: {database_url[:50]}...")

        engine = create_engine(database_url, echo=False)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ اتصال قاعدة البيانات ناجح!")
                return True
            else:
                print("❌ فشل في تنفيذ الاختبار")
                return False

    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("🧪 اختبار اتصال قاعدة البيانات")
    print("="*50)

    success = test_db_connection()

    if success:
        print("\n✅ قاعدة البيانات متصلة بنجاح!")
        sys.exit(0)
    else:
        print("\n❌ فشل في الاتصال بقاعدة البيانات!")
        print("\n🔧 حلول محتملة:")
        print("1. تحقق من كلمة المرور في Render Dashboard")
        print("2. أعد إنشاء DATABASE_URL في متغيرات البيئة")
        print("3. تأكد من أن قاعدة البيانات لم تنتهِ صلاحيتها")
        sys.exit(1)