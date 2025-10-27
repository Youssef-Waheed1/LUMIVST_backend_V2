from sqlalchemy import Column, String, Integer, DateTime, Float, Date, Boolean, func
from app.core.database import Base

class TimeSeries(Base):
    __tablename__ = "time_series"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # الحقول الجديدة للدعم السعودي
    original_symbol = Column(String(20))
    is_saudi = Column(Boolean, default=False)
    currency = Column(String(10), default="SAR")
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = ({'sqlite_autoincrement': True},)


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, nullable=False)
    indicator_type = Column(String(20))  # مثل RSI, MACD, SMA, إلخ
    value = Column(Float)
    
    # الحقول الجديدة للدعم السعودي
    original_symbol = Column(String(20))
    is_saudi = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())