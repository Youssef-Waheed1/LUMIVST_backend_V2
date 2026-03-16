"""
اختبار الشروط تدريجياً لمعرفة أين يختفي التقاطع
"""

from app.core.database import get_db
from app.models.stock_indicators import StockIndicator
from sqlalchemy import func, and_

db = next(get_db())

latest_date = db.query(func.max(StockIndicator.date)).scalar()
print(f"📅 آخر تاريخ: {latest_date}\n")

# اختبار تدريجي
query = db.query(StockIndicator).filter(StockIndicator.date == latest_date)
count = query.count()
print(f"🔹 البداية (جميع الأسهم): {count}")

# 1. sma50_gt_sma150
query = query.filter(StockIndicator.sma50_gt_sma150 == True)
count = query.count()
print(f"🔹 + sma50_gt_sma150: {count}")

# 2. sma50_gt_sma200
query = query.filter(StockIndicator.sma50_gt_sma200 == True)
count = query.count()
print(f"🔹 + sma50_gt_sma200: {count}")

# 3. sma150_gt_sma200
query = query.filter(StockIndicator.sma150_gt_sma200 == True)
count = query.count()
print(f"🔹 + sma150_gt_sma200: {count}")

# 4. sma200_gt_sma200_1m_ago
query = query.filter(StockIndicator.sma200_gt_sma200_1m_ago == True)
count = query.count()
print(f"🔹 + sma200_gt_sma200_1m_ago: {count}")

if count > 0:
    # 5. percent_off_52w_low > 30
    query = query.filter(StockIndicator.percent_off_52w_low > 30.0)
    count = query.count()
    print(f"🔹 + percent_off_52w_low > 30: {count}")
    
    if count > 0:
        # 6. percent_off_52w_high > -25
        query = query.filter(StockIndicator.percent_off_52w_high > -25.0)
        count = query.count()
        print(f"🔹 + percent_off_52w_high > -25: {count}")
        
        if count > 0:
            print(f"\n✅ وجدنا {count} أسهم!")
            results = query.limit(10).all()
            for stock in results:
                print(f"\n  - {stock.symbol}")

print("\n" + "="*60)
print("جرب بدون شرط sma200_gt_sma200_1m_ago:")
print("="*60)

query = db.query(StockIndicator).filter(StockIndicator.date == latest_date)
query = query.filter(StockIndicator.sma50_gt_sma150 == True)
query = query.filter(StockIndicator.sma50_gt_sma200 == True)
query = query.filter(StockIndicator.sma150_gt_sma200 == True)
# بدون: query = query.filter(StockIndicator.sma200_gt_sma200_1m_ago == True)
query = query.filter(StockIndicator.percent_off_52w_low > 30.0)
query = query.filter(StockIndicator.percent_off_52w_high > -25.0)

count = query.count()
print(f"✅ بدون sma200_gt_sma200_1m_ago: {count} أسهم")

if count > 0:
    results = query.limit(10).all()
    for stock in results:
        print(f"\n  - {stock.symbol}")
        if stock.sma_50 and stock.sma_150 and stock.sma_200 and stock.sma_200_1m_ago:
            print(f"    SMA200: اليوم={stock.sma_200:.2f}, منذ شهر={stock.sma_200_1m_ago:.2f}")
            print(f"    Condition: {stock.sma_200:.2f} > {stock.sma_200_1m_ago:.2f}? {stock.sma200_gt_sma200_1m_ago}")
