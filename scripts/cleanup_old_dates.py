"""
سكريبت لحذف بيانات المؤشرات القديمة وإبقاء أحدث تاريخ فقط
Script to delete old indicator data and keep only the latest date
"""

import sys
import os
from datetime import date
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal


def get_latest_date():
    """الحصول على أحدث تاريخ في جدول prices"""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT MAX(date) FROM prices"))
        latest_date = result.scalar()
        return latest_date
    finally:
        db.close()


def cleanup_old_dates(keep_date: date = None):
    """
    حذف جميع البيانات القديمة وإبقاء تاريخ واحد فقط
    Delete all old data and keep only one date
    
    Args:
        keep_date: التاريخ المراد إبقاؤه (إذا لم يُحدد، سيتم استخدام أحدث تاريخ)
    """
    db = SessionLocal()
    
    try:
        # الحصول على أحدث تاريخ إذا لم يُحدد
        if keep_date is None:
            result = db.execute(text("SELECT MAX(date) FROM prices"))
            keep_date = result.scalar()
        
        if not keep_date:
            print("❌ لا توجد بيانات في جدول prices")
            return
        
        print(f"🗑️  سيتم حذف جميع البيانات ما عدا تاريخ: {keep_date}")
        print(f"🗑️  Deleting all data except date: {keep_date}")
        
        # احسب عدد السجلات التي سيتم حذفها
        count_query = text("""
            SELECT COUNT(*) FROM stock_indicators
            WHERE date != :keep_date
        """)
        result = db.execute(count_query, {"keep_date": keep_date})
        delete_count = result.scalar()
        
        if delete_count == 0:
            print("✅ لا توجد بيانات قديمة للحذف")
            print("✅ No old data to delete")
            db.close()
            return
        
        # حذف البيانات القديمة
        delete_query = text("""
            DELETE FROM stock_indicators
            WHERE date != :keep_date
        """)
        result = db.execute(delete_query, {"keep_date": keep_date})
        db.commit()
        
        print(f"\n✅ تم حذف {delete_count} سجل")
        print(f"✅ Deleted {delete_count} records")
        
        # عرض الإحصائيات النهائية
        result = db.execute(text("""
            SELECT date, COUNT(*) as count FROM stock_indicators
            GROUP BY date
            ORDER BY date DESC
        """))
        
        print("\n📊 الإحصائيات النهائية | Final Statistics:")
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]} records")
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_old_dates()
