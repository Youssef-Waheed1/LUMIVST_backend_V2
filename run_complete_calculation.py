#!/usr/bin/env python3
"""
تشغيل الحساب الشامل لجميع المؤشرات على جميع الأسهم
"""

import sys
import os
import subprocess

def run_complete_calculation():
    """تشغيل السكريبت الشامل لحساب جميع المؤشرات"""
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'complete_historical_indicators.py')

    if not os.path.exists(script_path):
        print(f"❌ لم يتم العثور على السكريبت: {script_path}")
        return False

    print("🚀 بدء حساب جميع المؤشرات على جميع الأسهم...")
    print("⚠️ هذا قد يستغرق وقتاً طويلاً (ساعات)")
    print("💡 يمكنك مراقبة التقدم من خلال الرسائل في الكونسول")
    print("="*60)

    # تشغيل السكريبت بدون تحديد أسهم محددة (جميع الأسهم)
    cmd = [sys.executable, script_path, '--workers', '2']

    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n⚠️ تم إيقاف العملية بواسطة المستخدم")
        return False
    except Exception as e:
        print(f"❌ خطأ في تشغيل السكريبت: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔥 تشغيل الحساب الشامل لجميع المؤشرات")
    print("   سيتم حساب جميع المؤشرات على جميع الأسهم")
    print("="*60)

    success = run_complete_calculation()

    if success:
        print("\n✅ تم الانتهاء من الحساب بنجاح!")
        print("📊 يمكنك الآن فتح صفحة stocks/charts لرؤية جميع المؤشرات")
    else:
        print("\n❌ فشل في إكمال الحساب")

    print("="*60)