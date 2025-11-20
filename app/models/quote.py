from sqlalchemy import Column, String, Float, BigInteger, Boolean, DateTime
from app.core.database import Base

class StockQuote(Base):
    __tablename__ = "stock_quotes"
    
    # الحقول الأساسية
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
    
    # بيانات 52 أسبوع
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
    
    # RS Ratings - كل الفترات
    rs_12m = Column(Float)
    rs_9m = Column(Float)
    rs_6m = Column(Float)
    rs_3m = Column(Float)
    rs_1m = Column(Float)
    rs_2w = Column(Float)
    rs_1w = Column(Float)
    rs_1d = Column(Float)
    
    # ⭐ Change% لكل فترة (الحقول الجديدة)
    change_12m = Column(Float)
    change_9m = Column(Float)
    change_6m = Column(Float)
    change_3m = Column(Float)
    change_1m = Column(Float)
    change_2w = Column(Float)
    change_1w = Column(Float)
    
    last_updated = Column(DateTime)





























# from sqlalchemy import Column, String, Float, BigInteger, Boolean, DateTime
# from app.core.database import Base

# class StockQuote(Base):
#     __tablename__ = "stock_quotes"
    
#     # الحقول الأساسية
#     symbol = Column(String(50), primary_key=True, index=True)
#     currency = Column(String(10))
#     datetime = Column(String(100))
#     timestamp = Column(BigInteger)
#     open = Column(Float)
#     high = Column(Float)
#     low = Column(Float)
#     close = Column(Float)
#     volume = Column(BigInteger)
#     previous_close = Column(Float)
#     change = Column(Float)
#     percent_change = Column(Float)
#     average_volume = Column(BigInteger)
#     is_market_open = Column(Boolean)
    
#     # بيانات 52 أسبوع
#     fifty_two_week_low = Column(Float)
#     fifty_two_week_high = Column(Float)
#     fifty_two_week_low_change = Column(Float)
#     fifty_two_week_high_change = Column(Float)
#     fifty_two_week_low_change_percent = Column(Float)
#     fifty_two_week_high_change_percent = Column(Float)
#     fifty_two_week_range = Column(String(100))
    
#     # Extended hours
#     extended_price = Column(Float)
#     extended_change = Column(Float)
#     extended_percent_change = Column(Float)
#     extended_timestamp = Column(String(100))
    
#     # RS Ratings - كل الفترات
#     rs_12m = Column(Float)
#     rs_9m = Column(Float)
#     rs_6m = Column(Float)
#     rs_3m = Column(Float)
#     rs_1m = Column(Float)
#     rs_2w = Column(Float)
#     rs_1w = Column(Float)
#     rs_1d = Column(Float)  # ⭐ RS لآخر يوم
    
#     last_updated = Column(DateTime)













