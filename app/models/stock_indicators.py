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
    
    # ============ 1. RSI Indicator (Aymcfa-Abo Saad-RSI) ============
    rsi_14 = Column(Numeric(5, 2), nullable=True)              # RSI(14) - رمادي
    sma9_rsi = Column(Numeric(5, 2), nullable=True)            # SMA9 RSI - أزرق
    wma45_rsi = Column(Numeric(5, 2), nullable=True)           # WMA45 RSI - أحمر
    
    # ============ 2. The Number Indicator ============
    sma9_close = Column(Numeric(10, 2), nullable=True)         # SMA9 - أخضر
    the_number = Column(Numeric(10, 2), nullable=True)         # THE.NUMBER - أحمر
    the_number_hl = Column(Numeric(10, 2), nullable=True)      # Upper Band - أزرق (يضاف)
    the_number_ll = Column(Numeric(10, 2), nullable=True)      # Lower Band - أزرق (يضاف)
    
    # ============ 3. Stamp Indicator ============
    # Formula: A = RSI(14) - RSI(14)[9] + SMA(RSI(3), 3)
    rsi_14_9days_ago = Column(Numeric(5, 2), nullable=True)    # RSI14[9] - قيمة RSI من 9 أيام مضت
    rsi_3 = Column(Numeric(5, 2), nullable=True)              # RSI(3)
    sma3_rsi3 = Column(Numeric(5, 2), nullable=True)          # SMA(RSI3, 3)
    stamp_a_value = Column(Numeric(5, 2), nullable=True)      # قيمة A = RSI14 - RSI14[9] + SMA3(RSI3)
    
    # Stamp Plots
    stamp_s9rsi = Column(Numeric(5, 2), nullable=True)        # S9rsi - أحمر
    stamp_e45cfg = Column(Numeric(5, 2), nullable=True)       # E45cfg - أخضر
    stamp_e45rsi = Column(Numeric(5, 2), nullable=True)       # E45rsi - أصفر
    stamp_e20sma3 = Column(Numeric(5, 2), nullable=True)      # E20(sma3(rsi3)) - أسود
    
    # ============ 4. Trend Screener ============
    # Daily SMAs
    sma4 = Column(Numeric(10, 2), nullable=True)
    sma9 = Column(Numeric(10, 2), nullable=True)
    sma18 = Column(Numeric(10, 2), nullable=True)
    
    # Weekly SMAs
    sma4_w = Column(Numeric(10, 2), nullable=True)
    sma9_w = Column(Numeric(10, 2), nullable=True)
    sma18_w = Column(Numeric(10, 2), nullable=True)
    close_w = Column(Numeric(10, 2), nullable=True)
    
    # CCI
    cci = Column(Numeric(10, 2), nullable=True)
    cci_ema20 = Column(Numeric(10, 2), nullable=True)
    cci_ema20_w = Column(Numeric(10, 2), nullable=True)
    
    # Aroon (باستخدام أول occurrence)
    aroon_up = Column(Numeric(5, 2), nullable=True)
    aroon_down = Column(Numeric(5, 2), nullable=True)
    aroon_up_w = Column(Numeric(5, 2), nullable=True)
    aroon_down_w = Column(Numeric(5, 2), nullable=True)
    
    # Trend Conditions
    price_gt_sma18 = Column(Boolean, default=False)
    price_gt_sma9_weekly = Column(Boolean, default=False)
    sma_trend_daily = Column(Boolean, default=False)
    sma_trend_weekly = Column(Boolean, default=False)
    cci_gt_100 = Column(Boolean, default=False)
    cci_ema20_gt_0_daily = Column(Boolean, default=False)
    cci_ema20_gt_0_weekly = Column(Boolean, default=False)
    aroon_up_gt_70 = Column(Boolean, default=False)
    aroon_down_lt_30 = Column(Boolean, default=False)
    
    # Filters
    is_etf_or_index = Column(Boolean, default=False)
    has_gap = Column(Boolean, default=False)
    trend_signal = Column(Boolean, default=False)
    
    # ============ 5. RSI Screener ============
    # Daily Values
    wma45_rsi_screener = Column(Numeric(5, 2), nullable=True)  # WMA45 RSI للـ Screener
    ema45_rsi = Column(Numeric(5, 2), nullable=True)          # EMA45 RSI
    ema45_cfg = Column(Numeric(5, 2), nullable=True)          # EMA45 CFG
    ema20_sma3 = Column(Numeric(5, 2), nullable=True)         # EMA20(SMA3)
    wma45_close = Column(Numeric(10, 2), nullable=True)       # WMA45 Close
    
    # Weekly Values
    rsi_w = Column(Numeric(5, 2), nullable=True)
    rsi_3_w = Column(Numeric(5, 2), nullable=True)
    sma3_rsi3_w = Column(Numeric(5, 2), nullable=True)
    sma9_rsi_w = Column(Numeric(5, 2), nullable=True)
    wma45_rsi_w = Column(Numeric(5, 2), nullable=True)
    ema45_rsi_w = Column(Numeric(5, 2), nullable=True)
    ema45_cfg_w = Column(Numeric(5, 2), nullable=True)
    ema20_sma3_w = Column(Numeric(5, 2), nullable=True)
    sma9_close_w = Column(Numeric(10, 2), nullable=True)
    wma45_close_w = Column(Numeric(10, 2), nullable=True)
    the_number_w = Column(Numeric(10, 2), nullable=True)
    cfg_w = Column(Numeric(5, 2), nullable=True)
    
    # RSI Screener Conditions
    sma9_gt_tn_daily = Column(Boolean, default=False)
    sma9_gt_tn_weekly = Column(Boolean, default=False)
    rsi_lt_80_d = Column(Boolean, default=False)
    rsi_lt_80_w = Column(Boolean, default=False)
    sma9_rsi_lte_75_d = Column(Boolean, default=False)
    sma9_rsi_lte_75_w = Column(Boolean, default=False)
    ema45_rsi_lte_70_d = Column(Boolean, default=False)
    ema45_rsi_lte_70_w = Column(Boolean, default=False)
    rsi_55_70 = Column(Boolean, default=False)
    rsi_gt_wma45_d = Column(Boolean, default=False)
    rsi_gt_wma45_w = Column(Boolean, default=False)
    sma9rsi_gt_wma45rsi_d = Column(Boolean, default=False)
    sma9rsi_gt_wma45rsi_w = Column(Boolean, default=False)
    
    # STAMP Conditions
    stamp_daily = Column(Boolean, default=False)
    stamp_weekly = Column(Boolean, default=False)
    stamp = Column(Boolean, default=False)
    
    # ============ 6. CFG Analysis ============
    # CFG = RSI14 - RSI14[9] + SMA(RSI3, 3)
    cfg_daily = Column(Numeric(5, 2), nullable=True)
    cfg_sma9 = Column(Numeric(5, 2), nullable=True)
    cfg_sma20 = Column(Numeric(5, 2), nullable=True)
    cfg_ema20 = Column(Numeric(5, 2), nullable=True)
    cfg_ema45 = Column(Numeric(5, 2), nullable=True)
    
    # CFG Weekly
    cfg_w = Column(Numeric(5, 2), nullable=True)
    cfg_sma9_w = Column(Numeric(5, 2), nullable=True)
    cfg_ema20_w = Column(Numeric(5, 2), nullable=True)
    cfg_ema45_w = Column(Numeric(5, 2), nullable=True)
    
    # CFG Conditions
    cfg_gt_50_daily = Column(Boolean, default=False)
    cfg_ema45_gt_50 = Column(Boolean, default=False)
    cfg_ema20_gt_50 = Column(Boolean, default=False)
    cfg_gt_50_w = Column(Boolean, default=False)
    cfg_ema45_gt_50_w = Column(Boolean, default=False)
    cfg_ema20_gt_50_w = Column(Boolean, default=False)
    
    # CFG Components
    rsi_14_9days_ago_cfg = Column(Numeric(5, 2), nullable=True)  # RSI14[9] للـ CFG
    rsi_14_minus_9 = Column(Numeric(5, 2), nullable=True)        # RSI14 - RSI14[9]
    rsi_14_minus_9_w = Column(Numeric(5, 2), nullable=True)
    rsi_14_w_shifted = Column(Numeric(5, 2), nullable=True)  # ta.rsi(close[9], 14) Weekly
    
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
        Index('idx_stock_indicators_trend_signal', 'trend_signal'),
        Index('idx_stock_indicators_cfg_ema45_gt_50', 'cfg_ema45_gt_50'),
    )
    
    def __repr__(self):
        return f"<StockIndicator(symbol={self.symbol}, date={self.date}, score={self.score})>"