import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.price import Price
from app.models.rs_daily import RSDaily

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_price_at_date(df, target_date):
    """
    الحصول على السعر في تاريخ محدد أو أقرب تاريخ سابق
    """
    # البحث عن السعر في التاريخ المحدد أو قبله
    row = df[df['date'] <= target_date].iloc[-1:]
    if row.empty:
        return None
    return row.iloc[0]['close']

def calculate_rs_batch(db: Session, target_date: date):
    """
    حساب RS لكل الأسهم في تاريخ محدد
    """
    # 1. جلب بيانات السنة الماضية لكل الأسهم
    # نحتاج بيانات سنة + هامش بسيط (370 يوم)
    start_date = target_date - timedelta(days=370)
    
    query = db.query(
        Price.symbol,
        Price.date,
        Price.close
    ).filter(
        Price.date.between(start_date, target_date)
    ).order_by(Price.symbol, Price.date)
    
    # تحويل لـ DataFrame للمعالجة السريعة
    # استخدام connection لجلب البيانات (متوافق مع SQLAlchemy 2.0)
    with db.bind.connect() as connection:
        df = pd.read_sql(query.statement, connection)
    
    if df.empty:
        logger.warning(f"⚠️ لا توجد بيانات لتاريخ {target_date}")
        return 0
    
    # تحويل التاريخ للتنسيق المناسب
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    results = []
    
    # 2. حساب العوائد لكل سهم
    # Group by symbol
    grouped = df.groupby('symbol')
    
    for symbol, group in grouped:
        try:
            # السعر الحالي
            current_row = group[group['date'] == target_date]
            if current_row.empty:
                continue
            
            current_price = float(current_row.iloc[0]['close'])
            
            # حساب العوائد للفترات المختلفة
            # 3 Months (~63 trading days / 90 calendar days)
            # 6 Months (~126 trading days / 180 calendar days)
            # 9 Months (~189 trading days / 270 calendar days)
            # 12 Months (~252 trading days / 365 calendar days)
            
            periods = {
                '3m': float(get_price_at_date(group, target_date - timedelta(days=90)) or 0),
                '6m': float(get_price_at_date(group, target_date - timedelta(days=180)) or 0),
                '9m': float(get_price_at_date(group, target_date - timedelta(days=270)) or 0),
                '12m': float(get_price_at_date(group, target_date - timedelta(days=365)) or 0)
            }
            
            # تجاهل السهم لو مفيش بيانات سنة كاملة (سعر 12 شهر = 0)
            if periods['12m'] == 0:
                continue
                
            returns = {
                '3m': (current_price / periods['3m']) - 1 if periods['3m'] > 0 else 0,
                '6m': (current_price / periods['6m']) - 1 if periods['6m'] > 0 else 0,
                '9m': (current_price / periods['9m']) - 1 if periods['9m'] > 0 else 0,
                '12m': (current_price / periods['12m']) - 1 if periods['12m'] > 0 else 0
            }
            
            # حساب الأداء الموزون (Weighted Performance)
            # حسب منطق المستخدم:
            # 3 Months: 40%
            # Others: 20%
            weighted_perf = (
                (returns['3m'] * 0.4) +
                (returns['6m'] * 0.2) +
                (returns['9m'] * 0.2) +
                (returns['12m'] * 0.2)
            ) * 100  # تحويل لنسبة مئوية
            
            results.append({
                'symbol': symbol,
                'return_3m': returns['3m'],
                'return_6m': returns['6m'],
                'return_9m': returns['9m'],
                'return_12m': returns['12m'],
                'weighted_performance': weighted_perf
            })
            
        except Exception as e:
            logger.error(f"Error calculating for {symbol}: {e}")
            continue

    if not results:
        return 0

    # 3. حساب Relative Score و Percentile
    results_df = pd.DataFrame(results)
    
    # حساب Median للسوق (Market Proxy)
    median_perf = results_df['weighted_performance'].median()
    
    # حساب Relative Score (مثل TradingView)
    # (Stock Performance / Market Median) * 100
    # لتجنب القسمة على صفر
    if median_perf == 0:
        median_perf = 1
        
    results_df['rs_raw'] = (results_df['weighted_performance'] / abs(median_perf)) * 100
    
    # حساب Percentile (Rank 1-99)
    # نستخدم rank(pct=True) * 99 ليكون من 0 لـ 99، ثم +1
    results_df['rs_percentile'] = results_df['rs_raw'].rank(pct=True) * 99
    results_df['rs_percentile'] = results_df['rs_percentile'].clip(1, 99)
    
    # إضافة الترتيب
    results_df = results_df.sort_values('rs_percentile', ascending=False)
    results_df['rank_position'] = range(1, len(results_df) + 1)
    
    # 4. حفظ النتائج في قاعدة البيانات
    processed_count = 0
    for _, row in results_df.iterrows():
        # البحث عن سجل موجود
        existing_record = db.query(RSDaily).filter(
            RSDaily.symbol == row['symbol'],
            RSDaily.date == target_date
        ).first()

        if existing_record:
            # تحديث
            existing_record.return_3m = row['return_3m']
            existing_record.return_6m = row['return_6m']
            existing_record.return_9m = row['return_9m']
            existing_record.return_12m = row['return_12m']
            existing_record.rs_raw = row['rs_raw']
            existing_record.rs_percentile = row['rs_percentile']
            existing_record.rank_position = row['rank_position']
            existing_record.total_stocks = len(results_df)
        else:
            # إنشاء جديد
            rs_record = RSDaily(
                symbol=row['symbol'],
                date=target_date,
                return_3m=row['return_3m'],
                return_6m=row['return_6m'],
                return_9m=row['return_9m'],
                return_12m=row['return_12m'],
                rs_raw=row['rs_raw'],
                rs_percentile=row['rs_percentile'],
                rank_position=row['rank_position'],
                total_stocks=len(results_df)
            )
            db.add(rs_record)
            
        processed_count += 1
    
    db.commit()
    logger.info(f"✅ تم حساب RS لـ {processed_count} سهم في {target_date}")
    return processed_count

def run_historical_calculation(start_date_str: str, end_date_str: str):
    """
    تشغيل الحساب لفترة زمنية
    """
    db = SessionLocal()
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    curr = start_date
    while curr <= end_date:
        # تجاوز الجمعة والسبت
        if curr.weekday() not in [4, 5]:
            logger.info(f"🔄 جاري الحساب لتاريخ: {curr}")
            calculate_rs_batch(db, curr)
        
        curr += timedelta(days=1)
    
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python calculate_rs_historical.py START_DATE END_DATE")
        print("Example: python calculate_rs_historical.py 2023-01-01 2023-12-31")
    else:
        run_historical_calculation(sys.argv[1], sys.argv[2])
