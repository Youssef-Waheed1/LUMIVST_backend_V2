from sqlalchemy import Column, String, Integer, DateTime, Float, Date, Boolean, func
from app.core.database import Base

class Dividend(Base):
    __tablename__ = "dividends"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    amount = Column(Float)
    ex_dividend_date = Column(Date)
    payment_date = Column(Date)
    record_date = Column(Date)
    
    # الحقول الجديدة للدعم السعودي
    original_symbol = Column(String(20))
    is_saudi = Column(Boolean, default=False)
    currency = Column(String(10), default="SAR")  # عملة التوزيع
    
    created_at = Column(DateTime, server_default=func.now())


class StockSplit(Base):
    __tablename__ = "stock_splits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    split_ratio = Column(String(20))  # e.g., "2:1"
    execution_date = Column(Date)
    
    # الحقول الجديدة للدعم السعودي
    original_symbol = Column(String(20))
    is_saudi = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())