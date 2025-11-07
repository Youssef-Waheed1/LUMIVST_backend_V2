# app/schemas/quote.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class FiftyTwoWeek(BaseModel):
    low: Optional[float] = None
    high: Optional[float] = None
    low_change: Optional[float] = None
    high_change: Optional[float] = None
    low_change_percent: Optional[float] = None
    high_change_percent: Optional[float] = None
    range: Optional[str] = None

# ⭐ تأكد من وجود StockQuoteCreate
class StockQuoteCreate(BaseModel):
    symbol: str
    currency: Optional[str] = None
    datetime: Optional[str] = None
    timestamp: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    percent_change: Optional[float] = None
    average_volume: Optional[int] = None
    is_market_open: Optional[bool] = None
    fifty_two_week_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low_change: Optional[float] = None
    fifty_two_week_high_change: Optional[float] = None
    fifty_two_week_low_change_percent: Optional[float] = None
    fifty_two_week_high_change_percent: Optional[float] = None
    fifty_two_week_range: Optional[str] = None
    extended_price: Optional[float] = None
    extended_change: Optional[float] = None
    extended_percent_change: Optional[float] = None
    extended_timestamp: Optional[str] = None

class StockQuoteResponse(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    mic_code: Optional[str] = None
    currency: Optional[str] = None
    datetime: Optional[str] = None
    timestamp: Optional[int] = None
    last_quote_at: Optional[int] = None
    open: Optional[str] = None
    high: Optional[str] = None
    low: Optional[str] = None
    close: Optional[str] = None
    volume: Optional[str] = None
    previous_close: Optional[str] = None
    change: Optional[str] = None
    percent_change: Optional[str] = None
    average_volume: Optional[str] = None
    is_market_open: Optional[bool] = None
    
    # 52-week data
    fifty_two_week: Optional[Dict[str, Any]] = None
    fifty_two_week_low: Optional[str] = None
    fifty_two_week_high: Optional[str] = None
    fifty_two_week_low_change: Optional[str] = None
    fifty_two_week_high_change: Optional[str] = None
    fifty_two_week_low_change_percent: Optional[str] = None
    fifty_two_week_high_change_percent: Optional[str] = None
    fifty_two_week_range: Optional[str] = None
    
    # Extended hours
    extended_price: Optional[str] = None
    extended_change: Optional[str] = None
    extended_percent_change: Optional[str] = None
    extended_timestamp: Optional[str] = None
    
    last_updated: Optional[str] = None

    class Config:
        from_attributes = True