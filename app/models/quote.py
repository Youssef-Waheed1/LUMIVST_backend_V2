from sqlalchemy import Column, String, Float, BigInteger, Boolean, DateTime
from app.core.database import Base

class StockQuote(Base):
    __tablename__ = "stock_quotes"
    
    symbol = Column(String(50), primary_key=True, index=True)
    currency = Column(String(10))
    datetime = Column(String(100))
    timestamp = Column(BigInteger)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    previous_close = Column(Float)
    change = Column(Float)
    percent_change = Column(Float)
    average_volume = Column(BigInteger)
    is_market_open = Column(Boolean)
    
    # 52-week data
    fifty_two_week_low = Column(Float)
    fifty_two_week_high = Column(Float)
    fifty_two_week_low_change = Column(Float)
    fifty_two_week_high_change = Column(Float)
    fifty_two_week_low_change_percent = Column(Float)
    fifty_two_week_high_change_percent = Column(Float)
    fifty_two_week_range = Column(String(100))
    
    # Extended hours
    extended_price = Column(Float)
    extended_change = Column(Float)
    extended_percent_change = Column(Float)
    extended_timestamp = Column(String(100))
    
    last_updated = Column(DateTime)