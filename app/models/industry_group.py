from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base

class IndustryGroupHistory(Base):
    __tablename__ = "industry_group_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Hierarchy
    sector = Column(String(100))
    industry_group = Column(String(100), nullable=False, index=True)
    
    # Metrics
    number_of_stocks = Column(Integer)
    market_value = Column(Float)  # In Billions or raw value? Let's store raw value and format in frontend.
    
    # Classification Performance
    rs_score = Column(Float) # The raw score used for ranking (e.g. Mean Price Change)
    
    # Ranks
    rank = Column(Integer) # Current Rank (1 to N)
    rank_1_week_ago = Column(Integer, nullable=True) # Rank 1 week ago
    rank_3_months_ago = Column(Integer, nullable=True) # Rank 3 months ago
    rank_6_months_ago = Column(Integer, nullable=True) # Rank 6 months ago
    
    # Changes
    ytd_change_percent = Column(Float) # % Change YTD
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'industry_group', name='uix_date_industry_group'),
    )

    def __repr__(self):
        return f"<IndustryGroupHistory(date={self.date}, group={self.industry_group}, rank={self.rank})>"
