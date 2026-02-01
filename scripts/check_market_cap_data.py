import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.price import Price
from sqlalchemy import desc

db = SessionLocal()
latest_price = db.query(Price).order_by(desc(Price.date)).first()

if latest_price:
    print(f"Latest Date: {latest_price.date}")
    print(f"Checking Market Cap for a few stocks on {latest_price.date}...")
    prices = db.query(Price).filter(Price.date == latest_price.date).limit(5).all()
    for p in prices:
        print(f"Symbol: {p.symbol}, Market Cap: {p.market_cap}")
else:
    print("No prices found.")
db.close()
