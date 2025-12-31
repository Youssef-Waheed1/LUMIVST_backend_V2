"""
سكريبت لحذف جميع البيانات من جدول prices تمهيدًا لإعادة الاستيراد
"""

import sys
from pathlib import Path

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.price import Price

def truncate_prices():
    """
    حذف جميع السجلات من جدول prices
    """
    db = SessionLocal()
    
    try:
        # عد السجلات الحالية
        count = db.query(Price).count()
        
        print("=" * 60)
        print("⚠️  تحذير: حذف بيانات جدول الأسعار")
        print("=" * 60)
        print(f"📊 عدد السجلات الحالية: {count:,}")
        print("\n❗ تحذير: هذه العملية ستحذف جميع البيانات التاريخية!")
        print("⏱️  ستحتاج لإعادة استيراد CSV وإعادة حساب RS")
        print("\n❓ هل أنت متأكد؟ اكتب 'DELETE' للتأكيد:")
        
        confirmation = input().strip()
        
        if confirmation == 'DELETE':
            print("\n🗑️  جاري الحذف...")
            deleted = db.query(Price).delete()
            db.commit()
            print(f"✅ تم حذف {deleted:,} سجل بنجاح")
            print("✅ جدول prices أصبح فارغًا وجاهز لإعادة الاستيراد")
        else:
            print("❌ تم الإلغاء. لم يتم حذف أي بيانات.")
    
    except Exception as e:
        print(f"❌ خطأ: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    truncate_prices()
