from app.core.database import get_db
from app.models.price import Price
from sqlalchemy import desc

db = next(get_db())
try:
    print("Checking 'no_of_trades' in 'prices' table...")
    latest_prices = db.query(Price).order_by(desc(Price.date)).limit(10).all()
    
    if not latest_prices:
        print("No prices found in the table.")
    else:
        print(f"Found {len(latest_prices)} records. Checking sample:")
        for p in latest_prices:
            print(f"Date: {p.date}, Symbol: {p.symbol}, No of Trades: {p.no_of_trades}, Close: {p.close}")

    # Check valid count
    count_valid = db.query(Price).filter(Price.no_of_trades.isnot(None)).count()
    print(f"\nTotal records with valid 'no_of_trades': {count_valid}")
    
    # Check null count
    count_null = db.query(Price).filter(Price.no_of_trades.is_(None)).count()
    print(f"Total records with NULL 'no_of_trades': {count_null}")

finally:
    db.close()
