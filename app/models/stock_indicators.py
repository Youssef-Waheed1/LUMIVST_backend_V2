"""
Stock Indicators Model
Stores pre-computed technical indicators for each stock per day
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.core.database import Base


class StockIndicator(Base):
    __tablename__ = "stock_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    
    # Company Info
    company_name = Column(String(255), nullable=True)
    
    # Price
    close = Column(Numeric(10, 2), nullable=True)
    
    # RSI Values (Daily)
    rsi_14 = Column(Numeric(5, 2), nullable=True)
    sma9_rsi = Column(Numeric(5, 2), nullable=True)
    wma45_rsi = Column(Numeric(5, 2), nullable=True)
    ema45_rsi = Column(Numeric(5, 2), nullable=True)
    e45_cfg = Column(Numeric(5, 2), nullable=True)
    e20_sma3_rsi3 = Column(Numeric(5, 2), nullable=True)
    
    # The Number (Daily)
    sma9_close = Column(Numeric(10, 2), nullable=True)
    the_number = Column(Numeric(10, 2), nullable=True)
    
    # STAMP
    stamp = Column(Boolean, default=False)
    stamp_daily = Column(Boolean, default=False)
    stamp_weekly = Column(Boolean, default=False)
    
    # Daily Conditions
    rsi_55_70 = Column(Boolean, default=False)
    sma9_gt_tn_daily = Column(Boolean, default=False)
    rsi_lt_80_d = Column(Boolean, default=False)
    sma9_rsi_lte_75_d = Column(Boolean, default=False)
    ema45_rsi_lte_70_d = Column(Boolean, default=False)
    rsi_gt_wma45_d = Column(Boolean, default=False)
    sma9rsi_gt_wma45rsi_d = Column(Boolean, default=False)
    
    # Weekly Conditions
    sma9_gt_tn_weekly = Column(Boolean, default=False)
    rsi_lt_80_w = Column(Boolean, default=False)
    sma9_rsi_lte_75_w = Column(Boolean, default=False)
    ema45_rsi_lte_70_w = Column(Boolean, default=False)
    rsi_gt_wma45_w = Column(Boolean, default=False)
    sma9rsi_gt_wma45rsi_w = Column(Boolean, default=False)
    
    # Weekly Values
    rsi_w = Column(Numeric(5, 2), nullable=True)
    sma9_rsi_w = Column(Numeric(5, 2), nullable=True)
    wma45_rsi_w = Column(Numeric(5, 2), nullable=True)
    ema45_rsi_w = Column(Numeric(5, 2), nullable=True)
    sma9_close_w = Column(Numeric(10, 2), nullable=True)
    the_number_w = Column(Numeric(10, 2), nullable=True)
    
    # Trend Screener
    cci = Column(Numeric(10, 2), nullable=True)
    cci_ema20 = Column(Numeric(10, 2), nullable=True)
    aroon_up = Column(Numeric(5, 2), nullable=True)
    aroon_down = Column(Numeric(5, 2), nullable=True)
    trend_signal = Column(Boolean, default=False)
    
    # Final Results
    final_signal = Column(Boolean, default=False)
    score = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_stock_indicators_symbol_date'),
        Index('idx_stock_indicators_symbol', 'symbol'),
        Index('idx_stock_indicators_date', 'date'),
        Index('idx_stock_indicators_score', 'score'),
        Index('idx_stock_indicators_final_signal', 'final_signal'),
    )
    
    def __repr__(self):
        return f"<StockIndicator(symbol={self.symbol}, date={self.date}, score={self.score})>"
