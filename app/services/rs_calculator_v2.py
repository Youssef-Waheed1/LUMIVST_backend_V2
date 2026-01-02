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
    logger.info("📥 Loading price data from database...")
    query = db.query(
        Price.date,
        Price.symbol,
        Price.close,
        Price.company_name
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

    # 2. حساب Returns (%) لكل فترة - الطريقة الصحيحة
    # return_3m = (Price_Today - Price_3M_Ago) / Price_3M_Ago
    
    # ترتيب البيانات ضروري جداً عشان الـ Shift يشتغل صح
    df = df.sort_values(by=['symbol', 'date'])
    
    # Group By Symbol لتطبيق الحسابات لكل سهم على حدة
    df['seq'] = df.groupby('symbol').cumcount() + 1
    
    # دالة مساعدة لحساب العائد من الأسعار
    # Return = (Price_Today - Price_Old) / Price_Old = (Price_Today / Price_Old) - 1
    def calc_return(series, period_days):
        """
        حساب العائد لفترة معينة من الأسعار
        """
        return (series / series.shift(period_days)) - 1

    # تطبيق الحسابات لكل مجموعة (سهم)
    grouped = df.groupby('symbol')['close']
    
    # حساب العوائد بناءً على أيام التداول (63, 126, 189, 252)
    logger.info("🧮 Calculating returns from prices...")
    df['return_3m'] = grouped.transform(lambda x: calc_return(x, 63))
    df['return_6m'] = grouped.transform(lambda x: calc_return(x, 126))
    df['return_9m'] = grouped.transform(lambda x: calc_return(x, 189))
    df['return_12m'] = grouped.transform(lambda x: calc_return(x, 252))

    # 3. حساب RS Raw (المتوسط الموزون من Returns - الطريقة الصحيحة)
    # ⚠️ ملاحظة مهمة: rs_raw يُحسب من Returns (%) وليس من Ranks!
    # المعادلة: 0.4*R3M + 0.2*R6M + 0.2*R9M + 0.2*R12M
    df['rs_raw'] = (
        (0.20 * df['return_12m']) +
        (0.20 * df['return_9m']) +
        (0.20 * df['return_6m']) +
        (0.40 * df['return_3m'])
    )
    
    # تصفية البيانات التي لا تحتوي على RS Raw (الأسهم الجديدة جداً)
    
    # 4. حساب RS Rating (الترتيب المئوي اليومي) وحساب الترتيب لكل فترة
    def calculate_daily_rank(day_group):
        valid_rs = day_group.dropna()
        if valid_rs.empty:
            return pd.Series(index=day_group.index, dtype=float)
        ranks = valid_rs.rank(pct=True) * 100
        return ranks.round(0).clip(lower=1, upper=99).astype(int)

    # تطبيق دالة الترتيب لكل فترة زمنية (للعرض في الموقع)
    logger.info("⚡ Calculating Ranks per period...")
    
    df['rank_3m'] = df.groupby('date')['return_3m'].transform(calculate_daily_rank)
    df['rank_6m'] = df.groupby('date')['return_6m'].transform(calculate_daily_rank)
    df['rank_9m'] = df.groupby('date')['return_9m'].transform(calculate_daily_rank)
    df['rank_12m'] = df.groupby('date')['return_12m'].transform(calculate_daily_rank)

    # حساب الـ RS النهائي من rs_raw (وليس من الـ Ranks!)
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

    # كان بيتم حذف القيم الفارغة سابقاً، لكن المستخدم يريد ظهور جميع الشركات حتى لو البيانات ناقصة (مثل IFERROR في الإكسل)
    # filtered_results = result_df.dropna(subset=['rs_rating'])
    # الآن سنستخدم القائمة الكاملة
    filtered_results = result_df
    
    logger.info(f"💾 Saving {len(filtered_results)} RS records (Including NULLs for new stocks) to database...")
    
    # 5. الحفظ في قاعدة البيانات باستخدام Bulk Upsert
    from sqlalchemy.dialects.postgresql import insert
    
    # دالة مساعدة لتنظيف القيم الرقمية
    def clean_float(val):
        if pd.isna(val) or np.isinf(val):
            return None
        return float(val)

    # تحويل البيانات إلى قائمة قواميس (List of Dicts)
    # ملاحظة: هنا بنخزن الـ Rank (1-99) مكان الـ Return (%) ليظهر في الموقع كترتيب
    records_list = []
    for _, row in filtered_results.iterrows():
        # التعامل مع القيم التي قد تكون NaN (للشركات الجديدة)
        rs_percentile_val = int(row['rs_rating']) if pd.notnull(row['rs_rating']) else None
        
        records_list.append({
            "date": row['date'],
            "symbol": row['symbol'],
            "rs_raw": clean_float(row['rs_raw']),
            "rs_percentile": rs_percentile_val,
            "return_3m": clean_float(row['rank_3m']),
            "return_6m": clean_float(row['rank_6m']),
            "return_9m": clean_float(row['rank_9m']),
            "return_12m": clean_float(row['rank_12m']),
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
