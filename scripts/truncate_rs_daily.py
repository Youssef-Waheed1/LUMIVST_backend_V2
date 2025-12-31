"""
سكريبت لحذف جميع البيانات من جدول rs_daily تمهيدًا لإعادة حساب RS
"""

import sys
from pathlib import Path

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.rs_daily import RSDaily

def truncate_rs_daily():
    """
    حذف جميع السجلات من جدول rs_daily
    """
    db = SessionLocal()
    
    try:
        # عد السجلات الحالية
        count = db.query(RSDaily).count()
        
        print("=" * 60)
        print("⚠️  تحذير: حذف بيانات جدول RS")
        print("=" * 60)
        print(f"📊 عدد سجلات RS الحالية: {count:,}")
        print("\n❗ تحذير: هذه العملية ستحذف جميع حسابات RS القديمة!")
        print("⏱️  ستحتاج لإعادة حساب RS من البداية")
        print("\n❓ هل أنت متأكد؟ اكتب 'DELETE' للتأكيد:")
        
        confirmation = input().strip()
        
        if confirmation == 'DELETE':
            print("\n🗑️  جاري الحذف...")
            deleted = db.query(RSDaily).delete()
            db.commit()
            print(f"✅ تم حذف {deleted:,} سجل RS بنجاح")
            print("✅ جدول rs_daily أصبح فارغًا وجاهز لإعادة الحساب")
        else:
            print("❌ تم الإلغاء. لم يتم حذف أي بيانات.")
    
    except Exception as e:
        print(f"❌ خطأ: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    truncate_rs_daily()
