from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class TimeSeriesBase(BaseModel):
    symbol: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    
    # الحقول الجديدة للدعم السعودي
    original_symbol: Optional[str] = None
    is_saudi: Optional[bool] = False
    currency: Optional[str] = "SAR"

class TimeSeriesCreate(TimeSeriesBase):
    pass

class TimeSeriesUpdate(TimeSeriesBase):
    pass

class TimeSeries(TimeSeriesBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class TechnicalIndicatorBase(BaseModel):
    symbol: str
    date: date
    indicator_type: str
    value: Optional[float] = None
    
    # الحقول الجديدة للدعم السعودي
    original_symbol: Optional[str] = None
    is_saudi: Optional[bool] = False

class TechnicalIndicatorCreate(TechnicalIndicatorBase):
    pass

class TechnicalIndicatorUpdate(TechnicalIndicatorBase):
    pass

class TechnicalIndicator(TechnicalIndicatorBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True