import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.price import Price
from app.models.rs_daily import RSDaily
import logging
import datetime

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_and_save_rs_v2(db: Session, target_date=None):
    """
    حساب RS بناءً على أيام التداول الفعلية (Trading Days Sequence).
    يطابق منطق الإكسل المتقدم:
    1. Seq = عداد أيام التداول لكل سهم.
    2. Shift 63/126/189/252 يوم تداول (مش أيام تقويم).
    3. RS Raw = متوسط موزون.
    4. RS Rating = ترتيب مئوي يومي (1-99).
    """
    logger.info("🔄 Starting RS Calculation V2 (Trading Days Logic)...")
    
    # 1. جلب كل البيانات التاريخية
    # ملحوظة: لازم نجيب التاريخ كله عشان نحسب الـ Seq والـ Shifts صح
    query = db.query(
        Price.date,
        Price.symbol,
        Price.close,
        Price.company_name
        # ممكن نحتاج volume لو هنستخدمه في شروط السيولة مستقبلاً
    ).order_by(Price.symbol, Price.date)
    
    prices = query.all()
    
    if not prices:
        logger.warning("⚠️ No price data found in database.")
        return

    # تحويل لـ DataFrame
    df = pd.DataFrame([{
        'date': p.date,
        'symbol': p.symbol,
        'close': float(p.close),
        'company_name': p.company_name
    } for p in prices])
    
    logger.info(f"📊 Loaded {len(df)} price records.")

    # 2. حساب مؤشرات التداول (Trading Logic)
    
    # ترتيب البيانات ضروري جداً عشان الـ Shift يشتغل صح
    df = df.sort_values(by=['symbol', 'date'])
    
    # Group By Symbol لتطبيق الحسابات لكل سهم على حدة
    # تكافئ: حساب Seq لكل سهم
    df['seq'] = df.groupby('symbol').cumcount() + 1
    
    # دالة مساعدة لحساب العائد مع Shift (إزاحة صفوف)
    # R3M = Price / Price(shifted 63 rows) - 1
    def calc_return(series, days):
        return (series / series.shift(days)) - 1

    # تطبيق الحسابات لكل مجموعة (سهم)
    grouped = df.groupby('symbol')['close']
    
    # حساب العوائد بناءً على أيام التداول (63, 126, 189, 252)
    # إذا لم يوجد بيانات كافية (مثلاً سهم جديد)، القيمة ستكون NaN
    df['return_3m'] = grouped.transform(lambda x: calc_return(x, 63))
    df['return_6m'] = grouped.transform(lambda x: calc_return(x, 126))
    df['return_9m'] = grouped.transform(lambda x: calc_return(x, 189))
    df['return_12m'] = grouped.transform(lambda x: calc_return(x, 252))

    # 3. حساب RS Raw (المتوسط الموزون)
    # المعادلة: 0.4*R12M + 0.2*R9M + 0.2*R6M + 0.2*R3M
    # شرط: لا يحسب إلا إذا توفرت بيانات 12 شهر (R12M مش NaN)
    # هذا يحقق شرط المستخدم: "لا تحسب RS إلا بعد ما يكون عندك بيانات كفاية"
    df['rs_raw'] = (
        (0.40 * df['return_12m']) +
        (0.20 * df['return_9m']) +
        (0.20 * df['return_6m']) +
        (0.20 * df['return_3m'])
    )
    
    # تصفية البيانات التي لا تحتوي على RS Raw (الأسهم الجديدة جداً)
    # يمكننا إبقاءها بقيم Null أو حذفها من حسابات الـ Rank
    
    # 4. حساب RS Rating (الترتيب المئوي اليومي)
    # "دايماً قارن نفس اليوم فقط"
    
    def calculate_daily_rank(day_group):
        # تصفية القيم غير الموجودة (NaN) من الترتيب
        valid_rs = day_group.dropna()
        
        if valid_rs.empty:
            return pd.Series(index=day_group.index, dtype=float)
            
        # استخدام Percentile Rank
        # pct=True بيرجع قيم من 0 لـ 1
        ranks = valid_rs.rank(pct=True) * 100
        
        # التقريب وتحديد النطاق 1-99
        ranks = ranks.round(0).clip(lower=1, upper=99)
        return ranks.astype(int)

    # تطبيق دالة الترتيب لكل يوم على حدة
    logger.info("⚡ Calculating RS Ratings per day...")
    df['rs_rating'] = df.groupby('date')['rs_raw'].transform(calculate_daily_rank)
    
    # لو حددنا target_date (عشان التحديث اليومي السريع)، نصفي النتائج دلوقتي
    if target_date:
        logger.info(f"Filtering for date: {target_date}")
        # convert target_date to match dataframe date type if useful
        result_df = df[df['date'] == target_date].copy()
    else:
        # لو مفيش تاريخ، نحدث الكل (أو آخر فترة)
        # لتجنب إعادة كتابة ملايين السجلات، ممكن نحدث آخر سنة بس؟
        # المستخدم طلب سكريبت كامل، فهنحفظ كله مبدئياً
        result_df = df.copy()

    # إسقاط القيم الفارغة في rs_rating (لأننا مش هنسجل RS لسهم لسه مدرج امبارح)
    filtered_results = result_df.dropna(subset=['rs_rating'])
    
    logger.info(f"💾 Saving {len(filtered_results)} RS records to database...")
    
    # 5. الحفظ في قاعدة البيانات باستخدام Bulk Upsert
    from sqlalchemy.dialects.postgresql import insert
    
    # تحويل البيانات إلى قائمة قواميس (List of Dicts)
    records_list = []
    for _, row in filtered_results.iterrows():
        records_list.append({
            "date": row['date'],
            "symbol": row['symbol'],
            "rs_raw": float(row['rs_raw']),
            "rs_percentile": int(row['rs_rating']),
            "return_3m": float(row['return_3m'] * 100),
            "return_6m": float(row['return_6m'] * 100),
            "return_9m": float(row['return_9m'] * 100),
            "return_12m": float(row['return_12m'] * 100),
            "created_at": datetime.datetime.now()
        })
        
    logger.info(f"💾 Prepared {len(records_list)} records for bulk upsert...")

    # تقسيم البيانات لمجموعات (Chunks) لعدم تجاوز حدود الداتابيز
    chunk_size = 5000
    for i in range(0, len(records_list), chunk_size):
        chunk = records_list[i:i + chunk_size]
        
        stmt = insert(RSDaily).values(chunk)
        
        # تعريف النزاع: لو الرمز والتاريخ موجودين -> حدث البيانات
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol', 'date'],
            set_={
                "rs_raw": stmt.excluded.rs_raw,
                "rs_percentile": stmt.excluded.rs_percentile,
                "return_3m": stmt.excluded.return_3m,
                "return_6m": stmt.excluded.return_6m,
                "return_9m": stmt.excluded.return_9m,
                "return_12m": stmt.excluded.return_12m
                # created_at لا يتم تحديثه عشان نحافظ على تاريخ الإنشاء الأصلي، أو ممكن نحدثه لو عايزين
            }
        )
        
        db.execute(stmt)
        db.commit() # Commit بعد كل Chunk لتخفيف الضغط وتجنب الـ Timeout
        logger.info(f"✅ Upserted chunk {i} to {i+chunk_size}")
        
    # db.commit() # خلاص عملنا commit جوه
    logger.info("✅ RS Calculation V2 Completed Successfully!")

if __name__ == "__main__":
    # Test script standalone
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        calculate_and_save_rs_v2(db)
    finally:
        db.close()
