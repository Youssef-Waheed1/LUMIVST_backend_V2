from pydantic import BaseModel
from typing import Optional

class CompanyProfileBase(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    country: Optional[str] = None  # ⭐ جديد: إضافة country field

class CompanyProfileCreate(CompanyProfileBase):
    sector: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[int] = None
    website: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None  # ⭐ موجود مسبقاً
    logo_url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None

class CompanyProfileResponse(CompanyProfileBase):
    sector: Optional[str]
    industry: Optional[str]
    employees: Optional[int]
    website: Optional[str]
    description: Optional[str]
    state: Optional[str]
    country: Optional[str]  # ⭐ موجود مسبقاً
    logo_url: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    zip_code: Optional[str]
    
    class Config:
        from_attributes = True