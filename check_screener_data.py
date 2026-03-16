"""
التحقق من البيانات في الـ stock_indicators table
"""

from app.core.database import get_db
from app.models.stock_indicators import StockIndicator
from sqlalchemy import func, text

db = next(get_db())

# 1. عد الصفوف الكلية
total_rows = db.query(func.count(StockIndicator.id)).scalar()
print(f"✅ إجمالي الصفوف: {total_rows}")

# 2. التواريخ الموجودة
dates = db.query(func.distinct(StockIndicator.date)).order_by(StockIndicator.date.desc()).limit(10).all()
print(f"\n📅 آخر 10 تواريخ:")
for date_row in dates:
    count_on_date = db.query(func.count(StockIndicator.id)).filter(StockIndicator.date == date_row[0]).scalar()
    print(f"  - {date_row[0]}: {count_on_date} سهم")

# 3. التحقق من البيانات في آخر تاريخ
latest_date = db.query(func.max(StockIndicator.date)).scalar()
print(f"\n🔍 آخر تاريخ: {latest_date}")

if latest_date:
    # عينة من البيانات
    sample = db.query(StockIndicator).filter(StockIndicator.date == latest_date).limit(3).all()
    
    if sample:
        ind = sample[0]
        print(f"\n📊 عينة من البيانات ({ind.symbol}):")
        print(f"  - close: {ind.close}")
        print(f"  - sma_50: {ind.sma_50}")
        print(f"  - sma_150: {ind.sma_150}")
        print(f"  - sma_200: {ind.sma_200}")
        print(f"  - percent_off_52w_high: {ind.percent_off_52w_high}")
        print(f"  - percent_off_52w_low: {ind.percent_off_52w_low}")
        
        # Boolean conditions
        print(f"\n🔧 Boolean Conditions:")
        print(f"  - sma50_gt_sma150: {ind.sma50_gt_sma150}")
        print(f"  - sma50_gt_sma200: {ind.sma50_gt_sma200}")
        print(f"  - sma150_gt_sma200: {ind.sma150_gt_sma200}")
        print(f"  - sma200_gt_sma200_1m_ago: {ind.sma200_gt_sma200_1m_ago}")
    
    # عد الصفوف التي تحقق الشرط الأول فقط
    matching = db.query(func.count(StockIndicator.id)).filter(
        StockIndicator.date == latest_date,
        StockIndicator.sma50_gt_sma150 == True
    ).scalar()
    
    print(f"\n✅ أسهم حقق sma50_gt_sma150: {matching}")
    
    # عد الأسهم التي تحقق جميع شروط Trend-1-Month
    trend_1m = db.query(func.count(StockIndicator.id)).filter(
        StockIndicator.date == latest_date,
        StockIndicator.sma50_gt_sma150 == True,
        StockIndicator.sma50_gt_sma200 == True,
        StockIndicator.sma150_gt_sma200 == True,
        StockIndicator.sma200_gt_sma200_1m_ago == True,
        StockIndicator.percent_off_52w_low > 0.30,
        StockIndicator.percent_off_52w_high > -0.25,
    ).scalar()
    
    print(f"✅ أسهم حقق Trend-1-Month: {trend_1m}")
