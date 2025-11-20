from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from uuid import UUID

class ParameterSchema(BaseModel):
    default: int
    max_range: int
    min_range: int
    range: List[str]
    type: str

class OutputValueSchema(BaseModel):
    parameter_name: Dict[str, Any]

class TintingSchema(BaseModel):
    display: str
    color: str
    transparency: float
    lower_bound: str
    upper_bound: str
    parameters: Dict[str, ParameterSchema]

class TechnicalIndicatorBase(BaseModel):
    name: str
    display_name: str
    description: str
    category: str
    is_overlay: bool
    parameters: Dict[str, Any]
    output_values: Dict[str, Any]
    tinting: Optional[TintingSchema] = None

class TechnicalIndicatorCreate(TechnicalIndicatorBase):
    pass

class TechnicalIndicatorResponse(TechnicalIndicatorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TechnicalIndicatorDataBase(BaseModel):
    symbol: str
    indicator_name: str
    timeframe: str
    date: datetime
    values: Dict[str, float]

class TechnicalIndicatorDataCreate(TechnicalIndicatorDataBase):
    pass

class TechnicalIndicatorDataResponse(TechnicalIndicatorDataBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class TechnicalIndicatorRequest(BaseModel):
    symbol: str
    interval: str
    indicator: str
    parameters: Optional[Dict[str, Any]] = None

class MultipleIndicatorsRequest(BaseModel):
    symbol: str
    interval: str
    indicators: List[Dict[str, Any]]