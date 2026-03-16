"""
تحليل تفصيلي لماذا لا تتطابق الأسهم
"""

from app.core.database import get_db
from app.models.stock_indicators import StockIndicator
from sqlalchemy import func

db = next(get_db())

latest_date = db.query(func.max(StockIndicator.date)).scalar()
print(f"📅 آخر تاريخ: {latest_date}\n")

# 1. كم سهم يحقق كل شرط
conditions = {
    "sma50_gt_sma150": StockIndicator.sma50_gt_sma150 == True,
    "sma50_gt_sma200": StockIndicator.sma50_gt_sma200 == True,
    "sma150_gt_sma200": StockIndicator.sma150_gt_sma200 == True,
    "sma200_gt_sma200_1m_ago": StockIndicator.sma200_gt_sma200_1m_ago == True,
    "percent_off_52w_low > 30": StockIndicator.percent_off_52w_low > 30.0,
    "percent_off_52w_high > -25": StockIndicator.percent_off_52w_high > -25.0,
}

print("📊 عدد الأسهم التي تحقق كل شرط منفصل:")
for name, condition in conditions.items():
    count = db.query(func.count(StockIndicator.id)).filter(
        StockIndicator.date == latest_date,
        condition
    ).scalar()
    print(f"  ✅ {name}: {count}")

# 2. عرض 10 أسهم عشوائية مع تفاصيلهم
print(f"\n📋 عينة من 10 أسهم مع التفاصيل:")
stocks = db.query(StockIndicator).filter(StockIndicator.date == latest_date).limit(10).all()

for i, stock in enumerate(stocks, 1):
    print(f"\n{i}. {stock.symbol} ({stock.company_name})")
    print(f"   SMA: 50={stock.sma_50:.2f}, 150={stock.sma_150:.2f}, 200={stock.sma_200:.2f}")
    print(f"   Booleans: 50>150={stock.sma50_gt_sma150}, 50>200={stock.sma50_gt_sma200}, 150>200={stock.sma150_gt_sma200}")
    print(f"   Off 52W: High={stock.percent_off_52w_high:.2f}%, Low={stock.percent_off_52w_low:.2f}%")
    print(f"   SMA200 vs 1m ago: {stock.sma200_gt_sma200_1m_ago}")

# 3. أسهم تحقق sma50_gt_sma150
print(f"\n🎯 الأسهم التي تحقق sma50_gt_sma150=True:")
matching_sma = db.query(StockIndicator).filter(
    StockIndicator.date == latest_date,
    StockIndicator.sma50_gt_sma150 == True
).limit(5).all()

for stock in matching_sma:
    print(f"\n   {stock.symbol}")
    print(f"   - SMA50={stock.sma_50:.2f} > SMA150={stock.sma_150:.2f}? {stock.sma50_gt_sma150}")
    print(f"   - SMA50={stock.sma_50:.2f} > SMA200={stock.sma_200:.2f}? {stock.sma50_gt_sma200}")
    print(f"   - SMA150={stock.sma_150:.2f} > SMA200={stock.sma_200:.2f}? {stock.sma150_gt_sma200}")
    print(f"   - Off Low: {stock.percent_off_52w_low:.2f}% (need > 30%)")
    print(f"   - Off High: {stock.percent_off_52w_high:.2f}% (need > -25%)")
