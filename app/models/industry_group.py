from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base

class IndustryGroupHistory(Base):
    __tablename__ = "industry_group_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    sector = Column(String(100))
    industry_group = Column(String(100), nullable=False, index=True)
    
    # Metrics
    number_of_stocks = Column(Integer)
    market_value = Column(Float)  # Sum of member stocks market cap
    
    # Ranking & Performance
    rs_score = Column(Float)  # The raw score used for ranking (e.g., avg 6m performance)
    rank = Column(Integer)    # 1 is best
    
    # Historical Ranks (stored for easy access, though could be queried)
    rank_1_week_ago = Column(Integer)
    rank_3_months_ago = Column(Integer)
    rank_6_months_ago = Column(Integer)
    
    ytd_change_percent = Column(Float)
    
    # New Fields
    letter_grade = Column(String(5))  # A+, A, B, etc.
    change_vs_last_week = Column(Integer)  # Positive = Improvement
    change_vs_3m_ago = Column(Integer)
    change_vs_6m_ago = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'industry_group', name='uix_date_industry_group'),
    )
