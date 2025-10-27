from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ScreenerFilterBase(BaseModel):
    name: str
    description: Optional[str] = None
    
    # المعايير المالية
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_pe_ratio: Optional[float] = None
    max_pe_ratio: Optional[float] = None
    min_pb_ratio: Optional[float] = None
    max_pb_ratio: Optional[float] = None
    min_dividend_yield: Optional[float] = None
    max_dividend_yield: Optional[float] = None
    
    # المعايير الفنية
    min_rsi: Optional[float] = None
    max_rsi: Optional[float] = None
    min_volume: Optional[float] = None
    max_volume: Optional[float] = None
    
    # معايير القطاع
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    # الفلترة السعودية الجديدة
    saudi_only: Optional[bool] = False
    exchange_filter: Optional[str] = None
    country_filter: Optional[str] = None

class ScreenerFilterCreate(ScreenerFilterBase):
    pass

class ScreenerFilterUpdate(ScreenerFilterBase):
    name: Optional[str] = None

class ScreenerFilter(ScreenerFilterBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ScreenerResultBase(BaseModel):
    filter_id: int
    symbol: str
    match_score: Optional[float] = None
    
    # معلومات إضافية للنتيجة
    is_saudi: Optional[bool] = False
    company_name: Optional[str] = None
    sector: Optional[str] = None

class ScreenerResultCreate(ScreenerResultBase):
    pass

class ScreenerResultUpdate(ScreenerResultBase):
    pass

class ScreenerResult(ScreenerResultBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScreenerRequest(BaseModel):
    """نموذج لطلب تصفية الأسهم"""
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_pe_ratio: Optional[float] = None
    max_pe_ratio: Optional[float] = None
    min_pb_ratio: Optional[float] = None
    max_pb_ratio: Optional[float] = None
    min_dividend_yield: Optional[float] = None
    max_dividend_yield: Optional[float] = None
    min_rsi: Optional[float] = None
    max_rsi: Optional[float] = None
    min_volume: Optional[float] = None
    max_volume: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    # الفلترة السعودية الجديدة
    saudi_only: Optional[bool] = False
    exchange_filter: Optional[str] = None
    country_filter: Optional[str] = None

class ScreenerResponse(BaseModel):
    """نموذج لنتائج التصفية"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    current_price: Optional[float] = None
    volume: Optional[float] = None
    rsi: Optional[float] = None
    match_score: float
    
    # معلومات السعودية
    is_saudi: Optional[bool] = False
    exchange: Optional[str] = None
    currency: Optional[str] = None

class ScreenerResultsList(BaseModel):
    results: List[ScreenerResponse]
    total: int
    filter_criteria: ScreenerRequest