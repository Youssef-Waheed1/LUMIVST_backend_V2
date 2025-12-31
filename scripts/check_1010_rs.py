import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Check RS data for symbol 1010
print("=" * 50)
print("Checking RS data for symbol 1010")
print("=" * 50)

# Get earliest RS date
result = db.execute(text("""
    SELECT MIN(date) as earliest_date, MAX(date) as latest_date, COUNT(*) as total_records
    FROM rs_daily 
    WHERE symbol = '1010'
""")).fetchone()

print(f"\nEarliest RS Date: {result[0]}")
print(f"Latest RS Date: {result[1]}")
print(f"Total RS Records: {result[2]}")

# Get first 5 records
print("\nFirst 5 RS records:")
records = db.execute(text("""
    SELECT date, rs_percentile, return_12m 
    FROM rs_daily 
    WHERE symbol = '1010' 
    ORDER BY date 
    LIMIT 5
""")).fetchall()

for r in records:
    print(f"  {r[0]} - RS: {r[1]:.2f}, Return 12M: {r[2]:.4f}")

# Check price data availability
print("\n" + "=" * 50)
print("Checking Price data for symbol 1010")
print("=" * 50)

price_result = db.execute(text("""
    SELECT MIN(date) as earliest_date, MAX(date) as latest_date, COUNT(*) as total_records
    FROM prices 
    WHERE symbol = '1010'
""")).fetchone()

print(f"\nEarliest Price Date: {price_result[0]}")
print(f"Latest Price Date: {price_result[1]}")
print(f"Total Price Records: {price_result[2]}")

db.close()
