from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class RSResponse(BaseModel):
    """
    نموذج استجابة RS لسهم واحد
    """
    symbol: str
    company_name: Optional[str] = None
    date: date
    return_3m: Optional[float]
    return_6m: Optional[float]
    return_9m: Optional[float]
    return_12m: Optional[float]
    rs_raw: Optional[float]
    rs_percentile: Optional[float]
    
    # Computed RS per period
    rs_3m: Optional[int] = None
    rs_6m: Optional[int] = None
    rs_9m: Optional[int] = None
    rs_12m: Optional[int] = None
    
    rank_position: Optional[int]
    total_stocks: Optional[int]
    
    class Config:
        from_attributes = True

class RSLatestResponse(BaseModel):
    """
    نموذج استجابة قائمة RS (للـ Screener أو القائمة الكاملة)
    """
    data: List[RSResponse]
    total_count: int
    date: date
