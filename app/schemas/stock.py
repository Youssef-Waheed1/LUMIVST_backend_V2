from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Union

class StockResponse(BaseModel):
    """Schema موحد لبيانات السهم (مدمج من Profile + Quote)"""
    # البيانات الأساسية من Profile
    symbol: str
    name: str
    exchange: str = "Tadawul"
    sector: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[Union[int, str]] = None
    website: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    
    # البيانات المالية من Quote
    currency: str = "SAR"
    price: Optional[Union[float, str]] = None
    change: Optional[Union[float, str]] = None
    change_percent: Optional[Union[float, str]] = None
    previous_close: Optional[Union[float, str]] = None
    volume: Optional[Union[int, str]] = None
    turnover: Optional[str] = None
    open: Optional[Union[float, str]] = None
    high: Optional[Union[float, str]] = None
    low: Optional[Union[float, str]] = None
    average_volume: Optional[Union[int, str]] = None
    is_market_open: Optional[bool] = None
    
    # بيانات 52 أسبوع
    fifty_two_week: Optional[Dict[str, Any]] = None
    fifty_two_week_range: Optional[str] = None
    fifty_two_week_low: Optional[Union[float, str]] = None
    fifty_two_week_high: Optional[Union[float, str]] = None
    fifty_two_week_low_change: Optional[Union[float, str]] = None
    fifty_two_week_high_change: Optional[Union[float, str]] = None
    fifty_two_week_low_change_percent: Optional[Union[float, str]] = None
    fifty_two_week_high_change_percent: Optional[Union[float, str]] = None
    
    # 🎯 RS Ratings
    rs_12m: Optional[float] = None
    rs_9m: Optional[float] = None
    rs_6m: Optional[float] = None
    rs_3m: Optional[float] = None
    rs_1m: Optional[float] = None
    rs_2w: Optional[float] = None
    rs_1w: Optional[float] = None
    
    # ⭐ Change% لكل فترة (الحقول الجديدة)
    change_12m: Optional[float] = None
    change_9m: Optional[float] = None
    change_6m: Optional[float] = None
    change_3m: Optional[float] = None
    change_1m: Optional[float] = None
    change_2w: Optional[float] = None
    change_1w: Optional[float] = None
    
    # توقيتات
    last_updated: Optional[str] = None
    
    # Validators لتحويل "N/A" إلى None
    @field_validator(
        'fifty_two_week_low', 'fifty_two_week_high', 
        'fifty_two_week_low_change', 'fifty_two_week_high_change',
        'fifty_two_week_low_change_percent', 'fifty_two_week_high_change_percent',
        'price', 'change', 'change_percent', 'previous_close', 'open', 'high', 'low',
        # حقول Change الجديدة
        'change_12m', 'change_9m', 'change_6m', 'change_3m', 'change_1m', 'change_2w', 'change_1w',
        mode='before'
    )
    @classmethod
    def convert_na_to_none(cls, v):
        if v == "N/A" or v == "null" or v == "" or v == "None":
            return None
        return v
    
    @field_validator('volume', 'average_volume', 'employees', mode='before')
    @classmethod
    def convert_na_to_none_int(cls, v):
        if v == "N/A" or v == "null" or v == "" or v == "None":
            return None
        return v

    class Config:
        from_attributes = True





























# # app/schema/stock.py

# from pydantic import BaseModel, field_validator
# from typing import Optional, Dict, Any, Union

# class StockResponse(BaseModel):
#     """Schema موحد لبيانات السهم (مدمج من Profile + Quote)"""
#     # البيانات الأساسية من Profile
#     symbol: str
#     name: str
#     exchange: str = "Tadawul"
#     sector: Optional[str] = None
#     industry: Optional[str] = None
#     employees: Optional[Union[int, str]] = None
#     website: Optional[str] = None
#     description: Optional[str] = None
#     country: Optional[str] = None
#     state: Optional[str] = None
    
#     # البيانات المالية من Quote
#     currency: str = "SAR"
#     price: Optional[Union[float, str]] = None
#     change: Optional[Union[float, str]] = None
#     change_percent: Optional[Union[float, str]] = None
#     previous_close: Optional[Union[float, str]] = None
#     volume: Optional[Union[int, str]] = None
#     turnover: Optional[str] = None
#     open: Optional[Union[float, str]] = None
#     high: Optional[Union[float, str]] = None
#     low: Optional[Union[float, str]] = None
#     average_volume: Optional[Union[int, str]] = None
#     is_market_open: Optional[bool] = None
    
#     # بيانات 52 أسبوع
#     fifty_two_week: Optional[Dict[str, Any]] = None
#     fifty_two_week_range: Optional[str] = None
#     fifty_two_week_low: Optional[Union[float, str]] = None
#     fifty_two_week_high: Optional[Union[float, str]] = None
#     fifty_two_week_low_change: Optional[Union[float, str]] = None
#     fifty_two_week_high_change: Optional[Union[float, str]] = None
#     fifty_two_week_low_change_percent: Optional[Union[float, str]] = None
#     fifty_two_week_high_change_percent: Optional[Union[float, str]] = None
    
#       # 🎯 RS Ratings
#     rs_12m: Optional[float] = None
#     rs_9m: Optional[float] = None
#     rs_6m: Optional[float] = None
#     rs_3m: Optional[float] = None
#     rs_1m: Optional[float] = None
#     rs_2w: Optional[float] = None
#     rs_1w: Optional[float] = None
    
    
#     # توقيتات
#     last_updated: Optional[str] = None
    
#     # Validators لتحويل "N/A" إلى None
#     @field_validator(
#         'fifty_two_week_low', 'fifty_two_week_high', 
#         'fifty_two_week_low_change', 'fifty_two_week_high_change',
#         'fifty_two_week_low_change_percent', 'fifty_two_week_high_change_percent',
#         'price', 'change', 'change_percent', 'previous_close', 'open', 'high', 'low',
#         # الحقول الجديدة
#         'change_12m', 'change_9m', 'change_6m', 'change_3m', 'change_1m', 'change_2w', 'change_1w',
#         mode='before'
#     )
#     @classmethod
#     def convert_na_to_none(cls, v):
#         if v == "N/A" or v == "null" or v == "" or v == "None":
#             return None
#         return v
    
#     @field_validator('volume', 'average_volume', 'employees', 'rs_score', mode='before')
#     @classmethod
#     def convert_na_to_none_int(cls, v):
#         if v == "N/A" or v == "null" or v == "" or v == "None":
#             return None
#         return v

#     class Config:
#         from_attributes = True

# class StockListResponse(BaseModel):
#     data: list[StockResponse]
#     total: int
#     pagination: Optional[Dict[str, Any]] = None
#     timestamp: Optional[str] = None
#     country: Optional[str] = None