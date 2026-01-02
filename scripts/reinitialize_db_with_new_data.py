# real_final_solution.py
import psycopg2
import pandas as pd
import os
import time
from datetime import datetime

print("="*80)
print("🔥 الحل الحقيقي النهائي - تقسيم إلى ملفات صغيرة")
print("="*80)

def split_and_import():
    """تقسيم CSV إلى ملفات صغيرة واستيرادها واحدة تلو الأخرى"""
    
    CSV_PATH = "d:/Work/LUMIVST/Equites_Historical_Adjusted_Prices_Report.csv"
    DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
    
    # 1. قراءة CSV وتنظيفه مرة واحدة
    print("1. 📥 قراءة وتنظيف CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"   📊 الملف الأصلي: {len(df):,} سطر")
    
    # تنظيف
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=['Date'])
    df['% Change'] = df['% Change'].astype(str).str.replace('%', '')
    df['Symbol'] = df['Symbol'].astype(str).str.strip()
    
    # إزالة المكررات
    df = df.drop_duplicates(subset=['Symbol', 'Date'])
    print(f"   📈 بعد التنظيف: {len(df):,} سطر")
    
    # تنسيق التاريخ
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    # 2. تقسيم البيانات إلى مجموعات حسب الرمز
    print("\n2. 🪓 تقسيم البيانات إلى مجموعات...")
    
    # تجميع حسب الرمز
    grouped = df.groupby('Symbol')
    
    # إنشاء مجلد للملفات المؤقتة
    temp_dir = "temp_split_files"
    os.makedirs(temp_dir, exist_ok=True)
    
    # حفظ كل مجموعة في ملف منفصل
    file_paths = []
    for symbol, group in grouped:
        file_path = os.path.join(temp_dir, f"{symbol}.csv")
        group.to_csv(file_path, index=False)
        file_paths.append((symbol, file_path, len(group)))
    
    print(f"   📁 تم إنشاء {len(file_paths)} ملف مؤقت")
    
    # 3. تنظيف قاعدة البيانات أولاً
    print("\n3. 🧹 تنظيف قاعدة البيانات...")
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=30)
        cur = conn.cursor()
        
        # إزالة constraint مؤقتاً
        try:
            cur.execute("ALTER TABLE prices DROP CONSTRAINT IF EXISTS idx_prices_symbol_date")
            conn.commit()
        except:
            pass
        
        cur.execute("TRUNCATE TABLE prices RESTART IDENTITY CASCADE;")
        conn.commit()
        
        cur.close()
        conn.close()
        print("   ✅ تم تنظيف قاعدة البيانات")
    except Exception as e:
        print(f"   ❌ خطأ في التنظيف: {e}")
        return False
    
    # 4. استيراد كل ملف على حدة
    print("\n4. 📤 استيراد الملفات واحدة تلو الأخرى...")
    
    total_imported = 0
    start_time = time.time()
    
    for idx, (symbol, file_path, row_count) in enumerate(file_paths, 1):
        try:
            # إعادة الاتصال لكل ملف
            conn = psycopg2.connect(DB_URL, connect_timeout=30)
            conn.autocommit = True
            cur = conn.cursor()
            
            print(f"   📦 [{idx}/{len(file_paths)}] {symbol}: {row_count:,} سطر")
            
            # قراءة الملف الصغير
            with open(file_path, 'r', encoding='utf-8') as f:
                # تخطي السطر الأول (العناوين)
                next(f)
                
                # استخدام copy_from للملف الصغير
                cur.copy_from(
                    f,
                    'prices',
                    sep=',',
                    null='',
                    columns=[
                        'industry_group', 'symbol', 'company_name', 'date',
                        'open', 'high', 'low', 'close', 'change', 'change_percent',
                        'volume_traded', 'value_traded_sar', 'no_of_trades'
                    ]
                )
            
            total_imported += row_count
            
            # التقدم
            progress = (idx / len(file_paths)) * 100
            elapsed = time.time() - start_time
            if idx % 50 == 0 or idx == len(file_paths):
                print(f"      📊 التقدم: {progress:.1f}% - {total_imported:,} سطر - {elapsed:.0f} ثانية")
            
            cur.close()
            conn.close()
            
            # حذف الملف المؤقت بعد الاستيراد
            os.remove(file_path)
            
            # راحة قصيرة بين الملفات
            if idx % 100 == 0:
                time.sleep(1)
                
        except Exception as e:
            print(f"   ❌ خطأ في {symbol}: {e}")
            continue
    
    # 5. تنظيف مجلد الملفات المؤقتة
    try:
        os.rmdir(temp_dir)
    except:
        pass
    
    # 6. التحقق النهائي
    print("\n5. 🔍 التحقق النهائي...")
    
    conn = psycopg2.connect(DB_URL, connect_timeout=30)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM prices")
    final_count = cur.fetchone()[0]
    
    elapsed_total = time.time() - start_time
    
    print(f"   📊 إجمالي المستورد: {final_count:,} سطر")
    print(f"   ⏱️  الوقت الإجمالي: {elapsed_total:.1f} ثانية ({elapsed_total/60:.1f} دقيقة)")
    print(f"   🚀 السرعة: {final_count/elapsed_total:,.0f} سطر/ثانية")
    
    # إنشاء constraint جديد
    print("   🔒 إنشاء constraint جديد...")
    try:
        cur.execute("""
            CREATE UNIQUE INDEX idx_prices_symbol_date_new 
            ON prices (symbol, date)
        """)
        conn.commit()
        print("      ✅ تم إنشاء constraint")
    except Exception as e:
        print(f"      ⚠️  لا يمكن إنشاء constraint: {e}")
    
    cur.close()
    conn.close()
    
    return final_count

if __name__ == "__main__":
    try:
        result = split_and_import()
        
        if result:
            print("\n" + "="*80)
            print(f"🎉 تم استيراد {result:,} سطر بنجاح!")
            print("="*80)
        else:
            print("\n❌ فشل الاستيراد")
            
    except KeyboardInterrupt:
        print("\n\n❌ تم إيقاف العملية")
    except Exception as e:
        print(f"\n\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()