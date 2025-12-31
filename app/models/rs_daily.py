from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Index
from app.core.database import Base
from datetime import datetime

class RSDaily(Base):
    """
    جدول RS اليومي
    يخزن مؤشر القوة النسبية المحسوب لكل سهم يوميًا
    """
    __tablename__ = "rs_daily"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # العوائد حسب الفترة
    return_3m = Column(Numeric(10, 4))   # عائد 3 أشهر
    return_6m = Column(Numeric(10, 4))   # عائد 6 أشهر
    return_9m = Column(Numeric(10, 4))   # عائد 9 أشهر
    return_12m = Column(Numeric(10, 4))  # عائد 12 شهر
    
    # RS الخام والنهائي
    rs_raw = Column(Numeric(20, 6))           # RS قبل التحويل لـ percentile
    rs_percentile = Column(Numeric(5, 2))     # RS من 1 إلى 99
    
    # ترتيب السهم
    rank_position = Column(Integer)      # الترتيب بين الأسهم
    total_stocks = Column(Integer)       # عدد الأسهم الكلي في اليوم
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_rs_symbol_date', 'symbol', 'date', unique=True),
        Index('idx_rs_percentile_desc', 'rs_percentile', postgresql_using='btree'),
        Index('idx_rs_date_desc', 'date', postgresql_using='btree'),
    )
    
    def __repr__(self):
        return f"<RSDaily(symbol={self.symbol}, date={self.date}, rs={self.rs_percentile})>"
