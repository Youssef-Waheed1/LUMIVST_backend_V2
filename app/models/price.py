from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Index, BigInteger
from app.core.database import Base
from datetime import datetime

class Price(Base):
    """
    جدول الأسعار التاريخية للأسهم
    يخزن بيانات OHLCV اليومية
    """
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # معلومات السهم
    industry_group = Column(String(100))
    symbol = Column(String(10), nullable=False, index=True)
    company_name = Column(String(200))
    
    # التاريخ
    date = Column(Date, nullable=False, index=True)
    
    # بيانات السعر
    open = Column(Numeric(12, 2))
    high = Column(Numeric(12, 2))
    low = Column(Numeric(12, 2))
    close = Column(Numeric(12, 2), nullable=False)
    
    # بيانات التداول
    change = Column(Numeric(12, 2))
    change_percent = Column(Numeric(8, 4))
    volume_traded = Column(BigInteger)
    value_traded_sar = Column(Numeric(18, 2))
    no_of_trades = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes للأداء
    __table_args__ = (
        Index('idx_prices_symbol_date', 'symbol', 'date', unique=True),
        Index('idx_prices_date_desc', 'date', postgresql_using='btree'),
    )
    
    def __repr__(self):
        return f"<Price(symbol={self.symbol}, date={self.date}, close={self.close})>"
