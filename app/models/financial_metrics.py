from sqlalchemy import Column, Integer, String, Float, Enum, UniqueConstraint
from app.core.database import Base
import enum

class FinancialPeriod(str, enum.Enum):
    ANNUAL = 'Annual'
    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'
    UNKNOWN = 'Unknown'

class CompanyFinancialMetric(Base):
    __tablename__ = "company_financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    company_symbol = Column(String, index=True)
    year = Column(Integer, index=True)
    period = Column(Enum(FinancialPeriod), index=True)
    
    # The metric name (cleaned, snake_case) e.g., 'total_assets', 'net_profit'
    metric_name = Column(String, index=True)
    
    # The value. Most XBRL concepts are numeric, but some are text (Company Name, ISIN)
    metric_value = Column(Float, nullable=True)
    metric_text = Column(String, nullable=True)
    
    # Original Label in English (for display if needed)
    label_en = Column(String, nullable=True)
    
    # Metadata
    source_file = Column(String)

    # Composite unique constraint to prevent duplicates
    __table_args__ = (
        UniqueConstraint('company_symbol', 'year', 'period', 'metric_name', name='uix_financial_metric'),
    )
