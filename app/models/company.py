from sqlalchemy import Column, Integer, String, JSON, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), nullable=True)
    exchange = Column(String(50), nullable=True)
    mic_code = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)
    type = Column(String(50), nullable=True)
    figi_code = Column(String(50), nullable=True)
    cfi_code = Column(String(50), nullable=True)
    isin = Column(String(50), nullable=True)
    cusip = Column(String(50), nullable=True)
    original_symbol = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # ✅ تأكد من وجوده
    
    def __repr__(self):
        return f"<Company(symbol='{self.symbol}', name='{self.name}')>"