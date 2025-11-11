#!/usr/bin/env python3
"""
Script لتحديث جداول قاعدة البيانات بإضافة الحقول المفقودة - الإصدار المصحح
"""

import psycopg2
from app.core.database import engine, SessionLocal
from app.core.config import settings
import logging
from sqlalchemy import text  # ⬅️ أضف هذا الاستيراد

# إعداد الـ logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_tables():
    """
    تحديث جداول قاعدة البيانات بإضافة الحقول المفقودة
    """
    connection = None
    try:
        # الاتصال بقاعدة البيانات
        connection = engine.raw_connection()
        cursor = connection.cursor()
        
        logger.info("🚀 بدء تحديث جداول قاعدة البيانات...")
        
        # 1. تحديث جدول income_statements بإضافة minority_interests
        try:
            cursor.execute("""
                ALTER TABLE income_statements 
                ADD COLUMN IF NOT EXISTS minority_interests FLOAT;
            """)
            logger.info("✅ تم إضافة حقل minority_interests إلى income_statements")
        except Exception as e:
            logger.error(f"❌ فشل إضافة minority_interests: {e}")
        
        # 2. تحديث جدول cash_flows بإضافة interest_paid
        try:
            cursor.execute("""
                ALTER TABLE cash_flows 
                ADD COLUMN IF NOT EXISTS interest_paid FLOAT;
            """)
            logger.info("✅ تم إضافة حقل interest_paid إلى cash_flows")
        except Exception as e:
            logger.error(f"❌ فشل إضافة interest_paid: {e}")
        
        # حفظ التغييرات
        connection.commit()
        logger.info("🎉 تم حفظ جميع التغييرات في قاعدة البيانات")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث قاعدة البيانات: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
        logger.info("🔚 تم إنهاء عملية التحديث")

def verify_changes():
    """
    التحقق من أن التغييرات تمت بنجاح - الإصدار المصحح
    """
    db = SessionLocal()
    try:
        # التحقق من وجود الحقول في income_statements باستخدام text()
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'income_statements' 
            AND column_name = 'minority_interests';
        """))
        minority_exists = result.fetchone()
        
        # التحقق من وجود الحقول في cash_flows باستخدام text()
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'cash_flows' 
            AND column_name = 'interest_paid';
        """))
        interest_exists = result.fetchone()
        
        if minority_exists and interest_exists:
            logger.info("✅ التحقق النهائي: جميع الحقول مضافّة بنجاح!")
            logger.info(f"   - minority_interests: {minority_exists[0]}")
            logger.info(f"   - interest_paid: {interest_exists[0]}")
            return True
        else:
            logger.error("❌ التحقق النهائي: بعض الحقول غير مضافّة!")
            logger.info(f"   - minority_interests: {bool(minority_exists)}")
            logger.info(f"   - interest_paid: {bool(interest_exists)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق: {e}")
        return False
    finally:
        db.close()

def main():
    """
    الدالة الرئيسية لتشغيل السكريبت
    """
    print("=" * 60)
    print("🔄 بدء عملية تحديث جداول قاعدة البيانات - الإصدار المصحح")
    print("=" * 60)
    
    # تحديث الجداول
    update_database_tables()
    
    print("-" * 60)
    
    # التحقق من التغييرات
    success = verify_changes()
    
    print("=" * 60)
    if success:
        print("🎊 تم تحديث قاعدة البيانات بنجاح! يمكنك الآن استخدام التطبيق.")
    else:
        print("⚠️  هناك مشكلة في التحديث. يرجى مراجعة الأخطاء أعلاه.")
    print("=" * 60)

if __name__ == "__main__":
    main()