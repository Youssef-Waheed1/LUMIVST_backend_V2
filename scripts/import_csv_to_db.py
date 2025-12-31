"""
سكريبت استيراد البيانات التاريخية من ملف CSV إلى PostgreSQL

الاستخدام:
    python import_csv_to_db.py path/to/your/file.csv
"""

import pandas as pd
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.price import Price
from app.core.database import Base, engine

def clean_numeric(value):
    """
    تنظيف القيم الرقمية من الفواصل والمسافات
    """
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return value
    # إزالة الفواصل والمسافات
    cleaned = str(value).replace(',', '').replace(' ', '').strip()
    try:
        return float(cleaned)
    except:
        return None

def parse_date(date_str):
    """
    تحويل التاريخ - أولوية للصيغة الأمريكية M/D/YYYY (المستخدمة في ملفات Tadawul)
    """
    if pd.isna(date_str):
        return None
    
    # أولوية للصيغة الأمريكية M/D/YYYY (الأكثر شيوعًا في ملفات Tadawul)
    # ملاحظة: تم تغيير الترتيب لتجنب التفسير الخاطئ للتواريخ
    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except:
            continue
    
    print(f"⚠️ تحذير: فشل تحويل التاريخ {date_str}")
    return None

def import_csv_to_database(csv_file_path: str, batch_size: int = 1000):
    """
    استيراد ملف CSV إلى قاعدة البيانات
    
    Args:
        csv_file_path: مسار ملف CSV
        batch_size: عدد الصفوف في كل دفعة
    """
    
    # التحقق من وجود الملف
    if not os.path.exists(csv_file_path):
        print(f"❌ الملف غير موجود: {csv_file_path}")
        return
    
    print(f"📂 قراءة الملف: {csv_file_path}")
    
    # قراءة CSV
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
    except:
        # جرب encoding آخر
        df = pd.read_csv(csv_file_path, encoding='windows-1256')
    
    print(f"📊 عدد الصفوف: {len(df):,}")
    print(f"📋 الأعمدة: {list(df.columns)}")
    
    # تنظيف أسماء الأعمدة
    df.columns = df.columns.str.strip()
    
    # Mapping الأعمدة (حسب ما شفته في الصورة)
    column_mapping = {
        'Industry Group': 'industry_group',
        'Symbol': 'symbol',
        'Company Name': 'company_name',
        'Date': 'date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Change': 'change',
        '% Change': 'change_percent',
        'Volume Traded': 'volume_traded',
        'Value Traded (SAR)': 'value_traded_sar',
        'No. of Trades': 'no_of_trades'
    }
    
    # إعادة تسمية الأعمدة
    df = df.rename(columns=column_mapping)
    
    # تنظيف وتحويل البيانات
    print("🧹 تنظيف البيانات...")
    
    # تحويل التاريخ
    df['date'] = df['date'].apply(parse_date)
    
    # تنظيف الأعمدة الرقمية
    numeric_columns = ['open', 'high', 'low', 'close', 'change', 'change_percent', 
                      'volume_traded', 'value_traded_sar', 'no_of_trades']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
    
    # إزالة الصفوف التي ليس فيها تاريخ أو سعر إغلاق
    initial_count = len(df)
    df = df.dropna(subset=['date', 'close', 'symbol'])
    removed_count = initial_count - len(df)
    
    if removed_count > 0:
        print(f"⚠️ تم إزالة {removed_count} صف لعدم وجود بيانات أساسية")
    
    # فرز البيانات
    df = df.sort_values(['symbol', 'date'])
    
    print(f"✅ البيانات نظيفة: {len(df):,} صف جاهز للاستيراد")
    
    # إنشاء الجداول إذا لم تكن موجودة
    print("🔧 إنشاء الجداول...")
    Base.metadata.create_all(bind=engine)
    
    # إنشاء Session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # استيراد البيانات على دفعات
        total_inserted = 0
        total_updated = 0
        total_errors = 0
        
        print(f"💾 بدء الاستيراد (دفعات من {batch_size} صف)...")
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # تحويل الرمز إلى نص
                    symbol_str = str(row['symbol'])
                    
                    # البحث عن سجل موجود
                    existing = db.query(Price).filter(
                        Price.symbol == symbol_str,
                        Price.date == row['date']
                    ).first()
                    
                    if existing:
                        # تحديث السجل الموجود
                        for col in column_mapping.values():
                            if col in row.index and col not in ['id', 'created_at', 'updated_at']:
                                if col == 'symbol':
                                    setattr(existing, col, symbol_str)
                                else:
                                    setattr(existing, col, row[col])
                        existing.updated_at = datetime.utcnow()
                        total_updated += 1
                    else:
                        # إنشاء سجل جديد
                        price_record = Price(
                            industry_group=row.get('industry_group'),
                            symbol=symbol_str,
                            company_name=row.get('company_name'),
                            date=row['date'],
                            open=row.get('open'),
                            high=row.get('high'),
                            low=row.get('low'),
                            close=row['close'],
                            change=row.get('change'),
                            change_percent=row.get('change_percent'),
                            volume_traded=row.get('volume_traded'),
                            value_traded_sar=row.get('value_traded_sar'),
                            no_of_trades=row.get('no_of_trades')
                        )
                        db.add(price_record)
                        total_inserted += 1
                
                except Exception as e:
                    total_errors += 1
                    if total_errors <= 5:  # اعرض أول 5 أخطاء فقط
                        print(f"⚠️ خطأ في صف: {row.get('symbol')} - {row.get('date')}: {e}")
            
            # Commit كل دفعة
            db.commit()
            
            # عرض التقدم
            progress = min(i + batch_size, len(df))
            percent = (progress / len(df)) * 100
            print(f"   ⏳ {progress:,} / {len(df):,} ({percent:.1f}%) - "
                  f"مضاف: {total_inserted:,}, محدث: {total_updated:,}, أخطاء: {total_errors}")
        
        print("\n" + "="*60)
        print("✅ اكتمل الاستيراد بنجاح!")
        print(f"📊 الإحصائيات:")
        print(f"   • إجمالي الصفوف المعالجة: {len(df):,}")
        print(f"   • سجلات جديدة: {total_inserted:,}")
        print(f"   • سجلات محدثة: {total_updated:,}")
        print(f"   • أخطاء: {total_errors}")
        print("="*60)
        
        # إحصائيات إضافية
        print("\n📈 إحصائيات قاعدة البيانات:")
        total_records = db.query(Price).count()
        total_symbols = db.query(Price.symbol).distinct().count()
        date_range = db.query(
            db.func.min(Price.date),
            db.func.max(Price.date)
        ).first()
        
        print(f"   • إجمالي السجلات: {total_records:,}")
        print(f"   • عدد الأسهم: {total_symbols:,}")
        print(f"   • النطاق الزمني: {date_range[0]} إلى {date_range[1]}")
        
    except Exception as e:
        print(f"\n❌ خطأ فادح: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python import_csv_to_db.py path/to/file.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # يمكن تحديد batch_size كمعامل ثاني (اختياري)
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    import_csv_to_database(csv_file, batch_size)
