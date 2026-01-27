from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class RSResponse(BaseModel):
    """
    نموذج استجابة RS لسهم واحد - محدث
    """
    symbol: str
    company_name: Optional[str] = None
    industry_group: Optional[str] = None
    date: date
    
    # RS Score
    rs_rating: Optional[int] = None
    prev_rs_rating: Optional[int] = None
    rs_raw: Optional[float] = None
    
    # Returns
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_9m: Optional[float] = None
    return_12m: Optional[float] = None
    
    # Ranks (Detailed)
    rank_3m: Optional[int] = None
    rank_6m: Optional[int] = None
    rank_9m: Optional[int] = None
    rank_12m: Optional[int] = None
    
    class Config:
        from_attributes = True

class RSLatestResponse(BaseModel):
    """
    نموذج استجابة قائمة RS
    """
    data: List[RSResponse]
    total_count: int
    date: date
