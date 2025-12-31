"""
سكريبت فحص التواريخ في ملف CSV قبل الاستيراد
يتأكد من صحة تحويل التواريخ ويعرض أمثلة للتأكد
"""

import pandas as pd
import sys
from datetime import datetime
from pathlib import Path

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

def parse_date(date_str):
    """
    تحويل التاريخ - أولوية للصيغة الأمريكية M/D/YYYY
    """
    if pd.isna(date_str):
        return None
    
    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except:
            continue
    
    return None

def verify_csv_dates(csv_file_path: str, sample_size: int = 100):
    """
    فحص التواريخ في ملف CSV
    """
    print("=" * 60)
    print("🔍 فحص التواريخ في ملف CSV")
    print("=" * 60)
    
    # قراءة الملف
    print(f"\n📂 قراءة الملف: {csv_file_path}")
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
    except:
        df = pd.read_csv(csv_file_path, encoding='windows-1256')
    
    # تنظيف أسماء الأعمدة
    df.columns = df.columns.str.strip()
    
    # البحث عن عمود التاريخ
    date_column = None
    for col in ['Date', 'date', 'التاريخ']:
        if col in df.columns:
            date_column = col
            break
    
    if not date_column:
        print("❌ لم يتم العثور على عمود التاريخ!")
        return
    
    print(f"✅ عمود التاريخ: {date_column}")
    print(f"📊 إجمالي الصفوف: {len(df):,}")
    
    # أخذ عينة عشوائية
    sample_df = df.sample(n=min(sample_size, len(df)), random_state=42)
    
    print(f"\n🎲 فحص عينة عشوائية ({len(sample_df)} صف)...")
    print("-" * 60)
    
    # فحص التواريخ
    success_count = 0
    fail_count = 0
    examples = []
    
    for idx, row in sample_df.iterrows():
        original = row[date_column]
        parsed = parse_date(original)
        
        if parsed:
            success_count += 1
            if len(examples) < 10:
                examples.append((original, parsed))
        else:
            fail_count += 1
            print(f"⚠️ فشل: {original}")
    
    # عرض النتائج
    print("\n" + "=" * 60)
    print("📋 نتائج الفحص:")
    print("=" * 60)
    print(f"✅ نجح: {success_count} / {len(sample_df)}")
    print(f"❌ فشل: {fail_count} / {len(sample_df)}")
    
    if examples:
        print("\n📝 أمثلة على التحويل الناجح:")
        print("-" * 60)
        print(f"{'التاريخ الأصلي':<20} -> {'التاريخ المحول':<15}")
        print("-" * 60)
        for orig, parsed in examples:
            print(f"{str(orig):<20} -> {parsed}")
    
    # فحص نطاق التواريخ
    print("\n" + "=" * 60)
    print("📅 فحص نطاق التواريخ:")
    print("=" * 60)
    
    all_dates = df[date_column].apply(parse_date).dropna()
    if len(all_dates) > 0:
        min_date = all_dates.min()
        max_date = all_dates.max()
        print(f"أقدم تاريخ: {min_date}")
        print(f"أحدث تاريخ: {max_date}")
        print(f"النطاق: {(max_date - min_date).days} يوم")
        
        # التحقق من وجود تواريخ مستقبلية
        today = datetime.now().date()
        future_dates = all_dates[all_dates > today]
        if len(future_dates) > 0:
            print(f"\n⚠️ تحذير: وجدنا {len(future_dates)} تاريخ في المستقبل!")
        
        # التحقق من سنة 2002 (المطلوبة)
        dates_2002 = all_dates[(all_dates.dt.year == 2002) if hasattr(all_dates, 'dt') else all_dates.apply(lambda x: x.year == 2002)]
        if len(dates_2002) > 0:
            print(f"✅ وجدنا {len(dates_2002):,} سجل من سنة 2002")
        else:
            print("⚠️ لا توجد بيانات من سنة 2002!")
    
    print("\n" + "=" * 60)
    if fail_count == 0:
        print("✅ الفحص نجح! جميع التواريخ صالحة للاستيراد")
    else:
        print(f"⚠️ انتبه: {fail_count} تاريخ فشل في التحويل")
    print("=" * 60)
    
    # سؤال المستخدم
    print("\n❓ هل تريد المتابعة بالاستيراد؟ (y/n)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python verify_csv_dates.py path/to/file.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    verify_csv_dates(csv_file)
