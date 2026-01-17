from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date, datetime
from enum import Enum

class FilingCategoryEnum(str, Enum):
    FINANCIAL_STATEMENTS = 'Financial Statements'
    XBRL = 'XBRL'
    BOARD_REPORT = 'Board Report'
    ESG_REPORT = 'ESG Report'

class FilingPeriodEnum(str, Enum):
    ANNUAL = 'Annual'
    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'

class FileTypeEnum(str, Enum):
    PDF = 'pdf'
    EXCEL = 'excel'
    OTHER = 'other'

# Base Schema
class OfficialFilingBase(BaseModel):
    company_symbol: str
    category: FilingCategoryEnum
    period: FilingPeriodEnum
    year: int
    published_date: Optional[date] = None
    source_url: Optional[str] = None
    file_type: Optional[FileTypeEnum] = None

class OfficialFilingResponse(OfficialFilingBase):
    id: int
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Scraper Ingest Schemas ---

class ScrapedFilingItem(BaseModel):
    url: Optional[str] = None
    local_path: Optional[str] = None
    file_type: str # 'pdf', 'excel' 'none'
    period: str
    year: str # Scraper returns year as string sometimes
    published_date: Optional[str] = None

class IngestOfficialFilingsRequest(BaseModel):
    symbol: str
    # Map Category Name -> List of Items
    data: Dict[str, List[ScrapedFilingItem]] 
