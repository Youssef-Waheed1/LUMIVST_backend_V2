
from app.core.database import SessionLocal
from app.models.price import Price
from sqlalchemy import desc

def check_prices():
    db = SessionLocal()
    try:
        latest_date_row = db.query(Price.date).order_by(desc(Price.date)).first()
        if not latest_date_row:
            print("No prices found.")
            return

        latest_date = latest_date_row[0]
        print(f"Latest date: {latest_date}")

        prices = db.query(Price).filter(Price.date == latest_date).limit(5).all()
        for p in prices:
            print(f"Symbol: {p.symbol}, Close: {p.close}, Change: {p.change}, Change%: {p.change_percent}, No of Trades: {p.no_of_trades}")

    finally:
        db.close()

if __name__ == "__main__":
    check_prices()
