import sys
sys.path.append('.')
from app.core.database import SessionLocal
from sqlalchemy import text
import pandas as pd

db = SessionLocal()

print("=" * 60)
print("📊 فحص الأسهم التي ليس لها Industry Group")
print("=" * 60)

# 1. Get latest date
with db.bind.connect() as conn:
    latest_date = pd.read_sql(text("SELECT MAX(date) as max_date FROM prices"), conn)
    print(f"\n📅 آخر تاريخ في البيانات: {latest_date['max_date'].iloc[0]}")

# 2. Get unique symbols without industry_group
query = text("""
    SELECT DISTINCT symbol, industry_group, sector
    FROM prices
    WHERE date = (SELECT MAX(date) FROM prices)
    ORDER BY symbol
""")

with db.bind.connect() as conn:
    all_stocks = pd.read_sql(query, conn)

print(f"\n📈 إجمالي الأسهم في آخر تاريخ: {len(all_stocks)}")

# 3. Check stocks without industry_group
no_industry = all_stocks[
    (all_stocks['industry_group'].isna()) | 
    (all_stocks['industry_group'].str.strip() == '')
]

print(f"\n❌ الأسهم بدون Industry Group: {len(no_industry)}")
if len(no_industry) > 0:
    print("\nقائمة الأسهم:")
    print(no_industry.to_string(index=False))

# 4. Show industry group distribution
print("\n" + "=" * 60)
print("📊 توزيع الأسهم حسب Industry Group:")
print("=" * 60)

industry_counts = all_stocks.groupby('industry_group').size().sort_values(ascending=False)
print(f"\n✅ عدد Industry Groups: {len(industry_counts)}")
print("\nTop 10 Industry Groups:")
print(industry_counts.head(10).to_string())

db.close()
