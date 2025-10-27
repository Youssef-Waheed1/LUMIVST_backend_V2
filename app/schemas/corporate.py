from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class DividendBase(BaseModel):
    symbol: str
    amount: float
    ex_dividend_date: date
    payment_date: Optional[date] = None
    record_date: Optional[date] = None
    
    # الحقول الجديدة للدعم السعودي
    original_symbol: Optional[str] = None
    is_saudi: Optional[bool] = False
    currency: Optional[str] = "SAR"

class DividendCreate(DividendBase):
    pass

class DividendUpdate(DividendBase):
    pass

class Dividend(DividendBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class StockSplitBase(BaseModel):
    symbol: str
    split_ratio: str
    execution_date: date
    
    # الحقول الجديدة للدعم السعودي
    original_symbol: Optional[str] = None
    is_saudi: Optional[bool] = False

class StockSplitCreate(StockSplitBase):
    pass

class StockSplitUpdate(StockSplitBase):
    pass

class StockSplit(StockSplitBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True