from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum as PgEnum, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class FilingCategory(str, enum.Enum):
    FINANCIAL_STATEMENTS = 'Financial Statements'
    XBRL = 'XBRL'
    BOARD_REPORT = 'Board Report'
    ESG_REPORT = 'ESG Report'

class FilingPeriod(str, enum.Enum):
    ANNUAL = 'Annual'
    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'

class FileType(str, enum.Enum):
    PDF = 'pdf'
    EXCEL = 'excel'
    OTHER = 'other'

class FilingLanguage(str, enum.Enum):
    EN = 'en'
    AR = 'ar'

class CompanyOfficialFiling(Base):
    """
    Model for storing official company filings (PDF/Excel) downloaded from sources like Tadawul.
    """
    __tablename__ = "company_official_filings"

    id = Column(Integer, primary_key=True, index=True)
    company_symbol = Column(String, ForeignKey("companies.symbol"), nullable=False, index=True)
    
    category = Column(PgEnum(FilingCategory), nullable=False)
    period = Column(PgEnum(FilingPeriod), nullable=False)
    year = Column(Integer, nullable=False)
    published_date = Column(Date, nullable=True)
    
    file_url = Column(String, nullable=True) # Public S3 URL
    source_url = Column(String, nullable=True) # Original Tadawul URL
    file_type = Column(PgEnum(FileType), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    language = Column(PgEnum(FilingLanguage, name='filing_language_enum', create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False, server_default='en')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Note: Assuming Company model is defined elsewhere and registry handles it.
    # If using backref, ensure it doesn't conflict.
    company = relationship("Company", backref="official_filings")
