from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Index, text
from app.core.database import Base
from datetime import datetime

class RSDaily(Base):
    """
    جدول RS اليومي - Schema محدثة
    يخزن مؤشر القوة النسبية والرتب التفصيلية
    """
    __tablename__ = "rs_daily"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # التقييم الرئيسي
    rs_rating = Column(Integer)               # RS Rating (1-99)
    rs_raw = Column(Numeric(10, 6))           # القيمة الخام
    
    # العوائد
    return_3m = Column(Numeric(10, 6))
    return_6m = Column(Numeric(10, 6))
    return_9m = Column(Numeric(10, 6))
    return_12m = Column(Numeric(10, 6))
    
    # الرتب التفصيلية (New)
    rank_3m = Column(Integer)
    rank_6m = Column(Integer)
    rank_9m = Column(Integer)
    rank_12m = Column(Integer)
    
    # بيانات وصفية
    company_name = Column(String(255))
    industry_group = Column(String(255))
    
    # Generated column for filtering (Optimized)
    has_rating = Column(Boolean, default=False)
    
    # Indexes defined in DB directly via script, but we define them here for SQLAlchemy metadata
    __table_args__ = (
        Index('idx_rs_daily_symbol_date', 'symbol', 'date', unique=True),
        Index('idx_rs_daily_date_rating', 'date', text('rs_rating DESC')),
    )
    
    def __repr__(self):
        return f"<RSDaily(symbol={self.symbol}, date={self.date}, rating={self.rs_rating})>"
