from pydantic import BaseModel
from typing import Optional

class CompanyBase(BaseModel):
    symbol: str
    name: str
    currency: Optional[str] = None
    exchange: Optional[str] = None
    mic_code: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    figi_code: Optional[str] = None
    cfi_code: Optional[str] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    # إزالة access من المخطط

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True

class CompanyResponse(BaseModel):
    data: list[Company]
    status: str = "ok"