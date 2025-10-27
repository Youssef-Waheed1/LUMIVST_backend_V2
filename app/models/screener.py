from sqlalchemy import Column, String, Integer, DateTime, Float, Text, Boolean, ForeignKey, func
from app.core.database import Base

class ScreenerFilter(Base):
    __tablename__ = "screener_filters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # المعايير المالية
    min_market_cap = Column(Float)
    max_market_cap = Column(Float)
    min_pe_ratio = Column(Float)
    max_pe_ratio = Column(Float)
    min_pb_ratio = Column(Float)
    max_pb_ratio = Column(Float)
    min_dividend_yield = Column(Float)
    max_dividend_yield = Column(Float)
    
    # المعايير الفنية
    min_rsi = Column(Float)
    max_rsi = Column(Float)
    min_volume = Column(Float)
    max_volume = Column(Float)
    
    # معايير القطاع
    sector = Column(String(100))
    industry = Column(String(100))
    
    # الفلترة السعودية الجديدة
    saudi_only = Column(Boolean, default=False)  # فلترة الشركات السعودية فقط
    exchange_filter = Column(String(50))  # "Tadawul", "NASDAQ", etc.
    country_filter = Column(String(50))  # "Saudi Arabia", "United States"
    
    # إعدادات عامة
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScreenerResult(Base):
    __tablename__ = "screener_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filter_id = Column(Integer, ForeignKey("screener_filters.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    match_score = Column(Float)  # درجة التوافق مع المعايير
    
    # معلومات إضافية للنتيجة
    is_saudi = Column(Boolean, default=False)
    company_name = Column(String(255))
    sector = Column(String(100))
    
    created_at = Column(DateTime, server_default=func.now())